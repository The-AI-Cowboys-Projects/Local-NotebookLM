"""
Persistent notebook manager for Local-NotebookLM.

Each notebook is a named workspace with its own sources, settings,
and pipeline outputs.  Data is stored on the filesystem so notebooks
survive server restarts.

Layout
------
<base_dir>/
    notebooks.json               # registry + default_notebook_id
    <uuid>/
        metadata.json            # name, created/updated timestamps, sources, settings
        sources/                 # copies of uploaded files
        step1/ step2/ step3/ step4/ step5/   # pipeline outputs
        podcast.wav
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone


_DEFAULT_BASE = os.path.join(".", "local_notebooklm", "web_ui", "notebooks")
_LEGACY_OUTPUT = os.path.join(".", "local_notebooklm", "web_ui", "output")

_DEFAULT_SETTINGS: dict = {
    "format": "podcast",
    "length": "medium",
    "style": "normal",
    "language": "english",
    "outputs_to_generate": [
        "Podcast Audio",
        "Infographic HTML",
        "Infographic PNG",
        "PPTX Slides",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: str, data: dict | list) -> None:
    """Write JSON atomically: write to .tmp then rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


import logging as _logging

_log = _logging.getLogger(__name__)


def _read_json(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_read_json(path: str, fallback: dict | list | None = None) -> dict | list:
    """Read JSON with corruption recovery.  Returns *fallback* on error."""
    try:
        return _read_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        _log.warning("Corrupted JSON at %s: %s — using fallback", path, e)
        if fallback is not None:
            _atomic_write_json(path, fallback)
            return fallback
        raise
    except FileNotFoundError:
        if fallback is not None:
            _log.warning("Missing file %s — recreating from defaults", path)
            _atomic_write_json(path, fallback)
            return fallback
        raise


class NotebookManager:
    """Filesystem-backed notebook persistence."""

    def __init__(self, base_dir: str = _DEFAULT_BASE):
        self._base = base_dir
        os.makedirs(self._base, exist_ok=True)
        self._registry_path = os.path.join(self._base, "notebooks.json")

        # Bootstrap: migrate legacy output or create default notebook
        if not os.path.exists(self._registry_path):
            self._bootstrap()

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------

    def _load_registry(self) -> dict:
        fallback = {"notebooks": [], "default_notebook_id": ""}
        return _safe_read_json(self._registry_path, fallback)

    def _save_registry(self, registry: dict) -> None:
        _atomic_write_json(self._registry_path, registry)

    def _bootstrap(self) -> None:
        """First-launch initialisation."""
        legacy = os.path.abspath(_LEGACY_OUTPUT)
        has_legacy = os.path.isdir(legacy) and any(os.scandir(legacy))

        if has_legacy:
            nb_id = self._create_notebook_dir("Legacy Notebook")
            # Move legacy outputs into the new notebook directory
            nb_dir = self._notebook_dir(nb_id)
            for item in os.listdir(legacy):
                src = os.path.join(legacy, item)
                dst = os.path.join(nb_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        else:
            nb_id = self._create_notebook_dir("My Notebook")

        registry = {
            "notebooks": [
                {
                    "id": nb_id,
                    "name": "Legacy Notebook" if has_legacy else "My Notebook",
                    "created_at": _now_iso(),
                }
            ],
            "default_notebook_id": nb_id,
        }
        self._save_registry(registry)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notebook_dir(self, notebook_id: str) -> str:
        return os.path.join(self._base, notebook_id)

    def _metadata_path(self, notebook_id: str) -> str:
        return os.path.join(self._notebook_dir(notebook_id), "metadata.json")

    def _load_metadata(self, notebook_id: str) -> dict:
        fallback = {
            "name": "Recovered Notebook",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "sources": [],
            "settings": dict(_DEFAULT_SETTINGS),
        }
        return _safe_read_json(self._metadata_path(notebook_id), fallback)

    def _save_metadata(self, notebook_id: str, meta: dict) -> None:
        meta["updated_at"] = _now_iso()
        _atomic_write_json(self._metadata_path(notebook_id), meta)

    def _create_notebook_dir(self, name: str) -> str:
        """Create on-disk structure for a new notebook.  Returns its UUID."""
        nb_id = uuid.uuid4().hex[:12]
        nb_dir = self._notebook_dir(nb_id)
        os.makedirs(nb_dir, exist_ok=True)
        os.makedirs(os.path.join(nb_dir, "sources"), exist_ok=True)

        now = _now_iso()
        meta = {
            "name": name,
            "created_at": now,
            "updated_at": now,
            "sources": [],
            "settings": dict(_DEFAULT_SETTINGS),
        }
        _atomic_write_json(self._metadata_path(nb_id), meta)
        return nb_id

    def _assert_exists(self, notebook_id: str) -> None:
        if not os.path.isdir(self._notebook_dir(notebook_id)):
            raise KeyError(f"Notebook {notebook_id!r} does not exist")

    # ------------------------------------------------------------------
    # Public API — Registry
    # ------------------------------------------------------------------

    def list_notebooks(self) -> list[dict]:
        """Return ``[{id, name, created_at}, ...]`` ordered newest-first."""
        reg = self._load_registry()
        return list(reg.get("notebooks", []))

    def get_default_notebook_id(self) -> str:
        reg = self._load_registry()
        return reg["default_notebook_id"]

    def set_default_notebook_id(self, notebook_id: str) -> None:
        self._assert_exists(notebook_id)
        reg = self._load_registry()
        reg["default_notebook_id"] = notebook_id
        self._save_registry(reg)

    # ------------------------------------------------------------------
    # Public API — CRUD
    # ------------------------------------------------------------------

    def create_notebook(self, name: str) -> str:
        """Create a new notebook.  Returns its id."""
        name = (name or "").strip() or "Untitled Notebook"
        nb_id = self._create_notebook_dir(name)

        reg = self._load_registry()
        reg["notebooks"].insert(0, {
            "id": nb_id,
            "name": name,
            "created_at": _now_iso(),
        })
        reg["default_notebook_id"] = nb_id
        self._save_registry(reg)
        return nb_id

    def get_notebook(self, notebook_id: str) -> dict:
        """Return full metadata for a notebook."""
        self._assert_exists(notebook_id)
        return self._load_metadata(notebook_id)

    def rename_notebook(self, notebook_id: str, new_name: str) -> None:
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Notebook name cannot be empty")
        self._assert_exists(notebook_id)

        meta = self._load_metadata(notebook_id)
        meta["name"] = new_name
        self._save_metadata(notebook_id, meta)

        reg = self._load_registry()
        for entry in reg["notebooks"]:
            if entry["id"] == notebook_id:
                entry["name"] = new_name
                break
        self._save_registry(reg)

    def delete_notebook(self, notebook_id: str) -> str | None:
        """Delete a notebook.  Returns the id of the next notebook to switch to,
        or ``None`` if a fresh default was auto-created."""
        self._assert_exists(notebook_id)
        shutil.rmtree(self._notebook_dir(notebook_id), ignore_errors=True)

        reg = self._load_registry()
        reg["notebooks"] = [n for n in reg["notebooks"] if n["id"] != notebook_id]

        if not reg["notebooks"]:
            # Last notebook deleted — create a fresh default
            fresh_id = self._create_notebook_dir("My Notebook")
            reg["notebooks"].append({
                "id": fresh_id,
                "name": "My Notebook",
                "created_at": _now_iso(),
            })
            reg["default_notebook_id"] = fresh_id
            self._save_registry(reg)
            return fresh_id

        if reg["default_notebook_id"] == notebook_id:
            reg["default_notebook_id"] = reg["notebooks"][0]["id"]

        self._save_registry(reg)
        return reg["default_notebook_id"]

    def get_notebook_dir(self, notebook_id: str) -> str:
        """Return the filesystem path for processor ``output_dir``."""
        self._assert_exists(notebook_id)
        return self._notebook_dir(notebook_id)

    # ------------------------------------------------------------------
    # Public API — Sources
    # ------------------------------------------------------------------

    def add_file_source(self, notebook_id: str, file_path: str, original_name: str) -> str:
        """Copy a file into the notebook's sources/ directory.  Returns dest path."""
        self._assert_exists(notebook_id)
        sources_dir = os.path.join(self._notebook_dir(notebook_id), "sources")
        os.makedirs(sources_dir, exist_ok=True)

        dest = os.path.join(sources_dir, original_name)
        # Avoid overwriting: add suffix if name exists
        if os.path.exists(dest):
            base, ext = os.path.splitext(original_name)
            dest = os.path.join(sources_dir, f"{base}_{uuid.uuid4().hex[:6]}{ext}")
        shutil.copy2(file_path, dest)

        meta = self._load_metadata(notebook_id)
        meta["sources"].append({
            "type": "file",
            "filename": os.path.basename(dest),
            "added_at": _now_iso(),
        })
        self._save_metadata(notebook_id, meta)
        return dest

    def add_url_source(self, notebook_id: str, url: str) -> None:
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        # Avoid duplicate URLs
        existing_urls = {s["url"] for s in meta["sources"] if s.get("type") == "url"}
        if url in existing_urls:
            return
        meta["sources"].append({
            "type": "url",
            "url": url,
            "added_at": _now_iso(),
        })
        self._save_metadata(notebook_id, meta)

    def get_sources(self, notebook_id: str) -> list[dict]:
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        return list(meta.get("sources", []))

    def remove_source(self, notebook_id: str, index: int) -> None:
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        sources = meta.get("sources", [])
        if index < 0 or index >= len(sources):
            raise IndexError(f"Source index {index} out of range")

        removed = sources.pop(index)
        # Delete the actual file if it was a file source
        if removed.get("type") == "file" and removed.get("filename"):
            fp = os.path.join(self._notebook_dir(notebook_id), "sources", removed["filename"])
            if os.path.exists(fp):
                os.remove(fp)

        self._save_metadata(notebook_id, meta)

    # ------------------------------------------------------------------
    # Public API — Settings
    # ------------------------------------------------------------------

    def save_settings(self, notebook_id: str, settings: dict) -> None:
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        meta["settings"] = settings
        self._save_metadata(notebook_id, meta)

    def get_settings(self, notebook_id: str) -> dict:
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        return meta.get("settings", dict(_DEFAULT_SETTINGS))

    # ------------------------------------------------------------------
    # Public API — Generation history
    # ------------------------------------------------------------------

    def add_history_entry(self, notebook_id: str, entry: dict) -> None:
        """Append a generation run to the notebook's history (newest first, max 20)."""
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        history = meta.get("history", [])
        history.insert(0, entry)
        meta["history"] = history[:20]
        self._save_metadata(notebook_id, meta)

    def get_history(self, notebook_id: str) -> list[dict]:
        self._assert_exists(notebook_id)
        meta = self._load_metadata(notebook_id)
        return meta.get("history", [])

    # ------------------------------------------------------------------
    # Public API — Export / Import
    # ------------------------------------------------------------------

    def export_notebook(self, notebook_id: str, dest_path: str) -> str:
        """Export a notebook as a .zip archive.  Returns the zip file path."""
        import zipfile

        self._assert_exists(notebook_id)
        nb_dir = self._notebook_dir(notebook_id)

        if not dest_path.endswith(".zip"):
            dest_path += ".zip"

        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(nb_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    arc_name = os.path.relpath(abs_path, nb_dir)
                    zf.write(abs_path, arc_name)
        return dest_path

    def import_notebook(self, zip_path: str, name: str | None = None) -> str:
        """Import a notebook from a .zip archive.  Returns the new notebook id."""
        import zipfile

        nb_id = uuid.uuid4().hex[:12]
        nb_dir = self._notebook_dir(nb_id)
        os.makedirs(nb_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(nb_dir)

        # Determine name: use provided, or from metadata, or fallback
        meta_path = self._metadata_path(nb_id)
        if os.path.exists(meta_path):
            meta = _read_json(meta_path)
        else:
            meta = {
                "name": "Imported Notebook",
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "sources": [],
                "settings": dict(_DEFAULT_SETTINGS),
            }

        if name:
            meta["name"] = name
        elif "name" not in meta:
            meta["name"] = "Imported Notebook"

        meta["updated_at"] = _now_iso()
        _atomic_write_json(meta_path, meta)

        # Register
        reg = self._load_registry()
        reg["notebooks"].insert(0, {
            "id": nb_id,
            "name": meta["name"],
            "created_at": _now_iso(),
        })
        reg["default_notebook_id"] = nb_id
        self._save_registry(reg)
        return nb_id
