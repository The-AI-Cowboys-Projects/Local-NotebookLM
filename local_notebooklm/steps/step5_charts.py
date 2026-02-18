"""Step 5 — Chart generation for infographic visuals.

Generates matplotlib charts from structured podcast data:
- Topic importance horizontal bar chart
- Speaker distribution donut chart
- Conversation flow scatter timeline

All charts use a cyberpunk dark theme matching the HTML/PPTX infographic.
matplotlib is optional — functions return None if it is not installed.
"""

import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Theme constants (cyberpunk dark, matching HTML/PPTX infographic)
# ---------------------------------------------------------------------------

_BG = "#0a0a14"
_CARD_BG = "#0f0f1e"
_CYAN = "#00f0ff"
_TEAL = "#3bd6c6"
_MAGENTA = "#dd368a"
_PINK = "#ff00aa"
_BODY = "#e0e0f0"
_MUTED = "#8888aa"
_GRID = "#1e1e40"

_PALETTE = [_CYAN, _TEAL, _MAGENTA, _PINK, "#a855f7", "#facc15"]


def _setup_cyberpunk_style():
    """Configure matplotlib for non-interactive rendering with cyberpunk theme.

    Returns the ``matplotlib`` module, or raises ``ImportError``.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": _BG,
        "axes.facecolor": _CARD_BG,
        "axes.edgecolor": _GRID,
        "axes.labelcolor": _BODY,
        "text.color": _BODY,
        "xtick.color": _MUTED,
        "ytick.color": _MUTED,
        "grid.color": _GRID,
        "grid.alpha": 0.4,
        "figure.dpi": 150,
        "savefig.facecolor": _BG,
        "savefig.edgecolor": _BG,
        "font.size": 10,
    })
    return plt


def _fig_to_base64(fig) -> str:
    """Render a matplotlib figure to a base64-encoded PNG data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.3)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    buf.close()
    return f"data:image/png;base64,{b64}"


def _fig_to_png(fig, path: str) -> str:
    """Save a matplotlib figure to a PNG file and return the path."""
    fig.savefig(path, format="png", bbox_inches="tight", pad_inches=0.3)
    return path


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

def generate_topic_importance_chart(
    data: Dict[str, Any],
    output_path: Optional[str] = None,
) -> Optional[Tuple[str, Optional[str]]]:
    """Horizontal bar chart of topic importance scores.

    Returns ``(base64_data_uri, png_path_or_None)`` or ``None`` if
    matplotlib is missing or data is empty.
    """
    try:
        plt = _setup_cyberpunk_style()
    except ImportError:
        logger.info("matplotlib not installed — skipping topic chart.")
        return None

    topics = data.get("topics", [])
    if not topics:
        return None

    names = [t.get("name", "?") for t in topics]
    scores = [int(t.get("importance", 0)) for t in topics]

    # Reverse so highest importance is at top
    names = names[::-1]
    scores = scores[::-1]

    fig, ax = plt.subplots(figsize=(6, max(2, len(names) * 0.5 + 1)))
    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(names))][::-1]
    bars = ax.barh(names, scores, color=colors, height=0.6, edgecolor="none")
    ax.set_xlim(0, 5.5)
    ax.set_xlabel("Importance")
    ax.set_title("Topic Importance", color=_CYAN, fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="x", linestyle="--")
    ax.tick_params(axis="y", length=0)

    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_width() + 0.12, bar.get_y() + bar.get_height() / 2,
            str(score), va="center", color=_BODY, fontsize=9,
        )

    plt.tight_layout()

    b64 = _fig_to_base64(fig)
    png = _fig_to_png(fig, output_path) if output_path else None
    plt.close(fig)
    return (b64, png)


def generate_speaker_distribution_chart(
    data: Dict[str, Any],
    output_path: Optional[str] = None,
) -> Optional[Tuple[str, Optional[str]]]:
    """Donut chart of speaker line counts.

    Returns ``(base64_data_uri, png_path_or_None)`` or ``None``.
    """
    try:
        plt = _setup_cyberpunk_style()
    except ImportError:
        logger.info("matplotlib not installed — skipping speaker chart.")
        return None

    speakers = data.get("speakers", [])
    if not speakers:
        return None

    labels = [s.get("label", "?") for s in speakers]
    counts = [int(s.get("line_count", 0)) for s in speakers]

    if sum(counts) == 0:
        return None

    colors = [_PALETTE[i % len(_PALETTE)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(5, 5))
    wedges, texts, autotexts = ax.pie(
        counts,
        labels=labels,
        colors=colors,
        autopct="%1.0f%%",
        pctdistance=0.78,
        startangle=90,
        wedgeprops=dict(width=0.4, edgecolor=_BG, linewidth=2),
    )

    for t in texts:
        t.set_color(_BODY)
        t.set_fontsize(9)
    for t in autotexts:
        t.set_color(_BG)
        t.set_fontsize(8)
        t.set_fontweight("bold")

    ax.set_title("Speaker Distribution", color=_CYAN, fontsize=13, fontweight="bold", pad=12)

    plt.tight_layout()

    b64 = _fig_to_base64(fig)
    png = _fig_to_png(fig, output_path) if output_path else None
    plt.close(fig)
    return (b64, png)


def generate_conversation_flow_chart(
    data: Dict[str, Any],
    output_path: Optional[str] = None,
) -> Optional[Tuple[str, Optional[str]]]:
    """Scatter timeline of conversation flow entries.

    Returns ``(base64_data_uri, png_path_or_None)`` or ``None``.
    """
    try:
        plt = _setup_cyberpunk_style()
    except ImportError:
        logger.info("matplotlib not installed — skipping flow chart.")
        return None

    flow = data.get("conversation_flow", [])
    if not flow:
        return None

    # Build speaker → y-index mapping
    unique_speakers = []
    for entry in flow:
        spk = entry.get("speaker", "?")
        if spk not in unique_speakers:
            unique_speakers.append(spk)

    speaker_y = {s: i for i, s in enumerate(unique_speakers)}

    xs = list(range(1, len(flow) + 1))
    ys = [speaker_y[e.get("speaker", "?")] for e in flow]
    topics = [e.get("topic", "") for e in flow]
    colors = [_PALETTE[speaker_y[e.get("speaker", "?")] % len(_PALETTE)] for e in flow]

    fig, ax = plt.subplots(figsize=(max(6, len(flow) * 0.8 + 1), 3.5))
    ax.scatter(xs, ys, c=colors, s=120, zorder=3, edgecolors=_BG, linewidths=1.5)

    # Connect dots with lines
    for i in range(len(xs) - 1):
        ax.plot(
            [xs[i], xs[i + 1]], [ys[i], ys[i + 1]],
            color=_GRID, linewidth=1, alpha=0.5, zorder=1,
        )

    # Label each point with topic
    for x, y, topic in zip(xs, ys, topics):
        ax.annotate(
            topic, (x, y), textcoords="offset points", xytext=(0, 12),
            ha="center", fontsize=7, color=_MUTED,
        )

    ax.set_yticks(range(len(unique_speakers)))
    ax.set_yticklabels(unique_speakers)
    ax.set_xlabel("Segment")
    ax.set_title("Conversation Flow", color=_CYAN, fontsize=13, fontweight="bold", pad=12)
    ax.grid(axis="x", linestyle="--")
    ax.tick_params(axis="y", length=0)

    plt.tight_layout()

    b64 = _fig_to_base64(fig)
    png = _fig_to_png(fig, output_path) if output_path else None
    plt.close(fig)
    return (b64, png)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def generate_all_charts(
    data: Dict[str, Any],
    output_dir: Optional[str] = None,
) -> Dict[str, Optional[Tuple[str, Optional[str]]]]:
    """Generate all available charts and return a dict of results.

    Keys: ``"topics"``, ``"speakers"``, ``"flow"``
    Values: ``(base64_data_uri, png_path_or_None)`` or ``None``
    """
    out = Path(output_dir) if output_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    return {
        "topics": generate_topic_importance_chart(
            data, str(out / "chart_topics.png") if out else None,
        ),
        "speakers": generate_speaker_distribution_chart(
            data, str(out / "chart_speakers.png") if out else None,
        ),
        "flow": generate_conversation_flow_chart(
            data, str(out / "chart_flow.png") if out else None,
        ),
    }
