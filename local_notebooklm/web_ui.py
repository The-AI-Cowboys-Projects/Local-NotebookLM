import os
import shutil
import subprocess
import time
import gradio as gr
import argparse
from local_notebooklm.processor import podcast_processor
from local_notebooklm.steps.helpers import LengthType, FormatType, StyleType, SkipToOptions
from local_notebooklm.notebook_manager import NotebookManager


# ---------------------------------------------------------------------------
# Ollama auto-start
# ---------------------------------------------------------------------------

def _ensure_ollama():
    """Start Ollama if it isn't already running. Returns True if reachable."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        pass

    if not shutil.which("ollama"):
        print("[web_ui] Ollama binary not found — skipping auto-start.")
        return False

    print("[web_ui] Ollama not responding — starting ollama serve ...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(15):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            print("[web_ui] Ollama is ready.")
            return True
        except Exception:
            pass

    print("[web_ui] Ollama did not start within 15 seconds.")
    return False


# ---------------------------------------------------------------------------
# Cyberpunk Neon Dark Theme
# ---------------------------------------------------------------------------

def _build_cyberpunk_theme():
    """Build a gr.themes.Base with cyberpunk neon dark palette."""
    return gr.themes.Base(
        primary_hue=gr.themes.Color(
            c50="#e0fffe", c100="#b3fffc", c200="#80fff9",
            c300="#4dfff6", c400="#26f5ef", c500="#00f0ff",
            c600="#3bd6c6", c700="#0098a8", c800="#006d7d",
            c900="#004452", c950="#002a33",
        ),
        secondary_hue=gr.themes.Color(
            c50="#ffe5f5", c100="#ffb3e2", c200="#ff80cf",
            c300="#ff4dbc", c400="#ff26af", c500="#ff00aa",
            c600="#dd368a", c700="#a80075", c800="#7d005a",
            c900="#52003d", c950="#330026",
        ),
        neutral_hue=gr.themes.Color(
            c50="#e8e8f0", c100="#c4c4d4", c200="#9e9eb8",
            c300="#78789c", c400="#565680", c500="#3a3a5c",
            c600="#2a2a44", c700="#1e1e35", c800="#16162a",
            c900="#0f0f1e", c950="#000000",
        ),
        font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "Consolas", "monospace"],
    ).set(
        body_background_fill="#000000",
        body_background_fill_dark="#000000",
        body_text_color="#e0e0f0",
        body_text_color_dark="#e0e0f0",
        body_text_color_subdued="#8888aa",
        body_text_color_subdued_dark="#8888aa",
        background_fill_primary="#0f0f1e",
        background_fill_primary_dark="#0f0f1e",
        background_fill_secondary="#16162a",
        background_fill_secondary_dark="#16162a",
        border_color_primary="#1e1e40",
        border_color_primary_dark="#1e1e40",
        border_color_accent="#00f0ff40",
        border_color_accent_dark="#00f0ff40",
        block_background_fill="#12122200",
        block_background_fill_dark="#12122200",
        block_border_color="#1e1e40",
        block_border_color_dark="#1e1e40",
        block_label_background_fill="#16162a",
        block_label_background_fill_dark="#16162a",
        block_label_text_color="#00f0ff",
        block_label_text_color_dark="#00f0ff",
        block_title_text_color="#00f0ff",
        block_title_text_color_dark="#00f0ff",
        input_background_fill="#0f0f1e",
        input_background_fill_dark="#0f0f1e",
        input_border_color="#1e1e40",
        input_border_color_dark="#1e1e40",
        input_border_color_focus="#00f0ff",
        input_border_color_focus_dark="#00f0ff",
        input_placeholder_color="#555577",
        input_placeholder_color_dark="#555577",
        button_primary_background_fill="#00f0ff",
        button_primary_background_fill_dark="#00f0ff",
        button_primary_background_fill_hover="#3bd6c6",
        button_primary_background_fill_hover_dark="#3bd6c6",
        button_primary_text_color="#000000",
        button_primary_text_color_dark="#000000",
        button_primary_border_color="#00f0ff",
        button_primary_border_color_dark="#00f0ff",
        button_secondary_background_fill="#1e1e35",
        button_secondary_background_fill_dark="#1e1e35",
        button_secondary_text_color="#e0e0f0",
        button_secondary_text_color_dark="#e0e0f0",
        button_secondary_border_color="#2a2a55",
        button_secondary_border_color_dark="#2a2a55",
        shadow_drop="0 2px 12px rgba(0, 240, 255, 0.08)",
        shadow_drop_lg="0 4px 24px rgba(0, 240, 255, 0.12)",
    )


# ---------------------------------------------------------------------------
# Refined Cyberpunk CSS
# ---------------------------------------------------------------------------

CYBERPUNK_CSS = """
/* ── Google Font preload ─────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root variables ──────────────────────────────────────────── */
:root {
    --neon-cyan: #00f0ff;
    --neon-teal: #3bd6c6;
    --neon-magenta: #ff00aa;
    --neon-pink: #dd368a;
    --neon-purple: #b400ff;
    --true-black: #000000;
    --dark-bg: #000000;
    --card-bg: #0a0a14;
    --card-border: #1e1e40;
    --text-primary: #e0e0f0;
    --text-muted: #8888aa;
    --glow-cyan: 0 0 8px rgba(0,240,255,0.25), 0 0 20px rgba(0,240,255,0.08);
    --glow-teal: 0 0 8px rgba(59,214,198,0.25), 0 0 20px rgba(59,214,198,0.08);
    --glow-magenta: 0 0 8px rgba(255,0,170,0.25), 0 0 20px rgba(255,0,170,0.08);
    --glow-pink: 0 0 8px rgba(221,54,138,0.25), 0 0 20px rgba(221,54,138,0.08);
    --panel-bg: #06060e;
    --panel-border: #1a1a38;
}

/* ── Animated background ─────────────────────────────────────── */
.gradio-container {
    background: linear-gradient(135deg, #000000 0%, #0a0a18 40%, #080814 60%, #000000 100%) !important;
    background-size: 400% 400% !important;
    animation: bgShift 20s ease infinite !important;
    min-height: 100vh;
}
@keyframes bgShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* ── Scan-line overlay (subtle) ──────────────────────────────── */
.gradio-container::before {
    content: "";
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 240, 255, 0.01) 2px,
        rgba(0, 240, 255, 0.01) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* ── Slim header bar ─────────────────────────────────────────── */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 1.5rem;
    border-bottom: 1px solid var(--panel-border);
    background: var(--panel-bg);
}
.header-bar .title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    background: linear-gradient(90deg, var(--neon-cyan), var(--neon-teal), var(--neon-pink));
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite;
}
@keyframes shimmer {
    0% { background-position: 0% center; }
    100% { background-position: 200% center; }
}
.header-bar .pipeline-chips {
    display: flex;
    gap: 0.35rem;
    align-items: center;
}
.header-bar .pipeline-chips .chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--text-muted);
    padding: 0.2rem 0.5rem;
    border: 1px solid var(--card-border);
    border-radius: 4px;
    background: var(--card-bg);
    letter-spacing: 0.05em;
}
.header-bar .pipeline-chips .arrow {
    color: var(--neon-pink);
    font-size: 0.7rem;
    opacity: 0.4;
}

/* ── 3-Panel layout ──────────────────────────────────────────── */
.panel {
    background: var(--panel-bg) !important;
    border: none !important;
    min-height: calc(100vh - 100px);
    padding: 0 !important;
}
.panel-left {
    border-right: 1px solid var(--panel-border) !important;
}
.panel-right {
    border-left: 1px solid var(--panel-border) !important;
}
.panel-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--neon-cyan);
    padding: 0.9rem 1rem 0.6rem;
    border-bottom: 1px solid rgba(0, 240, 255, 0.12);
    margin-bottom: 0.5rem;
}
.panel-content {
    padding: 0.5rem 0.8rem 1rem;
}
.panel-empty {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: var(--text-muted);
    text-align: center;
    padding: 2rem 1rem;
    line-height: 1.6;
}

/* ── Section cards ───────────────────────────────────────────── */
.cyber-card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 10px !important;
    padding: 1.2rem !important;
    position: relative;
    transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}
.cyber-card:hover {
    border-color: rgba(59, 214, 198, 0.25) !important;
    box-shadow: var(--glow-teal);
    transform: scale(1.005);
}
.cyber-card-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--neon-cyan) !important;
    margin-bottom: 0.8rem !important;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(0, 240, 255, 0.15);
}

/* ── Generate button — gradient sweep ────────────────────────── */
#generate-btn {
    margin-top: 0.5rem;
}
#generate-btn button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    padding: 0.85rem 1.5rem !important;
    border-radius: 8px !important;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease !important;
    background: linear-gradient(90deg, #00f0ff, #3bd6c6, #00f0ff) !important;
    background-size: 200% 100% !important;
    animation: gradientSweep 3s ease-in-out infinite !important;
}
#generate-btn button:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 16px rgba(0,240,255,0.4), 0 0 32px rgba(59,214,198,0.2) !important;
}
@keyframes gradientSweep {
    0% { background-position: 0% center; }
    50% { background-position: 100% center; }
    100% { background-position: 0% center; }
}

/* ── Status output — typing cursor effect ────────────────────── */
#status-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    border: 1px solid var(--card-border) !important;
    background: var(--card-bg) !important;
    transition: border-color 0.3s, box-shadow 0.3s;
}
#status-box.success textarea {
    border-color: #00ff88 !important;
    box-shadow: 0 0 8px rgba(0,255,136,0.15);
}
#status-box.error textarea {
    border-color: #ff3366 !important;
    box-shadow: 0 0 8px rgba(255,51,102,0.15);
}

/* ── Audio player dark treatment ─────────────────────────────── */
#audio-player {
    border: 1px solid var(--card-border) !important;
    border-radius: 10px !important;
    background: var(--card-bg) !important;
    overflow: hidden;
}
#audio-player audio {
    filter: hue-rotate(160deg) saturate(1.5);
}

/* ── Accordion neon styling ──────────────────────────────────── */
.cyber-accordion .label-wrap {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.08em;
    border-bottom: 1px solid transparent !important;
    transition: all 0.3s ease;
    color: var(--text-muted) !important;
}
.cyber-accordion .label-wrap:hover {
    color: var(--neon-pink) !important;
    border-bottom-color: rgba(221, 54, 138, 0.3) !important;
}
.cyber-accordion .label-wrap .icon {
    color: var(--neon-teal) !important;
}

/* ── File upload dashed neon border ──────────────────────────── */
.cyber-upload .upload-container,
.cyber-upload [data-testid="droparea"] {
    border: 2px dashed rgba(0, 240, 255, 0.2) !important;
    border-radius: 8px !important;
    background: rgba(0, 240, 255, 0.015) !important;
    transition: all 0.3s ease;
}
.cyber-upload .upload-container:hover,
.cyber-upload [data-testid="droparea"]:hover {
    border-color: rgba(59, 214, 198, 0.45) !important;
    background: rgba(59, 214, 198, 0.03) !important;
    box-shadow: var(--glow-teal);
}

/* ── Dropdown styling ────────────────────────────────────────── */
.gradio-container select,
.gradio-container .wrap.svelte-1s0gk1z,
.gradio-container .secondary-wrap {
    background: var(--card-bg) !important;
    border-color: var(--card-border) !important;
    color: var(--text-primary) !important;
}

/* ── Output card grid ────────────────────────────────────────── */
.output-selector label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em;
}
.output-selector .wrap {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 0.5rem !important;
}
.output-selector .wrap > label {
    display: flex !important;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 0.7rem !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 8px !important;
    background: var(--card-bg) !important;
    cursor: pointer;
    transition: all 0.25s ease;
}
.output-selector .wrap > label:hover {
    border-color: var(--neon-teal) !important;
    box-shadow: var(--glow-teal);
}
.output-selector .wrap > label:has(input:checked) {
    border-color: var(--neon-cyan) !important;
    background: rgba(0, 240, 255, 0.06) !important;
}
.output-selector input[type="checkbox"] {
    accent-color: var(--neon-cyan) !important;
}

/* ── Scrollbar ───────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--dark-bg); }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--neon-teal), var(--neon-pink));
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { opacity: 0.8; }

/* ── Footer ──────────────────────────────────────────────────── */
.cyber-footer {
    text-align: center;
    padding: 1rem 1rem 1.5rem;
    margin-top: 0;
}
.cyber-footer .divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--neon-teal), var(--neon-cyan), var(--neon-pink), var(--neon-magenta), transparent);
    margin-bottom: 0.8rem;
}
.cyber-footer p {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-muted);
    letter-spacing: 0.1em;
}
.cyber-footer a {
    color: var(--neon-cyan) !important;
    text-decoration: none !important;
    transition: color 0.3s, text-shadow 0.3s;
}
.cyber-footer a:hover {
    color: var(--neon-pink) !important;
    text-shadow: 0 0 8px rgba(221,54,138,0.4);
}

/* ── Input fields ────────────────────────────────────────────── */
.gradio-container textarea,
.gradio-container input[type="text"] {
    caret-color: var(--neon-cyan) !important;
}
.gradio-container textarea:focus,
.gradio-container input[type="text"]:focus {
    box-shadow: 0 0 6px rgba(0,240,255,0.12) !important;
}

/* ── Group wrapper ───────────────────────────────────────────── */
.gradio-group {
    background: transparent !important;
    border: none !important;
}

/* ── Results fade-in ─────────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.results-section {
    animation: fadeInUp 0.5s ease-out;
}

/* ── Downloads row ───────────────────────────────────────────── */
.download-row {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
}
.download-row > div {
    flex: 1;
    min-width: 140px;
}

/* ── Center workspace empty state ────────────────────────────── */
.center-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
    text-align: center;
}
.center-empty .icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    opacity: 0.3;
}
.center-empty p {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    line-height: 1.6;
}

/* ── Notebook bar ───────────────────────────────────────────── */
.notebook-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 1rem;
    border-bottom: 1px solid var(--panel-border);
    background: var(--panel-bg);
}
.notebook-bar .nb-btn button {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    padding: 0.35rem 0.7rem !important;
    letter-spacing: 0.06em !important;
}

/* ── Source list in left panel ──────────────────────────────── */
.source-list {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    padding: 0.4rem 0;
}
.source-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 0.65rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--text-primary);
    transition: border-color 0.25s, box-shadow 0.25s;
}
.source-item:hover {
    border-color: rgba(59, 214, 198, 0.3);
    box-shadow: var(--glow-teal);
}
.source-icon {
    flex-shrink: 0;
    width: 18px;
    text-align: center;
    color: var(--neon-cyan);
    font-size: 0.82rem;
}
.source-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.source-empty {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--text-muted);
    text-align: center;
    padding: 1rem 0.5rem;
}
"""


# ---------------------------------------------------------------------------
# Hero / Pipeline / Footer HTML fragments
# ---------------------------------------------------------------------------

HEADER_HTML = """
<div class="header-bar">
    <span class="title">Local-NotebookLM</span>
    <div class="pipeline-chips">
        <span class="chip">1 Extract</span>
        <span class="arrow">&rarr;</span>
        <span class="chip">2 Script</span>
        <span class="arrow">&rarr;</span>
        <span class="chip">3 Prepare</span>
        <span class="arrow">&rarr;</span>
        <span class="chip">4 Audio</span>
        <span class="arrow">&rarr;</span>
        <span class="chip">5 Visual</span>
    </div>
</div>
"""

FOOTER_HTML = """
<div class="cyber-footer">
    <div class="divider"></div>
    <p>Local-NotebookLM by G&ouml;kdeniz G&uuml;lmez &nbsp;&bull;&nbsp;
       <a href="https://github.com/Goekdeniz-Guelmez/Local-NotebookLM" target="_blank">GitHub Repository</a>
    </p>
</div>
"""


# ---------------------------------------------------------------------------
# Notebook manager (global singleton)
# ---------------------------------------------------------------------------

_notebook_mgr = NotebookManager()


# ---------------------------------------------------------------------------
# Session restore — reload outputs from a notebook directory
# ---------------------------------------------------------------------------

def _load_results_from_dir(d: str):
    """Scan a directory for pipeline outputs and return an 8-tuple.

    Returns ``None`` when nothing is found.
    """
    if not os.path.isdir(d):
        return None

    audio_path = None
    candidate = os.path.join(d, "podcast.wav")
    if os.path.exists(candidate):
        audio_path = candidate

    file_contents = {}
    for rel in ["step1/extracted_text.txt", "step1/clean_extracted_text.txt", "step3/podcast_ready_data.txt"]:
        fp = os.path.join(d, rel)
        if os.path.exists(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    c = f.read()
                    file_contents[rel] = c[:1000] + "..." if len(c) > 1000 else c
            except Exception:
                pass

    infographic_html = None
    infographic_file = None
    infographic_path = os.path.join(d, "step5", "infographic.html")
    if os.path.exists(infographic_path):
        try:
            with open(infographic_path, 'r', encoding='utf-8') as f:
                infographic_html = f'<iframe srcdoc="{f.read().replace(chr(34), "&quot;").replace(chr(10), "&#10;")}" style="width:100%;height:600px;border:1px solid #1e1e40;border-radius:8px;" sandbox="allow-same-origin"></iframe>'
            infographic_file = infographic_path
        except Exception:
            pass

    pptx_file = None
    pptx_path = os.path.join(d, "step5", "infographic.pptx")
    if os.path.exists(pptx_path):
        pptx_file = pptx_path

    has_anything = audio_path or infographic_html or pptx_file or file_contents
    if not has_anything:
        return None

    parts = []
    if audio_path:
        parts.append("Audio")
    if infographic_html:
        parts.append("Infographic HTML")
    if os.path.exists(os.path.join(d, "step5", "infographic.png")):
        parts.append("Infographic PNG")
    if pptx_file:
        parts.append("PPTX")

    status = f"Previous results loaded: {', '.join(parts)}" if parts else ""

    return (
        status,
        audio_path,
        file_contents.get("step1/extracted_text.txt", ""),
        file_contents.get("step1/clean_extracted_text.txt", ""),
        file_contents.get("step3/podcast_ready_data.txt", ""),
        infographic_html,
        infographic_file,
        pptx_file,
    )


# ---------------------------------------------------------------------------
# Notebook callbacks
# ---------------------------------------------------------------------------

def _dropdown_choices():
    """Return Gradio-compatible ``(label, value)`` list for the notebook dropdown."""
    return [(nb["name"], nb["id"]) for nb in _notebook_mgr.list_notebooks()]


def _build_sources_html(sources: list[dict]) -> str:
    """Render source list as styled HTML cards."""
    if not sources:
        return '<div class="source-empty">No sources yet — upload a file or paste a URL</div>'
    items = []
    for i, s in enumerate(sources):
        if s.get("type") == "file":
            icon = "&#128196;"  # document emoji as fallback
            label = s.get("filename", "unknown")
        else:
            icon = "&#128279;"  # link emoji
            label = s.get("url", "unknown")
        items.append(
            f'<div class="source-item">'
            f'<span class="source-icon">{icon}</span>'
            f'<span class="source-name" title="{label}">{label}</span>'
            f'</div>'
        )
    return '<div class="source-list">' + "".join(items) + '</div>'


def _empty_outputs():
    """8-tuple of empty/cleared outputs."""
    return ("", None, "", "", "", None, None, None)


def _on_notebook_switch(notebook_id):
    """Load sources, results, and settings for the selected notebook.

    Returns updates for:
      sources_display, result_message, audio_output, extracted_text,
      clean_text, audio_script, infographic_preview, infographic_download,
      pptx_download, format, length, style, language, outputs_to_generate,
      output_dir
    """
    if not notebook_id:
        return (
            _build_sources_html([]),
            *_empty_outputs(),
            "podcast", "medium", "normal", "english",
            ["Podcast Audio", "Infographic HTML", "Infographic PNG", "PPTX Slides"],
            "",
        )

    _notebook_mgr.set_default_notebook_id(notebook_id)
    sources = _notebook_mgr.get_sources(notebook_id)
    settings = _notebook_mgr.get_settings(notebook_id)
    nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)

    sources_html = _build_sources_html(sources)

    results = _load_results_from_dir(nb_dir)
    if results is None:
        results = _empty_outputs()

    return (
        sources_html,
        *results,
        settings.get("format", "podcast"),
        settings.get("length", "medium"),
        settings.get("style", "normal"),
        settings.get("language", "english"),
        settings.get("outputs_to_generate", ["Podcast Audio", "Infographic HTML", "Infographic PNG", "PPTX Slides"]),
        nb_dir,
    )


def _on_create_notebook(name):
    """Create a notebook.  Returns updated dropdown + selected value + cleared name input."""
    nb_id = _notebook_mgr.create_notebook(name)
    choices = _dropdown_choices()
    return gr.update(choices=choices, value=nb_id), ""


def _on_rename_notebook(notebook_id, new_name):
    """Rename the current notebook.  Returns updated dropdown."""
    if not notebook_id or not new_name or not new_name.strip():
        return gr.update()
    try:
        _notebook_mgr.rename_notebook(notebook_id, new_name)
    except (KeyError, ValueError):
        return gr.update()
    choices = _dropdown_choices()
    return gr.update(choices=choices, value=notebook_id)


def _on_delete_notebook(notebook_id):
    """Delete notebook.  Returns updated dropdown + value to switch to."""
    if not notebook_id:
        return gr.update()
    next_id = _notebook_mgr.delete_notebook(notebook_id)
    choices = _dropdown_choices()
    return gr.update(choices=choices, value=next_id)


def _on_file_upload(file, notebook_id):
    """Copy uploaded file into the notebook sources.  Returns sources HTML."""
    if file is None or not notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id) if notebook_id else []
        return _build_sources_html(sources)
    file_path = file.name if hasattr(file, "name") else file
    original_name = os.path.basename(file_path)
    _notebook_mgr.add_file_source(notebook_id, file_path, original_name)
    return _build_sources_html(_notebook_mgr.get_sources(notebook_id))


def _on_url_add(url, notebook_id):
    """Record URL in notebook metadata.  Returns sources HTML + cleared URL input."""
    if not url or not url.strip() or not notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id) if notebook_id else []
        return _build_sources_html(sources), url or ""
    _notebook_mgr.add_url_source(notebook_id, url.strip())
    return _build_sources_html(_notebook_mgr.get_sources(notebook_id)), ""


def _on_settings_change(notebook_id, fmt, length, style, lang, outputs):
    """Silently save settings to notebook metadata."""
    if not notebook_id:
        return
    _notebook_mgr.save_settings(notebook_id, {
        "format": fmt,
        "length": length,
        "style": style,
        "language": lang,
        "outputs_to_generate": outputs,
    })


def _on_app_load():
    """Called on page load — switch to the default notebook."""
    default_id = _notebook_mgr.get_default_notebook_id()
    return default_id


# ---------------------------------------------------------------------------
# Processing logic
# ---------------------------------------------------------------------------

def _empty_result(status_msg):
    """Return a result tuple with only a status message and empty outputs."""
    return (status_msg, None, "", "", "", None, None, None)


def process_podcast(pdf_file, url_input, config_file, format_type, length, style, language, additional_preference, output_dir, skip_to, outputs_to_generate):
    """Generator that yields progress updates then a final result tuple."""

    # Resolve input: URL takes priority over file upload
    if url_input and url_input.strip():
        input_path = url_input.strip()
    elif pdf_file is not None:
        input_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    elif skip_to is not None and skip_to > 1:
        input_path = None
    else:
        yield _empty_result("Please upload a document or enter a URL.")
        return

    if not output_dir:
        output_dir = "./local_notebooklm/web_ui/output"

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        yield _empty_result(f"Failed to create output directory: {str(e)}")
        return

    if not outputs_to_generate:
        yield _empty_result("Please select at least one output to generate.")
        return

    try:
        if config_file is None:
            config_path = "./ollama_config.json"
        else:
            config_path = config_file.name if hasattr(config_file, 'name') else config_file

        selected = ", ".join(outputs_to_generate)
        print(f"Processing with output_dir: {output_dir}")
        print(f"Generating: {selected}")

        # Determine which steps will run
        want_audio = "Podcast Audio" in outputs_to_generate
        want_html = "Infographic HTML" in outputs_to_generate
        want_png = "Infographic PNG" in outputs_to_generate
        want_pptx = "PPTX Slides" in outputs_to_generate
        want_any_infographic = want_html or want_png or want_pptx

        # Calculate total steps
        total_steps = 3  # Steps 1-3 always run
        if want_audio:
            total_steps += 1
        if want_any_infographic:
            total_steps += 1

        # Show initial status
        yield _empty_result(f"[1/{total_steps}] Extracting text from input...")

        success, result = podcast_processor(
            input_path=input_path,
            config_path=config_path,
            format_type=format_type,
            length=length,
            style=style,
            preference=additional_preference if additional_preference else None,
            output_dir=output_dir,
            language=language,
            skip_to=skip_to,
            outputs=outputs_to_generate,
        )

        if not success:
            yield _empty_result(f"Failed: {result}")
            return

        # --- Collect results ---
        audio_path = None
        if want_audio:
            candidate = os.path.join(output_dir, "podcast.wav")
            if os.path.exists(candidate):
                audio_path = candidate

        file_contents = {}
        for file in ["step1/extracted_text.txt", "step1/clean_extracted_text.txt", "step3/podcast_ready_data.txt"]:
            full_path = os.path.join(output_dir, file)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_contents[file] = content[:1000] + "..." if len(content) > 1000 else content
                except Exception as e:
                    file_contents[file] = f"Error reading file: {str(e)}"

        infographic_html = None
        infographic_file = None
        infographic_path = os.path.join(output_dir, "step5", "infographic.html")
        if os.path.exists(infographic_path):
            try:
                with open(infographic_path, 'r', encoding='utf-8') as f:
                    infographic_html = f'<iframe srcdoc="{f.read().replace(chr(34), "&quot;").replace(chr(10), "&#10;")}" style="width:100%;height:600px;border:1px solid #1e1e40;border-radius:8px;" sandbox="allow-same-origin"></iframe>'
                infographic_file = infographic_path
            except Exception:
                pass

        pptx_file = None
        pptx_path = os.path.join(output_dir, "step5", "infographic.pptx")
        if os.path.exists(pptx_path):
            pptx_file = pptx_path

        # Build success message listing what was actually produced
        generated_list = []
        if audio_path:
            generated_list.append("Audio")
        if infographic_html:
            generated_list.append("Infographic HTML")
        png_path = os.path.join(output_dir, "step5", "infographic.png")
        if os.path.exists(png_path):
            generated_list.append("Infographic PNG")
        if pptx_file:
            generated_list.append("PPTX")

        status_msg = f"Complete — Generated: {', '.join(generated_list)}" if generated_list else "Complete."

        yield (
            status_msg,
            audio_path,
            file_contents.get("step1/extracted_text.txt", ""),
            file_contents.get("step1/clean_extracted_text.txt", ""),
            file_contents.get("step3/podcast_ready_data.txt", ""),
            infographic_html,
            infographic_file,
            pptx_file,
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        yield _empty_result(f"An error occurred: {str(e)}\n\nDetails:\n{error_details}")


# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------

def create_gradio_ui():
    format_options = list(FormatType.__args__) if hasattr(FormatType, '__args__') else ["podcast"]
    length_options = list(LengthType.__args__) if hasattr(LengthType, '__args__') else ["medium"]
    style_options = list(StyleType.__args__) if hasattr(StyleType, '__args__') else ["conversational"]

    theme = _build_cyberpunk_theme()

    # Pre-compute initial notebook state
    initial_choices = _dropdown_choices()
    initial_default = _notebook_mgr.get_default_notebook_id()

    with gr.Blocks(title="Local-NotebookLM", analytics_enabled=False) as app:

        # ── Header bar ────────────────────────────────────────
        gr.HTML(HEADER_HTML)

        # ── Notebook bar ──────────────────────────────────────
        with gr.Row(elem_classes="notebook-bar"):
            notebook_selector = gr.Dropdown(
                choices=initial_choices,
                value=initial_default,
                label="Notebook",
                scale=3,
                container=False,
            )
            notebook_name_input = gr.Textbox(
                placeholder="notebook name...",
                scale=2,
                container=False,
                show_label=False,
            )
            btn_new = gr.Button("+ New", size="sm", variant="secondary", elem_classes="nb-btn", scale=0)
            btn_rename = gr.Button("Rename", size="sm", variant="secondary", elem_classes="nb-btn", scale=0)
            btn_delete = gr.Button("Delete", size="sm", variant="stop", elem_classes="nb-btn", scale=0)

        # ── 3-Panel layout ────────────────────────────────────
        with gr.Row(equal_height=True):

            # ═══════════════════════════════════════════════
            # LEFT PANEL — Sources
            # ═══════════════════════════════════════════════
            with gr.Column(scale=1, min_width=280, elem_classes="panel panel-left"):
                gr.HTML('<div class="panel-header">Sources</div>')
                with gr.Group(elem_classes="panel-content"):
                    sources_display = gr.HTML(
                        value=_build_sources_html([]),
                    )
                    pdf_file = gr.File(
                        label="Upload Document",
                        file_types=[".pdf", ".docx", ".pptx", ".txt", ".md"],
                        elem_classes="cyber-upload",
                    )
                    url_input = gr.Textbox(
                        label="URL",
                        placeholder="https://youtube.com/watch?v=... or article URL",
                        info="YouTube, articles, and web pages",
                    )
                    with gr.Accordion("Config JSON", open=False, elem_classes="cyber-accordion"):
                        config_file = gr.File(
                            label="Config (Optional)",
                            file_types=[".json"],
                            elem_classes="cyber-upload",
                        )

            # ═══════════════════════════════════════════════
            # CENTER PANEL — Workspace
            # ═══════════════════════════════════════════════
            with gr.Column(scale=2, min_width=400, elem_classes="panel"):

                # Status bar
                result_message = gr.Textbox(
                    label="Status",
                    elem_id="status-box",
                )

                # Audio output
                with gr.Group(elem_classes="results-section"):
                    audio_output = gr.Audio(
                        label="Podcast Audio",
                        type="filepath",
                        elem_id="audio-player",
                    )

                # Infographic preview
                infographic_preview = gr.HTML(label="Infographic Preview")

                # Downloads
                with gr.Row(elem_classes="download-row"):
                    infographic_download = gr.File(label="Infographic HTML")
                    pptx_download = gr.File(label="PPTX Slides")

                # Pipeline data (collapsed)
                with gr.Accordion("Extracted Text", open=False, elem_classes="cyber-accordion"):
                    extracted_text = gr.Textbox(label="Extracted Text", lines=8)
                with gr.Accordion("Clean Text", open=False, elem_classes="cyber-accordion"):
                    clean_text = gr.Textbox(label="Clean Extracted Text", lines=8)
                with gr.Accordion("Podcast Script", open=False, elem_classes="cyber-accordion"):
                    audio_script = gr.Textbox(label="Podcast Script", lines=10)

            # ═══════════════════════════════════════════════
            # RIGHT PANEL — Studio
            # ═══════════════════════════════════════════════
            with gr.Column(scale=1, min_width=280, elem_classes="panel panel-right"):
                gr.HTML('<div class="panel-header">Studio</div>')
                with gr.Group(elem_classes="panel-content"):

                    # Output type cards
                    outputs_to_generate = gr.CheckboxGroup(
                        choices=["Podcast Audio", "Infographic HTML", "Infographic PNG", "PPTX Slides"],
                        value=["Podcast Audio", "Infographic HTML", "Infographic PNG", "PPTX Slides"],
                        label="Outputs",
                        elem_classes="output-selector",
                    )

                    # Settings 2x2 grid
                    gr.HTML('<div class="cyber-card-label" style="margin-top:0.8rem">// Settings</div>')
                    with gr.Row():
                        format_type = gr.Dropdown(
                            choices=format_options,
                            label="Format",
                            value=format_options[0],
                        )
                        length = gr.Dropdown(
                            choices=length_options,
                            label="Length",
                            value=length_options[1] if len(length_options) > 1 else length_options[0],
                        )
                    with gr.Row():
                        style = gr.Dropdown(
                            choices=style_options,
                            label="Style",
                            value=style_options[0],
                        )
                        language = gr.Dropdown(
                            choices=["english", "german", "french", "spanish", "italian", "portuguese"],
                            label="Language",
                            value="english",
                        )

                    # Generate button
                    generate_button = gr.Button(
                        "Generate",
                        variant="primary",
                        elem_id="generate-btn",
                    )

                    # Advanced options
                    with gr.Accordion("Advanced", open=False, elem_classes="cyber-accordion"):
                        additional_preference = gr.Textbox(
                            label="Preferences",
                            placeholder="Focus on key points, provide examples...",
                        )
                        output_dir = gr.Textbox(
                            label="Output Directory",
                            value="",
                            visible=False,
                        )
                        skip_to = gr.Dropdown(
                            choices=SkipToOptions,
                            label="Skip to Step",
                            value=None,
                        )

                    gr.HTML('<p class="panel-empty">Select outputs and click Generate</p>')

        # ── Footer ────────────────────────────────────────────
        gr.HTML(FOOTER_HTML)

        # ── All output components (order matches _on_notebook_switch) ──
        switch_outputs = [
            sources_display,
            result_message, audio_output, extracted_text, clean_text,
            audio_script, infographic_preview, infographic_download, pptx_download,
            format_type, length, style, language, outputs_to_generate,
            output_dir,
        ]

        # ── Wiring — Notebook bar ─────────────────────────────
        notebook_selector.change(
            fn=_on_notebook_switch,
            inputs=[notebook_selector],
            outputs=switch_outputs,
            show_progress="hidden",
        )

        btn_new.click(
            fn=_on_create_notebook,
            inputs=[notebook_name_input],
            outputs=[notebook_selector, notebook_name_input],
            show_progress="hidden",
        ).then(
            fn=_on_notebook_switch,
            inputs=[notebook_selector],
            outputs=switch_outputs,
            show_progress="hidden",
        )

        btn_rename.click(
            fn=_on_rename_notebook,
            inputs=[notebook_selector, notebook_name_input],
            outputs=[notebook_selector],
            show_progress="hidden",
        )

        btn_delete.click(
            fn=_on_delete_notebook,
            inputs=[notebook_selector],
            outputs=[notebook_selector],
            show_progress="hidden",
        ).then(
            fn=_on_notebook_switch,
            inputs=[notebook_selector],
            outputs=switch_outputs,
            show_progress="hidden",
        )

        # ── Wiring — Source uploads ───────────────────────────
        pdf_file.change(
            fn=_on_file_upload,
            inputs=[pdf_file, notebook_selector],
            outputs=[sources_display],
            show_progress="hidden",
        )

        url_input.submit(
            fn=_on_url_add,
            inputs=[url_input, notebook_selector],
            outputs=[sources_display, url_input],
            show_progress="hidden",
        )

        # ── Wiring — Auto-save settings on change ────────────
        for setting_component in [format_type, length, style, language, outputs_to_generate]:
            setting_component.change(
                fn=_on_settings_change,
                inputs=[notebook_selector, format_type, length, style, language, outputs_to_generate],
                outputs=None,
                show_progress="hidden",
            )

        # ── Wiring — Generate ─────────────────────────────────
        generate_button.click(
            fn=process_podcast,
            inputs=[pdf_file, url_input, config_file, format_type, length, style, language, additional_preference, output_dir, skip_to, outputs_to_generate],
            outputs=[result_message, audio_output, extracted_text, clean_text, audio_script, infographic_preview, infographic_download, pptx_download],
            show_progress="hidden",
        )

        # ── Restore notebook on page load / refresh ───────────
        app.load(
            fn=_on_app_load,
            inputs=None,
            outputs=[notebook_selector],
            show_progress="hidden",
        ).then(
            fn=_on_notebook_switch,
            inputs=[notebook_selector],
            outputs=switch_outputs,
            show_progress="hidden",
        )

    # Enable queue for session resilience
    app.queue()

    return app


def run_gradio_ui(share=False, port=None):
    _ensure_ollama()
    theme = _build_cyberpunk_theme()
    app = create_gradio_ui()
    app.launch(share=share, server_port=port, server_name="0.0.0.0", theme=theme, css=CYBERPUNK_CSS)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run Local-NotebookLM web UI")
    parser.add_argument("--share", action="store_true", help="Create a shareable link")
    parser.add_argument("--port", type=int, default=None, help="Port to run the interface on")

    return parser.parse_args()

def main():
    args = parse_arguments()
    run_gradio_ui(share=args.share, port=args.port)

if __name__ == "__main__" or __name__ == "local_notebooklm.web_ui":
    main()
