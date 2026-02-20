"""Background pipeline execution — decouple from Gradio WebSocket.

Runs actual pipeline work in a daemon thread so browser refreshes
don't kill the generation.  The Gradio generator becomes a thin
progress poller that can reconnect to an already-running job.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

_STATE_FILE = "pipeline_state.json"


@dataclass
class PipelineJob:
    """Mutable state for one background pipeline run."""

    notebook_id: str
    output_dir: str
    thread: threading.Thread | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # Progress fields — mutated from the worker thread
    status: str = "running"          # running | completed | failed | cancelled
    current_step: int = 0
    total_steps: int = 0
    step_label: str = ""
    step_times: list[float] = field(default_factory=list)
    error: str = ""
    failed_step: int | None = None
    log_text: str = ""
    gen_start: float = field(default_factory=time.time)

    # Carry final result pieces so the poller can pick them up
    history_entry: dict | None = None

    def snapshot(self) -> dict:
        """Thread-safe copy of current progress state."""
        with self._lock:
            return {
                "status": self.status,
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "step_label": self.step_label,
                "step_times": list(self.step_times),
                "error": self.error,
                "failed_step": self.failed_step,
                "log_text": self.log_text,
                "gen_start": self.gen_start,
            }

    def update(self, **kwargs: Any) -> None:
        """Thread-safe field update + atomic write to pipeline_state.json."""
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            self._persist()

    def _persist(self) -> None:
        """Write current state to disk (called under lock)."""
        state = {
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_label": self.step_label,
            "step_times": list(self.step_times),
            "error": self.error,
            "failed_step": self.failed_step,
            "gen_start": self.gen_start,
            "notebook_id": self.notebook_id,
        }
        path = os.path.join(self.output_dir, _STATE_FILE)
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(state, f)
            os.replace(tmp, path)
        except OSError:
            pass  # best-effort


# ---------------------------------------------------------------------------
# Module-level job registry
# ---------------------------------------------------------------------------

_jobs: dict[str, PipelineJob] = {}
_jobs_lock = threading.Lock()


def start_job(
    notebook_id: str,
    output_dir: str,
    worker_fn: Callable[["PipelineJob"], None],
    worker_args: tuple = (),
) -> PipelineJob:
    """Create a PipelineJob and spawn a daemon thread running *worker_fn*."""
    job = PipelineJob(notebook_id=notebook_id, output_dir=output_dir)

    def _target():
        try:
            worker_fn(job, *worker_args)
        except Exception as exc:
            job.update(status="failed", error=str(exc)[:500])

    t = threading.Thread(target=_target, daemon=True, name=f"pipeline-{notebook_id}")
    job.thread = t
    with _jobs_lock:
        _jobs[notebook_id] = job
    t.start()
    return job


def get_job(notebook_id: str) -> PipelineJob | None:
    with _jobs_lock:
        return _jobs.get(notebook_id)


def is_running(notebook_id: str) -> bool:
    job = get_job(notebook_id)
    if job is None:
        return False
    return job.status == "running" and job.thread is not None and job.thread.is_alive()


def cancel_job(notebook_id: str) -> None:
    job = get_job(notebook_id)
    if job is not None:
        job.cancel_event.set()
        job.update(status="cancelled")


def remove_job(notebook_id: str) -> None:
    """Remove a finished job from the registry."""
    with _jobs_lock:
        _jobs.pop(notebook_id, None)


def load_stale_state(output_dir: str) -> dict | None:
    """Read pipeline_state.json for crash recovery.

    Returns the dict if the file says ``status == "running"`` (i.e. the
    process died while a job was in-flight), else ``None``.

    Auto-clears the stale flag on read so the banner only appears once.
    """
    path = os.path.join(output_dir, _STATE_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            state = json.load(f)
        if state.get("status") == "running":
            # Mark as interrupted so subsequent loads don't re-trigger
            state["status"] = "interrupted"
            try:
                with open(path, "w") as f:
                    json.dump(state, f)
            except OSError:
                pass
            return state
    except (json.JSONDecodeError, OSError):
        pass
    return None
