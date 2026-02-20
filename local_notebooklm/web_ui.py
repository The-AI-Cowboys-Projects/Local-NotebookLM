import logging as _logging
import os
import shutil
import subprocess
import time
import gradio as gr
import argparse
from local_notebooklm.steps.helpers import LengthType, FormatType, StyleType, SkipToOptions
from local_notebooklm.notebook_manager import NotebookManager
from local_notebooklm.pipeline_runner import (
    PipelineJob, start_job, get_job, is_running, cancel_job, remove_job, load_stale_state,
)

_log = _logging.getLogger(__name__)


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
        font=[gr.themes.GoogleFont("IBM Plex Sans"), "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "Consolas", "monospace"],
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
        shadow_drop="0 2px 6px rgba(0, 0, 0, 0.3)",
        shadow_drop_lg="0 4px 12px rgba(0, 0, 0, 0.3)",
    )


# ---------------------------------------------------------------------------
# Refined Cyberpunk CSS
# ---------------------------------------------------------------------------

CYBERPUNK_CSS = """
/* ── IBM Plex Font preload ─────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;700&display=swap');

/* ── Carbon Design Tokens + Neon Palette ───────────────────────── */
:root {
    /* ── Neon palette (kept) ─────────────────────────────────── */
    --neon-cyan: #00f0ff;
    --neon-teal: #3bd6c6;
    --neon-magenta: #ff00aa;
    --neon-pink: #dd368a;
    --neon-purple: #b400ff;
    --neon-red: #ff3a3a;

    /* ── Carbon spacing scale (rem-based) ────────────────────── */
    --cds-spacing-01: 0.125rem;
    --cds-spacing-02: 0.25rem;
    --cds-spacing-03: 0.5rem;
    --cds-spacing-04: 0.75rem;
    --cds-spacing-05: 1rem;
    --cds-spacing-06: 1.5rem;
    --cds-spacing-07: 2rem;
    --cds-spacing-08: 2.5rem;
    --cds-spacing-09: 3rem;
    --cds-spacing-10: 4rem;
    --cds-spacing-11: 5rem;
    --cds-spacing-12: 6rem;

    /* ── Carbon typography scale ──────────────────────────────── */
    --cds-label-01-size: 0.75rem;
    --cds-label-01-weight: 400;
    --cds-label-01-line-height: 1.34;
    --cds-label-02-size: 0.875rem;
    --cds-label-02-weight: 400;
    --cds-body-01-size: 0.875rem;
    --cds-body-01-line-height: 1.43;
    --cds-body-02-size: 1rem;
    --cds-body-02-line-height: 1.5;
    --cds-heading-01-size: 0.875rem;
    --cds-heading-01-weight: 600;
    --cds-heading-02-size: 1rem;
    --cds-heading-02-weight: 600;
    --cds-heading-03-size: 1.25rem;
    --cds-heading-03-weight: 400;
    --cds-code-01-size: 0.75rem;
    --cds-code-01-line-height: 1.34;
    --cds-code-02-size: 0.875rem;
    --cds-code-02-line-height: 1.43;
    --cds-letter-spacing-dense: 0.16px;

    /* ── Carbon font stacks ──────────────────────────────────── */
    --cds-font-sans: 'IBM Plex Sans', system-ui, -apple-system, sans-serif;
    --cds-font-mono: 'IBM Plex Mono', Consolas, 'Courier New', monospace;

    /* ── Carbon component heights ────────────────────────────── */
    --cds-height-sm: 2rem;
    --cds-height-md: 2.5rem;
    --cds-height-lg: 3rem;

    /* ── Carbon motion ───────────────────────────────────────── */
    --cds-motion-productive: cubic-bezier(0.2, 0, 0.38, 0.9);
    --cds-motion-expressive: cubic-bezier(0.4, 0.14, 0.3, 1);
    --cds-duration-fast-01: 70ms;
    --cds-duration-fast-02: 110ms;
    --cds-duration-moderate-01: 150ms;
    --cds-duration-moderate-02: 240ms;
    --cds-duration-slow-01: 400ms;
    --cds-duration-slow-02: 700ms;

    /* ── Carbon focus ring ───────────────────────────────────── */
    --cds-focus: var(--neon-cyan);
    --cds-focus-inset: #000000;

    /* ── Carbon layer tokens → neon-mapped ───────────────────── */
    --cds-background: #000000;
    --cds-layer-01: #0a0a14;
    --cds-layer-02: #0f0f1e;
    --cds-layer-03: #16162a;
    --cds-layer-hover-01: #111125;
    --cds-layer-active-01: #1a1a3a;
    --cds-border-subtle-00: #141430;
    --cds-border-subtle-01: #1a1a3a;
    --cds-border-strong-01: #2a2a55;
    --cds-border-interactive: var(--neon-cyan);
    --cds-text-primary: #d8d8ec;
    --cds-text-secondary: #6e6e8e;
    --cds-text-placeholder: #555577;
    --cds-text-on-color: #000000;
    --cds-link-primary: var(--neon-cyan);
    --cds-link-primary-hover: var(--neon-teal);
    --cds-icon-primary: #d8d8ec;
    --cds-icon-secondary: #6e6e8e;
    --cds-button-primary: var(--neon-cyan);
    --cds-button-primary-hover: var(--neon-teal);
    --cds-button-secondary: var(--cds-layer-03);
    --cds-button-secondary-hover: var(--cds-border-strong-01);
    --cds-button-danger: var(--neon-red);
    --cds-support-error: var(--neon-red);
    --cds-support-success: var(--neon-teal);
    --cds-support-warning: #ff8844;
    --cds-support-info: var(--neon-cyan);
    --cds-notification-background-error: rgba(255,58,58,0.06);
    --cds-notification-background-info: rgba(0,240,255,0.04);

    /* ── Carbon shadow tokens ────────────────────────────────── */
    --cds-shadow-sm: 0 2px 6px rgba(0,0,0,0.3);
    --cds-shadow-md: 0 4px 12px rgba(0,0,0,0.3);
}

/* ── Solid background ──────────────────────────────────────────── */
.gradio-container {
    background: var(--cds-background) !important;
    min-height: 100vh;
}

/* ── Scan-line overlay (horizontal only, subtle) ───────────────── */
.gradio-container::before {
    content: "";
    position: fixed;
    inset: 0;
    background:
        repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,240,255,0.008) 2px, rgba(0,240,255,0.008) 4px);
    pointer-events: none;
    z-index: 9999;
}

/* ── Carbon UI Shell header (48px) ─────────────────────────────── */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--cds-spacing-05);
    height: var(--cds-height-lg);
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-00);
}
.header-bar .hud-label {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-label-01-size);
    font-weight: 400;
    color: var(--cds-text-secondary);
    letter-spacing: var(--cds-letter-spacing-dense);
    text-transform: uppercase;
}
.header-bar .title {
    font-family: var(--cds-font-sans);
    font-size: var(--cds-heading-03-size);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--neon-cyan);
}
.header-bar .title .accent {
    color: var(--neon-pink);
}

/* ── Pipeline chips → Carbon tags (pill shape) ─────────────────── */
.header-bar .pipeline-chips {
    display: flex;
    gap: var(--cds-spacing-02);
    align-items: center;
}
.header-bar .pipeline-chips .chip {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-label-01-size);
    font-weight: 500;
    color: var(--neon-cyan);
    padding: var(--cds-spacing-01) var(--cds-spacing-03);
    border: 1px solid rgba(0,240,255,0.2);
    background: rgba(0,240,255,0.03);
    letter-spacing: var(--cds-letter-spacing-dense);
    text-transform: uppercase;
    border-radius: 100px;
    transition: background var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.header-bar .pipeline-chips .chip:hover {
    background: rgba(0,240,255,0.06);
}
.header-bar .page-id {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-label-01-size);
    color: var(--cds-text-secondary);
    letter-spacing: 0.08em;
}

/* ── 3-Panel layout ──────────────────────────────────────────── */
.panel {
    background: var(--cds-background) !important;
    border: none !important;
    min-height: calc(100vh - 100px);
    padding: 0 !important;
}
.panel-left {
    border-right: 1px solid var(--cds-border-subtle-00) !important;
}
.panel-right {
    border-left: 1px solid var(--cds-border-subtle-00) !important;
}
.panel-header {
    font-family: var(--cds-font-sans);
    font-size: var(--cds-heading-01-size);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: var(--cds-letter-spacing-dense);
    color: var(--neon-cyan);
    padding: var(--cds-spacing-04) var(--cds-spacing-05) var(--cds-spacing-03);
    border-bottom: 1px solid var(--cds-border-subtle-00);
    margin-bottom: var(--cds-spacing-03);
}
.panel-content {
    padding: var(--cds-spacing-03) var(--cds-spacing-04) var(--cds-spacing-05);
}
.panel-empty {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-body-01-size);
    color: var(--cds-text-secondary);
    text-align: center;
    padding: var(--cds-spacing-07) var(--cds-spacing-05);
    line-height: 1.6;
}

/* ── Section cards — Carbon tile ──────────────────────────────── */
.cyber-card {
    background: var(--cds-layer-01) !important;
    border: 1px solid var(--cds-border-subtle-01) !important;
    border-radius: 0 !important;
    padding: var(--cds-spacing-05) !important;
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.cyber-card:hover {
    border-color: var(--neon-teal) !important;
}
.cyber-card-label {
    font-family: var(--cds-font-sans) !important;
    font-size: var(--cds-heading-01-size) !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: var(--cds-letter-spacing-dense);
    color: var(--neon-cyan) !important;
    margin-bottom: var(--cds-spacing-04) !important;
    padding-bottom: var(--cds-spacing-02);
    border-bottom: 1px solid var(--cds-border-subtle-00);
}

/* ── Generate button — Carbon primary contained ─────────────────── */
#generate-btn {
    margin-top: var(--cds-spacing-03);
}
#generate-btn button {
    font-family: var(--cds-font-sans) !important;
    font-size: var(--cds-body-01-size) !important;
    font-weight: 600 !important;
    letter-spacing: var(--cds-letter-spacing-dense) !important;
    text-transform: uppercase !important;
    padding: 0 var(--cds-spacing-05) !important;
    height: var(--cds-height-lg) !important;
    border-radius: 0 !important;
    background: var(--cds-button-primary) !important;
    color: var(--cds-text-on-color) !important;
    border: none !important;
    transition: background var(--cds-duration-fast-02) var(--cds-motion-productive) !important;
}
#generate-btn button:hover {
    background: var(--cds-button-primary-hover) !important;
}
#generate-btn button:focus {
    outline: 2px solid var(--cds-focus) !important;
    outline-offset: -2px;
}

/* ── Progress bar — Carbon progress indicator ──────────────────── */
.progress-hud {
    border: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    padding: var(--cds-spacing-04) var(--cds-spacing-05);
}
.progress-steps {
    display: flex;
    gap: 0;
    margin-bottom: var(--cds-spacing-03);
}
.progress-step {
    flex: 1;
    height: 4px;
    background: var(--cds-border-subtle-00);
    transition: background var(--cds-duration-moderate-02) var(--cds-motion-productive);
}
.progress-step.done {
    background: var(--neon-cyan);
}
.progress-step.active {
    background: linear-gradient(90deg, var(--neon-cyan), var(--neon-teal));
    animation: progressPulse 1.5s ease-in-out infinite;
}
@keyframes progressPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
.progress-step + .progress-step { margin-left: 3px; }
.progress-text {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-body-01-size);
    color: var(--cds-text-primary);
}
.progress-eta {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-code-01-size);
    color: var(--neon-teal);
    float: right;
}
.progress-complete {
    color: var(--neon-cyan);
}

/* ── Waveform container ──────────────────────────────────────── */
.waveform-wrap {
    border: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    padding: var(--cds-spacing-02);
    margin-top: var(--cds-spacing-02);
    min-height: 48px;
    overflow: hidden;
}
.waveform-bars {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2px;
    height: 40px;
}
.waveform-bars .bar {
    width: 3px;
    background: linear-gradient(180deg, var(--neon-cyan), var(--neon-teal));
    border-radius: 1px;
    animation: waveBar 1.2s ease-in-out infinite;
    opacity: 0.7;
}
@keyframes waveBar {
    0%, 100% { transform: scaleY(0.3); }
    50% { transform: scaleY(1); }
}

/* ── Regen button ──────────────────────────────────────────── */
#regen-audio-btn button {
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-code-02-size) !important;
    letter-spacing: var(--cds-letter-spacing-dense) !important;
    text-transform: uppercase !important;
    border: 1px solid rgba(0,240,255,0.25) !important;
    background: rgba(0,240,255,0.04) !important;
    color: var(--neon-cyan) !important;
    height: var(--cds-height-md);
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
#regen-audio-btn button:hover {
    border-color: var(--neon-cyan) !important;
}

/* ── Keyboard hint ─────────────────────────────────────────── */
.kbd-hint {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-label-01-size);
    color: var(--cds-text-secondary);
    text-align: center;
    padding: var(--cds-spacing-02) 0;
    opacity: 0.6;
}
.kbd-hint kbd {
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    padding: 0.1rem 0.35rem;
    font-size: var(--cds-code-01-size);
    color: var(--neon-teal);
}

/* ── Status output ─────────────────────────────────────────── */
#status-box textarea {
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-body-01-size) !important;
    border: 1px solid var(--cds-border-subtle-01) !important;
    border-left: 3px solid var(--neon-cyan) !important;
    border-radius: 0 !important;
    background: var(--cds-layer-01) !important;
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}

/* ── Audio player ──────────────────────────────────────────── */
#audio-player {
    border: 1px solid var(--cds-border-subtle-01) !important;
    border-radius: 0 !important;
    background: var(--cds-layer-01) !important;
    overflow: hidden;
}
#audio-player audio {
    filter: hue-rotate(160deg) saturate(1.5);
}

/* ── Accordion — Carbon accordion (bottom-border dividers) ────── */
.cyber-accordion .label-wrap {
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-body-01-size) !important;
    border-bottom: 1px solid var(--cds-border-subtle-00) !important;
    border-left: none !important;
    padding: var(--cds-spacing-03) 0 !important;
    transition: color var(--cds-duration-fast-02) var(--cds-motion-productive);
    color: var(--cds-text-secondary) !important;
}
.cyber-accordion .label-wrap:hover {
    color: var(--cds-text-primary) !important;
}
.cyber-accordion .label-wrap .icon {
    color: var(--neon-teal) !important;
}

/* ── File upload — Carbon file uploader ────────────────────────── */
.cyber-upload .upload-container,
.cyber-upload [data-testid="droparea"] {
    border: 1px dashed var(--cds-border-strong-01) !important;
    border-radius: 0 !important;
    background: transparent !important;
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.cyber-upload .upload-container:hover,
.cyber-upload [data-testid="droparea"]:hover {
    border-color: var(--neon-teal) !important;
    background: rgba(59,214,198,0.02) !important;
}

/* ── Dropdown / select ───────────────────────────────────────── */
.gradio-container select,
.gradio-container .wrap.svelte-1s0gk1z,
.gradio-container .secondary-wrap {
    background: var(--cds-layer-01) !important;
    border-color: var(--cds-border-subtle-01) !important;
    border-radius: 0 !important;
    color: var(--cds-text-primary) !important;
}

/* ── Output selector — Carbon selectable tile grid ────────────── */
.output-selector label {
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-code-02-size) !important;
}
.output-selector .wrap {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: var(--cds-spacing-03) !important;
}
.output-selector .wrap > label {
    display: flex !important;
    align-items: center;
    gap: var(--cds-spacing-02);
    padding: var(--cds-spacing-03) var(--cds-spacing-04) !important;
    border: 1px solid var(--cds-border-subtle-01) !important;
    border-radius: 0 !important;
    background: var(--cds-layer-01) !important;
    cursor: pointer;
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.output-selector .wrap > label:hover {
    border-color: var(--neon-teal) !important;
}
.output-selector .wrap > label:has(input:checked) {
    border-color: var(--neon-cyan) !important;
    background: rgba(0,240,255,0.04) !important;
}
.output-selector input[type="checkbox"] {
    accent-color: var(--neon-cyan) !important;
}

/* ── Scrollbar — solid thumb ───────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--cds-background); }
::-webkit-scrollbar-thumb {
    background: var(--neon-cyan);
    border-radius: 0;
}

/* ── Footer — clean divider ───────────────────────────────────── */
.cyber-footer {
    text-align: center;
    padding: var(--cds-spacing-04) var(--cds-spacing-05) var(--cds-spacing-05);
    margin-top: 0;
}
.cyber-footer .divider {
    height: 1px;
    background: var(--cds-border-subtle-00);
    margin-bottom: var(--cds-spacing-04);
}
.cyber-footer p {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-label-01-size);
    color: var(--cds-text-secondary);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.cyber-footer a {
    color: var(--neon-cyan) !important;
    text-decoration: none !important;
    transition: color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.cyber-footer a:hover {
    color: var(--neon-pink) !important;
}

/* ── Input fields ──────────────────────────────────────────── */
.gradio-container textarea,
.gradio-container input[type="text"] {
    caret-color: var(--neon-cyan) !important;
    border-radius: 0 !important;
}
.gradio-container textarea:focus,
.gradio-container input[type="text"]:focus {
    border-color: var(--neon-cyan) !important;
    outline: 2px solid var(--cds-focus) !important;
    outline-offset: -2px;
}

/* ── Global overrides — kill all border-radius ───────────────── */
.gradio-container .block,
.gradio-container .form,
.gradio-container .wrap,
.gradio-container .container,
.gradio-container button,
.gradio-container input,
.gradio-container textarea,
.gradio-container .tabitem {
    border-radius: 0 !important;
}

/* ── Global focus override — Carbon focus ring ───────────────── */
.gradio-container *:focus-visible {
    outline: 2px solid var(--cds-focus) !important;
    outline-offset: -2px;
    box-shadow: none !important;
}

/* ── Group wrapper ───────────────────────────────────────────── */
.gradio-group {
    background: transparent !important;
    border: none !important;
}

/* ── Results fade-in — Carbon expressive motion ──────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.results-section {
    animation: fadeInUp var(--cds-duration-slow-01) var(--cds-motion-expressive);
}

/* ── Downloads row ───────────────────────────────────────────── */
.download-row {
    display: flex;
    gap: var(--cds-spacing-04);
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
    padding: var(--cds-spacing-10) var(--cds-spacing-07);
    color: var(--cds-text-secondary);
    text-align: center;
}
.center-empty .icon {
    font-size: 2.5rem;
    margin-bottom: var(--cds-spacing-05);
    opacity: 0.3;
}
.center-empty p {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-body-01-size);
    line-height: 1.6;
}

/* ── Notebook bar ──────────────────────────────────────────── */
.notebook-bar {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    padding: var(--cds-spacing-02) var(--cds-spacing-05);
    border-bottom: 1px solid var(--cds-border-subtle-00);
    background: var(--cds-background);
}
.notebook-bar .nb-btn button {
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-code-01-size) !important;
    padding: var(--cds-spacing-02) var(--cds-spacing-04) !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    height: var(--cds-height-sm);
}

/* ── Source list ───────────────────────────────────────────── */
.source-list {
    display: flex;
    flex-direction: column;
    gap: var(--cds-spacing-02);
    padding: var(--cds-spacing-02) 0;
}
.source-item {
    display: flex;
    align-items: center;
    gap: var(--cds-spacing-03);
    padding: var(--cds-spacing-03) var(--cds-spacing-04);
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-left: 2px solid var(--neon-teal);
    border-radius: 0;
    font-family: var(--cds-font-mono);
    font-size: var(--cds-code-02-size);
    color: var(--cds-text-primary);
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.source-item:hover {
    border-color: var(--neon-teal);
    border-left-color: var(--neon-cyan);
}
.source-icon {
    flex-shrink: 0;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.source-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.source-empty {
    font-family: var(--cds-font-mono);
    font-size: var(--cds-code-02-size);
    color: var(--cds-text-secondary);
    text-align: center;
    padding: var(--cds-spacing-05) var(--cds-spacing-03);
}

/* ── All Gradio labels ───────────────────────────────────────── */
.gradio-container label span {
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-label-01-size) !important;
    letter-spacing: var(--cds-letter-spacing-dense);
    text-transform: uppercase;
    color: var(--cds-text-secondary) !important;
}

/* ── Secondary / stop buttons — Carbon ghost/danger ──────────── */
.gradio-container button.secondary {
    border-radius: 0 !important;
    border: 1px solid var(--cds-border-subtle-01) !important;
    background: var(--cds-layer-01) !important;
    color: var(--cds-text-primary) !important;
    font-family: var(--cds-font-mono) !important;
    height: var(--cds-height-md);
    transition: border-color var(--cds-duration-fast-02) var(--cds-motion-productive),
                color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
.gradio-container button.secondary:hover {
    border-color: var(--neon-teal) !important;
    color: var(--neon-cyan) !important;
}
.gradio-container button.stop {
    border-radius: 0 !important;
    border: 1px solid rgba(255,58,58,0.3) !important;
    background: rgba(255,58,58,0.05) !important;
}
.gradio-container button.stop:hover {
    border-color: var(--neon-red) !important;
}

/* ── Health banner — Carbon inline notification ────────────────── */
.health-banner {
    background: var(--cds-notification-background-error);
    border: 1px solid rgba(255,58,58,0.25);
    border-left: 3px solid var(--neon-red);
    padding: var(--cds-spacing-03) var(--cds-spacing-05);
    font-family: var(--cds-font-mono);
    font-size: var(--cds-label-01-size);
    color: #ff8888;
}

/* ── Preset pills ──────────────────────────────────── */
#preset-selector .wrap { gap: var(--cds-spacing-02) !important; }
#preset-selector label {
    font-size: var(--cds-code-01-size) !important;
    padding: var(--cds-spacing-01) var(--cds-spacing-03) !important;
    border-radius: 0 !important;
}

/* ── Stop button ───────────────────────────────────── */
#stop-btn button {
    background: rgba(255,58,58,0.08) !important;
    border: 1px solid rgba(255,58,58,0.3) !important;
    color: #ff6666 !important;
    height: var(--cds-height-lg);
}
#stop-btn button:hover {
    background: rgba(255,58,58,0.15) !important;
    border-color: var(--neon-red) !important;
}

/* ── Retry button ──────────────────────────────────── */
#retry-btn button {
    background: rgba(255,165,0,0.08) !important;
    border: 1px solid rgba(255,165,0,0.3) !important;
    color: #ffaa44 !important;
}
#retry-btn button:hover {
    background: rgba(255,165,0,0.15) !important;
    border-color: #ffaa44 !important;
}

/* ── Log viewer ────────────────────────────────────── */
.log-viewer {
    margin-top: var(--cds-spacing-03);
    font-family: var(--cds-font-mono);
    font-size: var(--cds-code-01-size);
}
.log-viewer summary {
    cursor: pointer;
    color: var(--cds-text-secondary);
    padding: var(--cds-spacing-02) 0;
}
.log-viewer pre {
    max-height: 200px;
    overflow-y: auto;
    background: rgba(0,0,0,0.4);
    padding: var(--cds-spacing-03);
    border: 1px solid var(--cds-border-subtle-00);
    color: var(--cds-text-secondary);
    white-space: pre-wrap;
    word-break: break-all;
}

/* ── History timeline ──────────────────────────────── */
.history-timeline { display: flex; flex-direction: column; gap: var(--cds-spacing-02); }
.history-empty { color: var(--cds-text-secondary); font-size: var(--cds-label-01-size); padding: var(--cds-spacing-03) 0; }
.hist-entry {
    display: flex; align-items: center; gap: var(--cds-spacing-03); flex-wrap: wrap;
    padding: var(--cds-spacing-03) var(--cds-spacing-04);
    border-left: 2px solid var(--neon-teal);
    background: rgba(0,240,255,0.02);
    font-family: var(--cds-font-mono);
    font-size: var(--cds-code-01-size);
}
.hist-entry.fail { border-left-color: var(--neon-red); background: rgba(255,58,58,0.02); }
.hist-ts { color: var(--cds-text-secondary); min-width: 120px; }
.hist-badge {
    background: rgba(0,240,255,0.08);
    padding: 1px 6px;
    color: var(--neon-cyan);
}
.hist-dur { color: var(--cds-text-secondary); }
.hist-out { color: var(--neon-teal); }
.hist-err { color: #ff6666; font-size: var(--cds-label-01-size); width: 100%; }

/* ── Notebook tabs — Carbon underline tabs ──────────── */
#notebook-tabs .wrap {
    gap: 0 !important;
    flex-wrap: nowrap !important;
    overflow-x: auto;
    border-bottom: 1px solid var(--cds-border-subtle-00);
}
#notebook-tabs label {
    border-radius: 0 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: var(--cds-spacing-03) var(--cds-spacing-05) !important;
    font-family: var(--cds-font-mono) !important;
    font-size: var(--cds-code-01-size) !important;
    color: var(--cds-text-secondary) !important;
    background: transparent !important;
    white-space: nowrap;
    transition: color var(--cds-duration-fast-02) var(--cds-motion-productive),
                border-color var(--cds-duration-fast-02) var(--cds-motion-productive);
}
#notebook-tabs label:hover {
    color: var(--cds-text-primary) !important;
}
#notebook-tabs label.selected, #notebook-tabs input:checked + label {
    border-bottom-color: var(--neon-cyan) !important;
    color: var(--neon-cyan) !important;
}
"""


# ---------------------------------------------------------------------------
# Hero / Pipeline / Footer HTML fragments
# ---------------------------------------------------------------------------

HEADER_HTML = """
<div class="header-bar">
    <div>
        <div class="hud-label">Interface V2.0</div>
        <span class="title">LOCAL<span class="accent">:</span>NOTEBOOK<span class="accent">LM</span></span>
    </div>
    <div class="pipeline-chips">
        <span class="chip">01 Extract</span>
        <span class="chip">02 Script</span>
        <span class="chip">03 Prepare</span>
        <span class="chip">04 Audio / Visual</span>
    </div>
    <span class="page-id">SYS::ACTIVE</span>
</div>
"""

FOOTER_HTML = """
<div class="cyber-footer">
    <div class="divider"></div>
    <p>LOCAL-NOTEBOOKLM // G&ouml;kdeniz G&uuml;lmez &nbsp;&mdash;&nbsp;
       <a href="https://github.com/Goekdeniz-Guelmez/Local-NotebookLM" target="_blank">GitHub</a>
    </p>
</div>
"""


# ---------------------------------------------------------------------------
# Notebook manager (global singleton)
# ---------------------------------------------------------------------------

_notebook_mgr = NotebookManager()


# ---------------------------------------------------------------------------
# Generation state — now per-job via pipeline_runner; these are kept only
# as fallbacks for the _post_generate / _on_retry callbacks when no job exists.
# ---------------------------------------------------------------------------

_last_failed_step: int | None = None
_last_log_text: str = ""


class _LogCapture(_logging.Handler):
    """Capture log records during a pipeline run for display in the UI."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []
        self.setLevel(_logging.INFO)
        self.setFormatter(_logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record):
        self.records.append(self.format(record))

    def get_text(self) -> str:
        return "\n".join(self.records)


# ---------------------------------------------------------------------------
# Settings presets
# ---------------------------------------------------------------------------

_PRESETS: dict[str, dict] = {
    "Custom": {},
    "Quick Summary": {
        "format": "summary", "length": "short", "style": "professional",
        "temperature": 0.5,
    },
    "Casual Chat": {
        "format": "podcast", "length": "medium", "style": "casual",
        "temperature": 0.8,
    },
    "Academic Lecture": {
        "format": "lecture", "length": "long", "style": "academic",
        "temperature": 0.4,
    },
    "News Brief": {
        "format": "news-report", "length": "short", "style": "professional",
        "temperature": 0.3,
    },
    "Deep Dive Panel": {
        "format": "panel-discussion", "length": "very-long", "style": "technical",
        "temperature": 0.7,
    },
    "Storytelling": {
        "format": "storytelling", "length": "long", "style": "friendly",
        "temperature": 0.9,
    },
    "Gen-Z Explainer": {
        "format": "explainer", "length": "medium", "style": "gen-z",
        "temperature": 1.0,
    },
    "Fast Mode": {
        "format": "summary", "length": "short", "style": "normal",
        "temperature": 0.3,
    },
}


# ---------------------------------------------------------------------------
# Provider health check
# ---------------------------------------------------------------------------

def _check_provider_health() -> str:
    """Test LLM/TTS endpoints + optional deps, return HTML banner (empty if all OK)."""
    import urllib.request
    checks = []  # (name, ok)
    warnings = []  # text strings

    # Ollama LLM
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        checks.append(("Ollama LLM", True))
    except Exception:
        checks.append(("Ollama LLM", False))

    # Kokoro TTS
    try:
        urllib.request.urlopen("http://localhost:8880/v1/models", timeout=3)
        checks.append(("Kokoro TTS", True))
    except Exception:
        checks.append(("Kokoro TTS", False))

    # Optional dependency checks
    try:
        import docling  # noqa: F401
    except ImportError:
        warnings.append("Docling not installed — PDF extraction will use PyPDF2 (lower quality)")

    try:
        import trafilatura  # noqa: F401
    except ImportError:
        warnings.append("trafilatura not installed — URL extraction will fall back to BeautifulSoup")

    all_ok = all(ok for _, ok in checks) and not warnings
    if all_ok:
        return ""

    items = []
    for name, ok in checks:
        color = "var(--neon-teal)" if ok else "var(--neon-red, #ff3a3a)"
        dot = "&#x25CF;"
        items.append(f'<span style="color:{color};margin-right:12px">{dot} {name}</span>')

    warn_html = ""
    if warnings:
        warn_items = "".join(f"<li>{w}</li>" for w in warnings)
        warn_html = (
            f'<ul style="margin:4px 0 0;padding-left:18px;font-size:var(--cds-code-01-size);'
            f'color:var(--cds-text-secondary);list-style:disc">{warn_items}</ul>'
        )

    provider_msg = ""
    if not all(ok for _, ok in checks):
        provider_msg = (
            '<span style="color:var(--cds-text-secondary);margin-left:8px">'
            '&mdash; some providers offline, generation may fail</span>'
        )

    return (
        '<div class="health-banner">'
        f'{"".join(items)}{provider_msg}{warn_html}'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Session restore — reload outputs from a notebook directory
# ---------------------------------------------------------------------------

def _load_results_from_dir(d: str):
    """Scan a directory for pipeline outputs and return a 9-tuple.

    Returns ``None`` when nothing is found.
    """
    if not os.path.isdir(d):
        return None

    audio_path = None
    for subdir in [os.path.join(d, "step4"), d]:
        for ext in ["wav", "mp3", "ogg", "flac", "aac"]:
            candidate = os.path.join(subdir, f"podcast.{ext}")
            if os.path.exists(candidate):
                audio_path = candidate
                break
        if audio_path:
            break

    file_contents = {}
    for rel in ["step1/extracted_text.txt", "step1/clean_extracted_text.txt", "step3/podcast_ready_data.txt"]:
        fp = os.path.join(d, rel)
        if os.path.exists(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    c = f.read()
                    file_contents[rel] = c[:1000] + "..." if len(c) > 1000 else c
            except Exception as e:
                _log.warning("Failed to read pipeline output %s: %s", rel, e)

    infographic_html = None
    infographic_file = None
    infographic_path = os.path.join(d, "step5", "infographic.html")
    if os.path.exists(infographic_path):
        try:
            with open(infographic_path, 'r', encoding='utf-8') as f:
                infographic_html = f'<iframe srcdoc="{f.read().replace(chr(34), "&quot;").replace(chr(10), "&#10;")}" style="width:100%;height:600px;border:1px solid var(--cds-border-subtle-00);border-radius:0;" sandbox="allow-same-origin"></iframe>'
            infographic_file = infographic_path
        except Exception as e:
            _log.warning("Failed to read infographic HTML: %s", e)

    png_image = None
    png_path = os.path.join(d, "step5", "infographic.png")
    if os.path.exists(png_path):
        png_image = png_path

    pptx_file = None
    pptx_path = os.path.join(d, "step5", "infographic.pptx")
    if os.path.exists(pptx_path):
        pptx_file = pptx_path

    has_anything = audio_path or infographic_html or png_image or pptx_file or file_contents
    if not has_anything:
        return None

    parts = []
    if audio_path:
        parts.append("Audio")
    if infographic_html:
        parts.append("Infographic HTML")
    if png_image:
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
        png_image,
        pptx_file,
    )


# ---------------------------------------------------------------------------
# Notebook callbacks
# ---------------------------------------------------------------------------

def _dropdown_choices():
    """Return Gradio-compatible ``(label, value)`` list for the notebook dropdown."""
    return [(nb["name"], nb["id"]) for nb in _notebook_mgr.list_notebooks()]


_ICON_FILE = (
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M3 1h7l4 4v10H3V1z" stroke="var(--neon-cyan)" stroke-width="1.2" fill="none"/>'
    '<path d="M10 1v4h4" stroke="var(--neon-cyan)" stroke-width="1.2" fill="none"/>'
    '<line x1="5" y1="8" x2="11" y2="8" stroke="var(--neon-teal)" stroke-width="0.8"/>'
    '<line x1="5" y1="10.5" x2="9" y2="10.5" stroke="var(--neon-teal)" stroke-width="0.8"/>'
    '</svg>'
)
_ICON_LINK = (
    '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M6.5 9.5l3-3" stroke="var(--neon-pink)" stroke-width="1.2"/>'
    '<path d="M8.5 7.5l1.8-1.8a2 2 0 0 1 2.8 2.8L11.3 10.3" stroke="var(--neon-pink)" stroke-width="1.2" fill="none"/>'
    '<path d="M7.5 8.5l-1.8 1.8a2 2 0 0 1-2.8-2.8L4.7 5.7" stroke="var(--neon-pink)" stroke-width="1.2" fill="none"/>'
    '</svg>'
)
_ICON_EMPTY = (
    '<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="4" y="6" width="20" height="16" rx="1" stroke="var(--cds-text-secondary)" stroke-width="1" fill="none" opacity="0.4"/>'
    '<line x1="9" y1="12" x2="19" y2="12" stroke="var(--cds-text-secondary)" stroke-width="0.8" opacity="0.3"/>'
    '<line x1="9" y1="15" x2="16" y2="15" stroke="var(--cds-text-secondary)" stroke-width="0.8" opacity="0.3"/>'
    '<line x1="9" y1="18" x2="13" y2="18" stroke="var(--cds-text-secondary)" stroke-width="0.8" opacity="0.3"/>'
    '</svg>'
)


def _build_sources_html(sources: list[dict]) -> str:
    """Render source list as styled HTML cards with SVG icons."""
    if not sources:
        return (
            '<div class="source-empty">'
            f'{_ICON_EMPTY}<br>'
            'No sources yet — upload a file or paste a URL'
            '</div>'
        )
    items = []
    for i, s in enumerate(sources):
        if s.get("type") == "file":
            icon = _ICON_FILE
            label = s.get("filename", "unknown")
        else:
            icon = _ICON_LINK
            label = s.get("url", "unknown")
        items.append(
            f'<div class="source-item">'
            f'<span class="source-icon">{icon}</span>'
            f'<span class="source-name" title="{label}">{label}</span>'
            f'</div>'
        )
    return '<div class="source-list">' + "".join(items) + '</div>'


def _source_dropdown_choices(sources: list[dict]) -> list[tuple[str, int]]:
    """Return ``(label, index)`` pairs for the source selector dropdown."""
    if not sources:
        return []
    choices = []
    for i, s in enumerate(sources):
        if s.get("type") == "file":
            label = s.get("filename", "unknown")
        else:
            label = s.get("url", "unknown")
        choices.append((f"{i+1}. {label}", i))
    return choices


def _read_source_content(notebook_id: str, index: int) -> str:
    """Read the content of a source by index.  Returns text preview."""
    if not notebook_id:
        return ""
    sources = _notebook_mgr.get_sources(notebook_id)
    if index is None or index < 0 or index >= len(sources):
        return ""
    src = sources[index]
    if src.get("type") == "url":
        return f"URL: {src.get('url', '')}"
    # File source
    filename = src.get("filename", "")
    nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)
    fp = os.path.join(nb_dir, "sources", filename)
    if not os.path.exists(fp):
        return f"[File not found: {filename}]"
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        try:
            import PyPDF2
            with open(fp, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            return text[:5000] + "\n\n[...truncated]" if len(text) > 5000 else text
        except ImportError:
            return "[PyPDF2 not installed — cannot preview PDF content]"
        except Exception as e:
            return f"[Error reading PDF: {e}]"
    elif ext in (".txt", ".md"):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                text = f.read()
            return text[:5000] + "\n\n[...truncated]" if len(text) > 5000 else text
        except Exception as e:
            return f"[Error reading file: {e}]"
    elif ext in (".docx", ".pptx"):
        return f"[Preview not available for {ext} files — upload processes the full document]"
    else:
        return f"[Unsupported file type: {ext}]"


def _format_eta(elapsed_per_step: list[float], current_step: int, total_steps: int) -> str:
    """Format an ETA string based on average time per completed step."""
    if not elapsed_per_step:
        return "ETA: estimating..."
    avg = sum(elapsed_per_step) / len(elapsed_per_step)
    remaining = (total_steps - current_step) * avg
    if remaining < 60:
        return f"ETA: ~{int(remaining)}s"
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    return f"ETA: ~{mins}m {secs}s"


def _build_progress_html(step: int, total: int, message: str, eta: str = "",
                         complete: bool = False) -> str:
    """Build HUD-style progress bar HTML."""
    if complete:
        return (
            '<div class="progress-hud">'
            '<div class="progress-steps">'
            + ''.join(f'<div class="progress-step done"></div>' for _ in range(total))
            + '</div>'
            f'<span class="progress-text progress-complete">{message}</span>'
            '</div>'
        )
    if step == 0 or total == 0:
        return (
            '<div class="progress-hud">'
            f'<span class="progress-text">{message}</span>'
            '</div>'
        )
    bars = []
    for i in range(1, total + 1):
        if i < step:
            bars.append('<div class="progress-step done"></div>')
        elif i == step:
            bars.append('<div class="progress-step active"></div>')
        else:
            bars.append('<div class="progress-step"></div>')
    eta_span = f'<span class="progress-eta">{eta}</span>' if eta else ""
    return (
        '<div class="progress-hud">'
        f'<div class="progress-steps">{"".join(bars)}</div>'
        f'<span class="progress-text">[{step}/{total}] {message}</span>{eta_span}'
        '</div>'
    )


def _build_waveform_html(audio_path: str | None = None, n_bars: int = 80) -> str:
    """Build waveform visualization from real audio data (or fallback to random)."""
    heights = []
    if audio_path and os.path.exists(audio_path):
        try:
            import numpy as np
            import soundfile as sf
            data, _sr = sf.read(audio_path)
            if data.ndim > 1:
                data = data.mean(axis=1)
            # Downsample to n_bars buckets via RMS per bucket
            bucket_size = max(1, len(data) // n_bars)
            for i in range(n_bars):
                chunk = data[i * bucket_size:(i + 1) * bucket_size]
                if len(chunk) == 0:
                    break
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                heights.append(rms)
            # Normalize to 10-100% range
            peak = max(heights) if heights else 1.0
            if peak > 0:
                heights = [max(10, int((h / peak) * 100)) for h in heights]
        except Exception as e:
            _log.warning("Could not compute real waveform: %s", e)
            heights = []
    # Fallback: random heights
    if not heights:
        import random
        heights = [random.randint(15, 100) for _ in range(n_bars)]
    bars = []
    for h in heights:
        bars.append(f'<div class="bar" style="height:{h}%"></div>')
    return '<div class="waveform-wrap"><div class="waveform-bars">' + ''.join(bars) + '</div></div>'


def _build_log_html(log_text: str) -> str:
    """Build collapsible log viewer HTML."""
    if not log_text:
        return ""
    escaped = (log_text.replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace('"', "&quot;"))
    return (
        '<details class="log-viewer"><summary>Pipeline Logs</summary>'
        f'<pre>{escaped}</pre></details>'
    )


def _build_history_html(history: list[dict]) -> str:
    """Build generation history timeline HTML with per-step profiling."""
    if not history:
        return '<div class="history-empty">No generation history yet.</div>'
    items = []
    for entry in history[:10]:
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        fmt = entry.get("format", "?")
        style = entry.get("style", "?")
        length = entry.get("length", "?")
        dur = entry.get("duration_s", 0)
        status = entry.get("status", "unknown")
        status_cls = "done" if status == "success" else "fail"
        outputs = ", ".join(entry.get("outputs", [])) or "none"
        error = entry.get("error", "")
        err_html = f'<div class="hist-err">{error[:120]}</div>' if error else ""
        # Step profiling
        step_times = entry.get("step_times", [])
        step_html = ""
        if step_times:
            step_labels = ["Extract", "Script", "TTS-Prep", "Audio", "Visual"]
            bars = []
            for i, t in enumerate(step_times):
                lbl = step_labels[i] if i < len(step_labels) else f"S{i+1}"
                bars.append(
                    f'<span style="color:var(--neon-teal);font-size:var(--cds-label-01-size)">'
                    f'{lbl}:{t:.0f}s</span>'
                )
            step_html = (
                f'<div style="width:100%;display:flex;gap:8px;flex-wrap:wrap;'
                f'margin-top:2px">{" ".join(bars)}</div>'
            )
        items.append(
            f'<div class="hist-entry {status_cls}">'
            f'<span class="hist-ts">{ts}</span>'
            f'<span class="hist-badge">{fmt} / {style} / {length}</span>'
            f'<span class="hist-dur">{dur:.0f}s</span>'
            f'<span class="hist-out">{outputs}</span>'
            f'{step_html}{err_html}'
            f'</div>'
        )
    return '<div class="history-timeline">' + "".join(items) + '</div>'


def _on_preset_select(preset_name):
    """Apply a settings preset.  Returns updates for format, length, style, language, temperature."""
    p = _PRESETS.get(preset_name, {})
    if not p:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    return (
        gr.update(value=p.get("format")) if "format" in p else gr.update(),
        gr.update(value=p.get("length")) if "length" in p else gr.update(),
        gr.update(value=p.get("style")) if "style" in p else gr.update(),
        gr.update(value=p.get("language")) if "language" in p else gr.update(),
        gr.update(value=p.get("temperature")) if "temperature" in p else gr.update(),
    )


def _on_download_script(script_text, notebook_id):
    """Export the podcast script as a Markdown file.  Returns a file path for gr.File."""
    if not script_text or not script_text.strip():
        return None
    import tempfile, ast
    md_lines = ["# Podcast Script\n"]
    try:
        parsed = ast.literal_eval(script_text)
        if isinstance(parsed, list):
            for speaker, text in parsed:
                md_lines.append(f"**{speaker}:** {text}\n")
    except Exception:
        md_lines.append(script_text)
    tmp = tempfile.NamedTemporaryFile(suffix=".md", prefix="podcast_script_", delete=False, mode="w")
    tmp.write("\n".join(md_lines))
    tmp.close()
    return tmp.name


def _build_script_stats_html(text: str) -> str:
    """Live word count + estimated audio duration for the podcast script."""
    if not text or not text.strip():
        return ""
    words = len(text.split())
    minutes = words / 150  # ~150 wpm for TTS
    m = int(minutes)
    s = int((minutes - m) * 60)
    return (
        f'<div style="font-family:var(--cds-font-mono);font-size:var(--cds-code-01-size);color:var(--cds-text-secondary);padding:4px 0">'
        f'{words:,} words &middot; ~{m}m {s}s estimated audio'
        f'</div>'
    )


def _diagnose_error(error: Exception, step: int | None = None) -> str:
    """Map common pipeline errors to user-friendly diagnostics with remedies."""
    msg = str(error).lower()
    hints = []
    if "connection" in msg or "refused" in msg or "timeout" in msg:
        hints.append("Check that Ollama and TTS services are running (ollama serve)")
    if "429" in msg or "rate limit" in msg:
        hints.append("Rate limited — wait 30s and retry, or switch to a local provider")
    if "model" in msg and ("not found" in msg or "does not exist" in msg):
        hints.append("Model not found — run 'ollama pull &lt;model&gt;' to download it")
    if "out of memory" in msg or "oom" in msg or "cuda" in msg:
        hints.append("Out of memory — try a smaller model or reduce chunk_size in config")
    if "api key" in msg or "authentication" in msg or "unauthorized" in msg:
        hints.append("Authentication failed — check your API key in the config JSON")
    if ("empty" in msg and "response" in msg) or "returned empty" in msg:
        hints.append("LLM returned empty — try a larger model (3b+) or lower temperature")
    if "parse" in msg or "literal_eval" in msg or "syntax" in msg:
        hints.append("Transcript parsing failed — try a larger model for better structured output")
    if "file not found" in msg or "no such file" in msg:
        hints.append("File not found — re-upload the source document")
    if "disk" in msg or "space" in msg or "no space" in msg:
        hints.append("Disk space issue — free up storage and retry")
    if not hints:
        if step and step <= 2:
            hints.append("LLM provider may be offline or overloaded — check service status")
        elif step and step >= 4:
            hints.append("TTS provider may be offline — check that Kokoro/TTS is running")
    return hints[0] if hints else ""


def _build_audio_metrics_html(audio_path: str | None) -> str:
    """Compute and display audio quality metrics after generation."""
    if not audio_path or not os.path.exists(audio_path):
        return ""
    try:
        import numpy as np
        import soundfile as sf
        data, sr = sf.read(audio_path)
        if data.ndim > 1:
            data = data.mean(axis=1)
        duration = len(data) / sr
        file_size = os.path.getsize(audio_path)
        peak = float(np.max(np.abs(data)))
        rms = float(np.sqrt(np.mean(data ** 2)))
        mins = int(duration // 60)
        secs = int(duration % 60)
        size_mb = file_size / (1024 * 1024)
        return (
            f'<div style="display:flex;gap:16px;flex-wrap:wrap;padding:6px 0;'
            f'font-family:var(--cds-font-mono);font-size:var(--cds-code-01-size);color:var(--cds-text-secondary)">'
            f'<span>Duration: <b style="color:var(--neon-cyan)">{mins}:{secs:02d}</b></span>'
            f'<span>Sample Rate: <b style="color:var(--neon-teal)">{sr/1000:.1f}kHz</b></span>'
            f'<span>Size: <b style="color:var(--neon-teal)">{size_mb:.1f}MB</b></span>'
            f'<span>Peak: <b style="color:var(--neon-teal)">{peak:.3f}</b></span>'
            f'<span>RMS: <b style="color:var(--neon-teal)">{rms:.4f}</b></span>'
            f'</div>'
        )
    except Exception as e:
        _log.warning("Could not compute audio metrics: %s", e)
        return ""


def _build_temp_explainer_html(temp: float) -> str:
    """Dynamic temperature description that updates as the slider moves."""
    if temp is None:
        temp = 0.7
    temp = float(temp)
    if temp <= 0.3:
        desc, label = "Deterministic and focused. Best for factual summaries and technical content.", "PRECISE"
        color = "var(--neon-cyan)"
    elif temp <= 0.6:
        desc, label = "Balanced and reliable. Good for professional podcasts and lectures.", "BALANCED"
        color = "var(--neon-teal)"
    elif temp <= 0.9:
        desc, label = "Creative and varied. Ideal for casual conversations and storytelling.", "CREATIVE"
        color = "var(--neon-pink)"
    elif temp <= 1.3:
        desc, label = "Highly creative with unexpected phrasing. Great for entertainment.", "WILD"
        color = "#ff8844"
    else:
        desc, label = "Maximum randomness. Output may be incoherent — use with caution.", "CHAOTIC"
        color = "var(--neon-red)"
    return (
        f'<div style="font-family:var(--cds-font-mono);font-size:var(--cds-label-01-size);padding:2px 0;color:var(--cds-text-secondary)">'
        f'<span style="color:{color};font-weight:600">[{label}]</span> {desc}'
        f'</div>'
    )


def _on_voice_preview(host_voice, cohost_voice, config_file):
    """Generate a short voice sample using the configured TTS. Returns audio path."""
    import json as _json
    from local_notebooklm.config import base_config
    from local_notebooklm.steps.helpers import set_provider, generate_speech

    sample_text = "Hello, welcome to the show! Today we are going to explore some fascinating topics together."

    if config_file is not None:
        config_path = config_file.name if hasattr(config_file, 'name') else config_file
        with open(config_path, 'r') as f:
            config = _json.load(f)
    else:
        ollama_cfg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ollama_config.json",
        )
        if os.path.exists(ollama_cfg):
            with open(ollama_cfg, 'r') as f:
                config = _json.load(f)
        else:
            config = base_config

    voice = (host_voice or "").strip() or config.get("Host-Speaker-Voice", "af_alloy")

    try:
        tts_client = set_provider(config=config["Text-To-Speech-Model"]["provider"])
        import tempfile
        audio_format = config.get("Text-To-Speech-Model", {}).get("audio_format", "wav")
        tmp = tempfile.NamedTemporaryFile(
            suffix=f".{audio_format}", prefix="voice_preview_", delete=False)
        tmp.close()
        out_base = tmp.name.rsplit(".", 1)[0]
        result = generate_speech(
            client=tts_client,
            text=sample_text,
            voice=voice,
            model_name=config["Text-To-Speech-Model"]["model"],
            response_format=audio_format,
            output_path=out_base,
        )
        return result
    except Exception as e:
        _log.warning("Voice preview failed: %s", e)
        return None


def _post_generate(notebook_id):
    """Called after generation finishes.  Updates log viewer, history, and retry button."""
    global _last_log_text, _last_failed_step
    # Pull latest state from job if available
    job = get_job(notebook_id) if notebook_id else None
    if job is not None:
        snap = job.snapshot()
        _last_log_text = snap.get("log_text", _last_log_text)
        _last_failed_step = snap.get("failed_step", _last_failed_step)
    log_html = _build_log_html(_last_log_text)
    history_html = ""
    if notebook_id:
        try:
            history = _notebook_mgr.get_history(notebook_id)
            history_html = _build_history_html(history)
        except Exception as e:
            _log.warning("Failed to load generation history: %s", e)
    retry_visible = gr.update(visible=(_last_failed_step is not None))
    return log_html, history_html, retry_visible


def _on_retry(pdf_file, url_input, config_file, format_type, length, style,
              language, additional_preference, output_dir, skip_to,
              outputs_to_generate, notebook_id,
              host_voice, cohost_voice, temperature,
              selected_source_index):
    """Re-run the pipeline, skipping to the last failed step."""
    global _last_failed_step
    # Check job-level state first, fall back to global
    job = get_job(notebook_id) if notebook_id else None
    retry_step = None
    if job is not None:
        retry_step = job.snapshot().get("failed_step")
        remove_job(notebook_id)
    if retry_step is None:
        retry_step = _last_failed_step
    if retry_step is None:
        yield _empty_result("No failed step to retry.")
        return
    _last_failed_step = None
    yield from process_podcast(
        pdf_file, url_input, config_file, format_type, length, style,
        language, additional_preference, output_dir, retry_step,
        outputs_to_generate, notebook_id,
        host_voice, cohost_voice, temperature,
        selected_source_index=selected_source_index,
    )


def _empty_outputs():
    """9-tuple of empty/cleared outputs."""
    return ("", None, "", "", "", None, None, None, None)


def _on_notebook_switch(notebook_id):
    """Load sources, results, and settings for the selected notebook.

    Returns updates for (24 values):
      sources_display, source_selector, source_content_viewer,
      progress_display, audio_output, extracted_text,
      clean_text, audio_script, infographic_preview, infographic_download,
      png_preview, pptx_download,
      format, length, style, language, outputs_to_generate, output_dir,
      host_voice, cohost_voice, temperature,
      log_viewer, history_display, speaker_personality
    """
    if not notebook_id:
        return (
            _build_sources_html([]),
            gr.update(choices=[], value=None),
            "",
            *_empty_outputs(),
            "podcast", "medium", "normal", "english",
            ["Podcast Audio", "Infographic HTML", "Infographic PNG", "PPTX Slides"],
            "",
            "", "", 0.7,
            "", "",
            "",
        )

    _notebook_mgr.set_default_notebook_id(notebook_id)
    sources = _notebook_mgr.get_sources(notebook_id)
    settings = _notebook_mgr.get_settings(notebook_id)
    nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)

    sources_html = _build_sources_html(sources)
    src_choices = _source_dropdown_choices(sources)

    # ── Check for a running background job ───────────────────
    progress_override = None
    if is_running(notebook_id):
        job = get_job(notebook_id)
        snap = job.snapshot()
        eta = _format_eta(snap["step_times"], snap["current_step"], snap["total_steps"])
        progress_override = _build_progress_html(
            snap["current_step"], snap["total_steps"],
            f'{snap["step_label"]} — click Generate to reconnect', eta,
        )
    else:
        # Check for stale "running" state from a process crash
        stale = load_stale_state(nb_dir)
        if stale is not None:
            progress_override = _build_progress_html(
                stale.get("current_step", 0), stale.get("total_steps", 0),
                "Previous run interrupted (process crash) — partial results may be available",
            )

    results = _load_results_from_dir(nb_dir)
    if results is None:
        results = _empty_outputs()

    # If there's a running-job banner, override the progress display
    if progress_override is not None:
        results = (progress_override, *results[1:])

    history_html = _build_history_html(_notebook_mgr.get_history(notebook_id))

    return (
        sources_html,
        gr.update(choices=src_choices, value=None),
        "",
        *results,
        settings.get("format", "podcast"),
        settings.get("length", "medium"),
        settings.get("style", "normal"),
        settings.get("language", "english"),
        settings.get("outputs_to_generate", ["Podcast Audio", "Infographic HTML", "Infographic PNG", "PPTX Slides"]),
        nb_dir,
        settings.get("host_voice", ""),
        settings.get("cohost_voice", ""),
        settings.get("temperature", 0.7),
        "",
        history_html,
        settings.get("speaker_personality", ""),
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
    """Copy uploaded file into the notebook sources.

    Returns: sources HTML, source_selector update, cleared source viewer.
    """
    if file is None or not notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id) if notebook_id else []
        return (
            _build_sources_html(sources),
            gr.update(choices=_source_dropdown_choices(sources)),
            "",
        )
    file_path = file.name if hasattr(file, "name") else file
    original_name = os.path.basename(file_path)
    _notebook_mgr.add_file_source(notebook_id, file_path, original_name)
    sources = _notebook_mgr.get_sources(notebook_id)
    return (
        _build_sources_html(sources),
        gr.update(choices=_source_dropdown_choices(sources)),
        "",
    )


def _check_url_reachable(url: str) -> str | None:
    """HEAD-request a URL. Returns None if OK, or a warning string."""
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "Local-NotebookLM/1.0"})
        urllib.request.urlopen(req, timeout=8)
        return None
    except urllib.error.HTTPError as e:
        return f"URL returned HTTP {e.code}"
    except Exception as e:
        return f"URL unreachable: {e}"


def _on_url_add(url, notebook_id):
    """Record URL in notebook metadata after reachability check.

    Returns: sources HTML, URL input (cleared or kept with warning), source_selector update, viewer.
    """
    if not url or not url.strip() or not notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id) if notebook_id else []
        return (
            _build_sources_html(sources),
            url or "",
            gr.update(choices=_source_dropdown_choices(sources)),
            "",
        )
    clean_url = url.strip()
    # Reachability check
    warning = _check_url_reachable(clean_url)
    if warning:
        _log.warning("URL check failed for %s: %s", clean_url, warning)
        sources = _notebook_mgr.get_sources(notebook_id)
        return (
            _build_sources_html(sources),
            clean_url,
            gr.update(choices=_source_dropdown_choices(sources)),
            f"[Warning: {warning} — URL was NOT added. Check the address and try again.]",
        )
    _notebook_mgr.add_url_source(notebook_id, clean_url)
    sources = _notebook_mgr.get_sources(notebook_id)
    return (
        _build_sources_html(sources),
        "",
        gr.update(choices=_source_dropdown_choices(sources)),
        "",
    )


def _on_settings_change(notebook_id, fmt, length, style, lang, outputs,
                        host_voice, cohost_voice, temperature, speaker_personality):
    """Silently save settings to notebook metadata."""
    if not notebook_id:
        return
    _notebook_mgr.save_settings(notebook_id, {
        "format": fmt,
        "length": length,
        "style": style,
        "language": lang,
        "outputs_to_generate": outputs,
        "host_voice": host_voice or "",
        "cohost_voice": cohost_voice or "",
        "temperature": temperature if temperature is not None else 0.7,
        "speaker_personality": speaker_personality or "",
    })


def _on_source_select(index, notebook_id):
    """Load and display content of the selected source."""
    if index is None or not notebook_id:
        return ""
    return _read_source_content(notebook_id, index)


def _on_remove_source(index, notebook_id):
    """Remove the selected source.

    Returns: sources HTML, source_selector update, cleared viewer.
    """
    if index is None or not notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id) if notebook_id else []
        return (
            _build_sources_html(sources),
            gr.update(choices=_source_dropdown_choices(sources), value=None),
            "",
        )
    try:
        _notebook_mgr.remove_source(notebook_id, index)
    except (IndexError, KeyError) as e:
        _log.warning("Failed to remove source index %s: %s", index, e)
    sources = _notebook_mgr.get_sources(notebook_id)
    return (
        _build_sources_html(sources),
        gr.update(choices=_source_dropdown_choices(sources), value=None),
        "",
    )


def _on_app_load():
    """Called on page load — switch to the default notebook."""
    default_id = _notebook_mgr.get_default_notebook_id()
    return default_id


def _on_regen_audio(edited_script, notebook_id, config_file, host_voice, cohost_voice):
    """Re-generate audio from an edited podcast script (Step 4 only).

    Writes the edited text back to step3 output, then runs step4.
    Yields progress then final result (progress_html, audio, waveform).
    """
    if not edited_script or not edited_script.strip():
        yield _build_progress_html(0, 0, "No script to re-generate."), None, ""
        return
    if not notebook_id:
        yield _build_progress_html(0, 0, "No notebook selected."), None, ""
        return

    import json as _json, pickle
    from pathlib import Path as _Path
    from local_notebooklm.config import validate_config, base_config
    from local_notebooklm.steps.helpers import set_provider
    from local_notebooklm.steps.step4 import step4

    nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)
    step3_dir = _Path(nb_dir) / "step3"
    step4_dir = _Path(nb_dir) / "step4"
    step3_dir.mkdir(parents=True, exist_ok=True)
    step4_dir.mkdir(parents=True, exist_ok=True)

    # Write edited script to step3 output
    pkl_path = step3_dir / "podcast_ready_data.pkl"
    txt_path = step3_dir / "podcast_ready_data.txt"
    with open(pkl_path, 'wb') as f:
        pickle.dump(edited_script, f)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(edited_script)

    # Load config
    if config_file is not None:
        config_path = config_file.name if hasattr(config_file, 'name') else config_file
        with open(config_path, 'r') as f:
            config = _json.load(f)
    else:
        ollama_cfg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ollama_config.json",
        )
        if os.path.exists(ollama_cfg):
            with open(ollama_cfg, 'r') as f:
                config = _json.load(f)
        else:
            config = base_config

    # Apply voice overrides
    if host_voice and host_voice.strip():
        config["Host-Speaker-Voice"] = host_voice.strip()
    if cohost_voice and cohost_voice.strip():
        config["Co-Host-Speaker-1-Voice"] = cohost_voice.strip()

    yield _build_progress_html(1, 1, "Re-generating audio from edited script..."), None, ""

    try:
        tts_client = set_provider(config=config["Text-To-Speech-Model"]["provider"])
        step4(
            client=tts_client,
            config=config,
            input_dir=str(step3_dir),
            output_dir=str(step4_dir),
        )

        audio_path = None
        for ext in ["wav", "mp3", "ogg", "flac", "aac"]:
            candidate = os.path.join(str(step4_dir), f"podcast.{ext}")
            if os.path.exists(candidate):
                audio_path = candidate
                break

        waveform = _build_waveform_html(audio_path) if audio_path else ""
        yield (
            _build_progress_html(1, 1, "Audio re-generated", complete=True),
            audio_path,
            waveform,
        )
    except Exception as e:
        yield _build_progress_html(0, 0, f"Re-gen failed: {e}"), None, ""


def _on_export_notebook(notebook_id):
    """Export notebook as zip.  Returns file path for download."""
    if not notebook_id:
        return None
    import tempfile
    nb = _notebook_mgr.get_notebook(notebook_id)
    name_safe = nb.get("name", "notebook").replace(" ", "_").replace("/", "_")
    dest = os.path.join(tempfile.gettempdir(), f"{name_safe}.zip")
    return _notebook_mgr.export_notebook(notebook_id, dest)


def _on_import_notebook(zip_file):
    """Import a notebook from zip.  Returns updated dropdown + selected value."""
    if zip_file is None:
        return gr.update(), gr.update()
    file_path = zip_file.name if hasattr(zip_file, "name") else zip_file
    nb_id = _notebook_mgr.import_notebook(file_path)
    choices = _dropdown_choices()
    return gr.update(choices=choices, value=nb_id), gr.update(value=None)


def _process_batch(config_file, format_type, length, style, language,
                   additional_preference, skip_to, outputs_to_generate,
                   notebook_id, host_voice, cohost_voice, temperature):
    """Process ALL sources in the notebook sequentially.

    Yields (progress_html, audio, extracted, clean, script, infographic,
            infographic_file, png, pptx) like process_podcast.
    """
    if not notebook_id:
        yield _empty_result(_build_progress_html(0, 0, "No notebook selected."))
        return

    sources = _notebook_mgr.get_sources(notebook_id)
    if not sources:
        yield _empty_result(_build_progress_html(0, 0, "No sources to process."))
        return

    nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)
    total_sources = len(sources)
    last_result = None

    for src_idx, src in enumerate(sources):
        # Resolve input path for this source
        if src.get("type") == "file":
            input_path = os.path.join(nb_dir, "sources", src["filename"])
            if not os.path.exists(input_path):
                continue
        elif src.get("type") == "url":
            input_path = src["url"]
        else:
            continue

        src_label = src.get("filename", src.get("url", "unknown"))
        yield _empty_result(
            _build_progress_html(
                src_idx + 1, total_sources,
                f"Batch [{src_idx+1}/{total_sources}]: {src_label}"
            )
        )

        # Run the full pipeline for this source using process_podcast
        for result in process_podcast(
            None, input_path if src.get("type") == "url" else None,
            config_file, format_type, length, style, language,
            additional_preference, nb_dir, skip_to, outputs_to_generate,
            notebook_id, host_voice, cohost_voice, temperature,
            _source_file_override=input_path if src.get("type") == "file" else None,
        ):
            last_result = result
            yield result

    if last_result:
        yield last_result
    else:
        yield _empty_result(_build_progress_html(0, 0, "No processable sources found."))


# ---------------------------------------------------------------------------
# Processing logic
# ---------------------------------------------------------------------------

def _empty_result(status_msg):
    """Return a result tuple with only a status message and empty outputs."""
    return (status_msg, None, "", "", "", None, None, None, None)


def _pipeline_worker(job: PipelineJob, input_path, config, skip_to,
                     outputs_to_generate, format_type, length, style,
                     language, full_preference, notebook_id):
    """Run the step1-step5 pipeline in a background thread.

    This is a regular function (NOT a generator).  It mutates *job*
    via ``job.update()`` so the polling generator can relay progress
    to the Gradio frontend.
    """
    import json as _json
    from pathlib import Path as _Path
    from local_notebooklm.config import validate_config, base_config
    from local_notebooklm.steps.helpers import set_provider
    from local_notebooklm.steps.step1 import step1
    from local_notebooklm.steps.step2 import step2
    from local_notebooklm.steps.step3 import step3
    from local_notebooklm.steps.step4 import step4
    from local_notebooklm.steps.step5 import step5

    capture = _LogCapture()
    _logging.getLogger("local_notebooklm").addHandler(capture)

    output_dir = job.output_dir

    want_audio = "Podcast Audio" in outputs_to_generate
    want_html = "Infographic HTML" in outputs_to_generate
    want_png = "Infographic PNG" in outputs_to_generate
    want_pptx = "PPTX Slides" in outputs_to_generate
    want_any_infographic = want_html or want_png or want_pptx

    total_steps = 1
    if want_audio:
        total_steps += 3
    if want_any_infographic:
        total_steps += 1

    job.update(total_steps=total_steps)

    selected = ", ".join(outputs_to_generate)
    print(f"Processing with output_dir: {output_dir}")
    print(f"Generating: {selected}")

    output_base = _Path(output_dir)
    output_dirs = {f"step{i}": output_base / f"step{i}" for i in range(1, 6)}
    for dp in output_dirs.values():
        dp.mkdir(parents=True, exist_ok=True)

    small_text_client = set_provider(config=config["Small-Text-Model"]["provider"])
    big_text_client = set_provider(config=config["Big-Text-Model"]["provider"])
    tts_client = set_provider(config=config["Text-To-Speech-Model"]["provider"]) if want_audio else None

    system_prompts = {}
    for sn in ["step1", "step2", "step3"]:
        if sn in config and "system" in config[sn]:
            system_prompts[sn] = config[sn]["system"]
        elif "system" in config:
            system_prompts[sn] = config["system"]
        else:
            system_prompts[sn] = None

    current_step = 0
    cleaned_text_file = None
    transcript_file = None
    step_times: list[float] = []

    try:
        # ── Step 1: Extract text ─────────────────────────────
        current_step += 1
        job.update(current_step=current_step, step_label="Extracting text from document...")
        step_start = time.time()

        if not skip_to or skip_to <= 1:
            cleaned_text_file = step1(
                client=small_text_client,
                input_path=input_path,
                config=config,
                output_dir=str(output_dirs["step1"]),
                system_prompt=system_prompts["step1"],
            )
        else:
            step1_files = list(output_dirs["step1"].glob("*.txt"))
            if step1_files:
                cleaned_text_file = str(sorted(step1_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
            else:
                job.update(status="failed", error="No output files from Step 1. Cannot skip.",
                           failed_step=current_step, log_text=capture.get_text())
                _logging.getLogger("local_notebooklm").removeHandler(capture)
                return

        step_times.append(time.time() - step_start)
        job.update(step_times=list(step_times))

        if job.cancel_event.is_set():
            job.update(status="cancelled", log_text=capture.get_text())
            _logging.getLogger("local_notebooklm").removeHandler(capture)
            return

        # ── Steps 2-4: Podcast pipeline ──────────────────────
        if want_audio:
            # ── Step 2 ───────────────────────────────────────
            current_step += 1
            job.update(current_step=current_step, step_label="Generating transcript...")
            step_start = time.time()

            if not skip_to or skip_to <= 2:
                _, transcript_file = step2(
                    client=big_text_client,
                    config=config,
                    input_file=cleaned_text_file,
                    output_dir=str(output_dirs["step2"]),
                    format_type=format_type,
                    length=length,
                    style=style,
                    preference_text=full_preference,
                    system_prompt=system_prompts["step2"],
                )
            else:
                step2_files = list(output_dirs["step2"].glob("*.pkl"))
                if step2_files:
                    transcript_file = str(sorted(step2_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                else:
                    job.update(status="failed", error="No output files from Step 2. Cannot skip.",
                               failed_step=current_step, log_text=capture.get_text())
                    _logging.getLogger("local_notebooklm").removeHandler(capture)
                    return

            step_times.append(time.time() - step_start)
            job.update(step_times=list(step_times))

            if job.cancel_event.is_set():
                job.update(status="cancelled", log_text=capture.get_text())
                _logging.getLogger("local_notebooklm").removeHandler(capture)
                return

            # ── Step 3 ───────────────────────────────────────
            current_step += 1
            job.update(current_step=current_step, step_label="Optimizing for text-to-speech...")
            step_start = time.time()

            if not skip_to or skip_to <= 3:
                step3(
                    client=big_text_client,
                    config=config,
                    input_file=transcript_file,
                    output_dir=str(output_dirs["step3"]),
                    format_type=format_type,
                    system_prompt=system_prompts["step3"],
                    language=language,
                )

            step_times.append(time.time() - step_start)
            job.update(step_times=list(step_times))

            if job.cancel_event.is_set():
                job.update(status="cancelled", log_text=capture.get_text())
                _logging.getLogger("local_notebooklm").removeHandler(capture)
                return

            # ── Step 4 ───────────────────────────────────────
            current_step += 1
            job.update(current_step=current_step, step_label="Generating audio...")
            step_start = time.time()

            if not skip_to or skip_to <= 4:
                step4(
                    client=tts_client,
                    config=config,
                    input_dir=str(output_dirs["step3"]),
                    output_dir=str(output_dirs["step4"]),
                )

            step_times.append(time.time() - step_start)
            job.update(step_times=list(step_times))

            if job.cancel_event.is_set():
                job.update(status="cancelled", log_text=capture.get_text())
                _logging.getLogger("local_notebooklm").removeHandler(capture)
                return

        # ── Step 5: Generate infographic ─────────────────────
        if want_any_infographic:
            current_step += 1
            job.update(current_step=current_step, step_label="Generating infographic...")
            step_start = time.time()

            if not skip_to or skip_to <= 5:
                step5_input = str(output_dirs["step3"]) if want_audio else str(output_dirs["step1"])
                try:
                    step5(
                        client=big_text_client,
                        config=config,
                        input_dir=step5_input,
                        output_dir=str(output_dirs["step5"]),
                        generate_html=want_html,
                        generate_png=want_png,
                        generate_pptx=want_pptx,
                    )
                except Exception as e:
                    _log.warning("Step 5 (infographic) failed (non-fatal): %s", e)

            step_times.append(time.time() - step_start)
            job.update(step_times=list(step_times))

        # ── Record success ───────────────────────────────────
        log_text = capture.get_text()
        _logging.getLogger("local_notebooklm").removeHandler(capture)

        if notebook_id:
            from datetime import datetime, timezone
            generated = []
            # Check what was actually produced
            for subdir in [os.path.join(output_dir, "step4"), output_dir]:
                for ext in ["wav", "mp3", "ogg", "flac", "aac"]:
                    if os.path.exists(os.path.join(subdir, f"podcast.{ext}")):
                        generated.append("Audio")
                        break
                if "Audio" in generated:
                    break
            if os.path.exists(os.path.join(output_dir, "step5", "infographic.html")):
                generated.append("Infographic HTML")
            if os.path.exists(os.path.join(output_dir, "step5", "infographic.png")):
                generated.append("Infographic PNG")
            if os.path.exists(os.path.join(output_dir, "step5", "infographic.pptx")):
                generated.append("PPTX")

            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "format": format_type, "length": length, "style": style,
                "language": language,
                "duration_s": round(time.time() - job.gen_start, 1),
                "status": "success",
                "outputs": generated,
                "step_times": [round(t, 1) for t in step_times],
            }
            _notebook_mgr.add_history_entry(notebook_id, entry)

        job.update(status="completed", log_text=log_text)

    except Exception as e:
        import traceback
        log_text = capture.get_text()
        _logging.getLogger("local_notebooklm").removeHandler(capture)

        if notebook_id:
            from datetime import datetime, timezone
            _notebook_mgr.add_history_entry(notebook_id, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "format": format_type, "length": length, "style": style,
                "language": language,
                "duration_s": round(time.time() - job.gen_start, 1),
                "status": "failed",
                "outputs": [],
                "error": str(e)[:200],
            })

        job.update(
            status="failed",
            error=str(e)[:500] + "\n" + traceback.format_exc(),
            failed_step=current_step,
            log_text=log_text,
        )


def process_podcast(pdf_file, url_input, config_file, format_type, length, style,
                    language, additional_preference, output_dir, skip_to,
                    outputs_to_generate, notebook_id,
                    host_voice="", cohost_voice="", temperature=0.7,
                    selected_source_index=None, _source_file_override=None):
    """Thin polling generator — starts a background worker and yields progress.

    If the browser disconnects and the user clicks Generate again, this
    reconnects to the already-running job instead of starting a new one.
    """
    global _last_failed_step, _last_log_text

    # ── Reconnect to an existing running job ─────────────────
    if notebook_id and is_running(notebook_id):
        job = get_job(notebook_id)
        while True:
            snap = job.snapshot()
            if snap["status"] == "completed":
                _last_log_text = snap["log_text"]
                _last_failed_step = None
                result = _load_results_from_dir(job.output_dir)
                if result is None:
                    result = _empty_outputs()
                yield (
                    _build_progress_html(snap["total_steps"], snap["total_steps"],
                                         "Complete — reconnected", complete=True),
                    *result[1:],
                )
                remove_job(notebook_id)
                return
            elif snap["status"] in ("failed", "cancelled"):
                _last_failed_step = snap.get("failed_step")
                _last_log_text = snap["log_text"]
                err = snap.get("error", "Unknown error")
                diagnosis = _diagnose_error(Exception(err), _last_failed_step)
                diag_html = ""
                if diagnosis:
                    diag_html = (
                        f'<div style="margin-top:6px;padding:6px 10px;background:rgba(0,240,255,0.04);'
                        f'border-left:2px solid var(--neon-teal);font-family:var(--cds-font-mono);'
                        f'font-size:var(--cds-code-01-size);color:var(--neon-teal)">'
                        f'Suggestion: {diagnosis}</div>'
                    )
                yield _empty_result(
                    _build_progress_html(0, 0, f"Step {_last_failed_step or '?'} failed: {err.split(chr(10))[0]}")
                    + diag_html
                )
                remove_job(notebook_id)
                return
            else:
                eta = _format_eta(snap["step_times"], snap["current_step"], snap["total_steps"])
                yield _empty_result(
                    _build_progress_html(snap["current_step"], snap["total_steps"],
                                         snap["step_label"], eta)
                )
                time.sleep(1.5)

    # ── Validation (runs in the Gradio thread, lightweight) ──
    _last_failed_step = None

    input_path = _source_file_override
    if input_path is None and url_input and url_input.strip():
        input_path = url_input.strip()
    elif input_path is None and pdf_file is not None:
        input_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    elif input_path is None and notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id)
        nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)
        target_sources = sources
        if selected_source_index is not None and 0 <= selected_source_index < len(sources):
            target_sources = [sources[selected_source_index]]
        for src in target_sources:
            if src.get("type") == "file":
                fp = os.path.join(nb_dir, "sources", src["filename"])
                if os.path.exists(fp):
                    input_path = fp
                    break
            elif src.get("type") == "url":
                input_path = src["url"]
                break

    if input_path is None and (skip_to is None or skip_to <= 1):
        yield _empty_result("Please upload a document or enter a URL.")
        return

    if not output_dir:
        if notebook_id:
            output_dir = _notebook_mgr.get_notebook_dir(notebook_id)
        else:
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
        disk = shutil.disk_usage(output_dir)
        free_mb = disk.free / (1024 * 1024)
        if free_mb < 500:
            yield _empty_result(
                f"Low disk space: {free_mb:.0f} MB free. At least 500 MB recommended. "
                "Free up space before generating."
            )
            return
    except Exception:
        pass

    # ── Load & validate config (still in Gradio thread) ──────
    import json as _json
    from local_notebooklm.config import validate_config, ConfigValidationError, base_config

    if config_file is not None:
        config_path = config_file.name if hasattr(config_file, 'name') else config_file
        with open(config_path, 'r') as f:
            config = _json.load(f)
    else:
        ollama_cfg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ollama_config.json",
        )
        if os.path.exists(ollama_cfg):
            with open(ollama_cfg, 'r') as f:
                config = _json.load(f)
        else:
            config = base_config

    try:
        validate_config(config)
    except ConfigValidationError as e:
        yield _empty_result(f"Invalid configuration: {e}")
        return

    if host_voice and str(host_voice).strip():
        config["Host-Speaker-Voice"] = str(host_voice).strip()
    if cohost_voice and str(cohost_voice).strip():
        config["Co-Host-Speaker-1-Voice"] = str(cohost_voice).strip()
    if temperature is not None:
        temp_val = float(temperature)
        for step_key in ["Step1", "Step2", "Step3"]:
            if step_key in config:
                config[step_key]["temperature"] = temp_val

    # Speaker personality injection
    full_preference = additional_preference or ""
    if notebook_id:
        nb_settings = _notebook_mgr.get_settings(notebook_id)
        personality = nb_settings.get("speaker_personality", "")
        if personality and personality.strip():
            full_preference = (
                f"SPEAKER PERSONALITIES:\n{personality.strip()}\n\n"
                + full_preference
            )
    full_preference = full_preference.strip() or None

    # ── Spawn background worker ──────────────────────────────
    job_id = notebook_id or "default"
    job = start_job(
        notebook_id=job_id,
        output_dir=output_dir,
        worker_fn=_pipeline_worker,
        worker_args=(input_path, config, skip_to, outputs_to_generate,
                     format_type, length, style, language, full_preference,
                     notebook_id),
    )

    # ── Poll loop ────────────────────────────────────────────
    while True:
        snap = job.snapshot()

        if snap["status"] == "completed":
            _last_log_text = snap["log_text"]
            _last_failed_step = None
            result = _load_results_from_dir(output_dir)
            if result is None:
                result = _empty_outputs()

            generated_parts = []
            if result[1]:  # audio_path
                generated_parts.append("Audio")
            if result[5]:  # infographic_html
                generated_parts.append("Infographic HTML")
            if result[7]:  # png_image
                generated_parts.append("Infographic PNG")
            if result[8]:  # pptx_file
                generated_parts.append("PPTX")

            gen_label = f"Generated: {', '.join(generated_parts)}" if generated_parts else "Complete"
            yield (
                _build_progress_html(snap["total_steps"], snap["total_steps"],
                                     gen_label, complete=True),
                *result[1:],
            )
            remove_job(job_id)
            return

        elif snap["status"] in ("failed", "cancelled"):
            _last_failed_step = snap.get("failed_step")
            _last_log_text = snap["log_text"]
            err = snap.get("error", "Unknown error")
            err_first_line = err.split("\n")[0]
            diagnosis = _diagnose_error(Exception(err_first_line), _last_failed_step)
            diag_html = ""
            if diagnosis:
                diag_html = (
                    f'<div style="margin-top:6px;padding:6px 10px;background:rgba(0,240,255,0.04);'
                    f'border-left:2px solid var(--neon-teal);font-family:var(--cds-font-mono);'
                    f'font-size:var(--cds-code-01-size);color:var(--neon-teal)">'
                    f'Suggestion: {diagnosis}</div>'
                )
            # Include traceback if available
            tb_html = ""
            if "\n" in err:
                tb_text = err[err.index("\n")+1:]
                if tb_text.strip():
                    escaped_tb = (tb_text.replace("&", "&amp;").replace("<", "&lt;")
                                  .replace(">", "&gt;"))
                    tb_html = f'\n<details><summary>Full traceback</summary><pre>{escaped_tb}</pre></details>'
            yield _empty_result(
                _build_progress_html(0, 0, f"Step {_last_failed_step or '?'} failed: {err_first_line}")
                + diag_html + tb_html
            )
            remove_job(job_id)
            return

        else:
            eta = _format_eta(snap["step_times"], snap["current_step"], snap["total_steps"])
            yield _empty_result(
                _build_progress_html(snap["current_step"], snap["total_steps"],
                                     snap["step_label"], eta)
            )
            time.sleep(1.5)


def _on_stop(notebook_id):
    """Cancel the background pipeline job for the given notebook."""
    job_id = notebook_id or "default"
    cancel_job(job_id)


# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------

def create_gradio_ui():
    format_options = list(FormatType.__args__) if hasattr(FormatType, '__args__') else ["podcast"]
    length_options = list(LengthType.__args__) if hasattr(LengthType, '__args__') else ["medium"]
    style_options = list(StyleType.__args__) if hasattr(StyleType, '__args__') else ["conversational"]

    # Pre-compute initial notebook state
    initial_choices = _dropdown_choices()
    initial_default = _notebook_mgr.get_default_notebook_id()

    with gr.Blocks(title="Local-NotebookLM", analytics_enabled=False) as app:

        # ── Header bar ────────────────────────────────────────
        gr.HTML(HEADER_HTML)
        health_banner = gr.HTML(value="", elem_id="health-banner")

        # ── Notebook tabs ─────────────────────────────────────
        notebook_selector = gr.Radio(
            choices=initial_choices,
            value=initial_default,
            label="",
            elem_id="notebook-tabs",
            container=False,
        )

        # ── Notebook actions bar ──────────────────────────────
        with gr.Row(elem_classes="notebook-bar"):
            notebook_name_input = gr.Textbox(
                placeholder="notebook name...",
                scale=2,
                container=False,
                show_label=False,
            )
            btn_new = gr.Button("+ New", size="sm", variant="secondary", elem_classes="nb-btn", scale=0)
            btn_rename = gr.Button("Rename", size="sm", variant="secondary", elem_classes="nb-btn", scale=0)
            btn_export = gr.Button("Export", size="sm", variant="secondary", elem_classes="nb-btn", scale=0)
            btn_import = gr.Button("Import", size="sm", variant="secondary", elem_classes="nb-btn", scale=0)
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
                    with gr.Row():
                        source_selector = gr.Dropdown(
                            choices=[],
                            value=None,
                            label="Select Source",
                            scale=3,
                            container=True,
                        )
                        btn_remove_source = gr.Button(
                            "Remove",
                            size="sm",
                            variant="stop",
                            elem_classes="nb-btn",
                            scale=0,
                        )
                    with gr.Accordion("Source Content", open=False, elem_classes="cyber-accordion"):
                        source_content_viewer = gr.Textbox(
                            label="Preview",
                            lines=10,
                            interactive=False,
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

                # Progress display (HUD bar)
                progress_display = gr.HTML(
                    value="",
                    elem_id="progress-display",
                )

                # Audio output + waveform
                with gr.Group(elem_classes="results-section"):
                    audio_output = gr.Audio(
                        label="Podcast Audio",
                        type="filepath",
                        elem_id="audio-player",
                    )
                    waveform_display = gr.HTML(value="", elem_id="waveform-area")
                    audio_metrics_display = gr.HTML(value="", elem_id="audio-metrics")

                # Infographic preview
                infographic_preview = gr.HTML(label="Infographic Preview")

                # Downloads
                with gr.Row(elem_classes="download-row"):
                    infographic_download = gr.File(label="Infographic HTML")
                    pptx_download = gr.File(label="PPTX Slides")

                # Infographic PNG
                png_preview = gr.Image(
                    label="Infographic PNG",
                    type="filepath",
                )

                # Pipeline data (collapsed) — script is editable
                with gr.Accordion("Extracted Text", open=False, elem_classes="cyber-accordion"):
                    extracted_text = gr.Textbox(label="Extracted Text", lines=8)
                with gr.Accordion("Clean Text", open=False, elem_classes="cyber-accordion"):
                    clean_text = gr.Textbox(label="Clean Extracted Text", lines=8)
                with gr.Accordion("Podcast Script (editable)", open=False, elem_classes="cyber-accordion"):
                    audio_script = gr.Textbox(
                        label="Podcast Script",
                        lines=10,
                        interactive=True,
                        info="Edit the script then click Re-generate Audio",
                    )
                    script_stats_display = gr.HTML(value="", elem_id="script-stats")
                    with gr.Row():
                        btn_regen_audio = gr.Button(
                            "Re-generate Audio from Script",
                            variant="secondary",
                            elem_id="regen-audio-btn",
                            scale=3,
                        )
                        btn_download_script = gr.Button(
                            "Download Script (.md)",
                            variant="secondary",
                            size="sm",
                            scale=1,
                        )
                    script_download_file = gr.File(visible=False)

                # Pipeline log viewer
                with gr.Accordion("Pipeline Logs", open=False, elem_classes="cyber-accordion"):
                    log_viewer = gr.HTML(value="", elem_id="log-viewer")

                # Generation history
                with gr.Accordion("Generation History", open=False, elem_classes="cyber-accordion"):
                    history_display = gr.HTML(value="", elem_id="history-display")

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

                    # Preset selector
                    preset_selector = gr.Dropdown(
                        choices=list(_PRESETS.keys()),
                        value="Custom",
                        label="Preset",
                        elem_classes="preset-pills",
                    )

                    # Settings 2x2 grid
                    gr.HTML('<div class="cyber-card-label" style="margin-top:0.8rem">Settings</div>')
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

                    # Temperature
                    temperature_slider = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=0.7,
                        step=0.1,
                        label="Creativity",
                    )
                    temp_explainer = gr.HTML(
                        value=_build_temp_explainer_html(0.7),
                        elem_id="temp-explainer",
                    )

                    # Generate + Stop buttons
                    with gr.Row():
                        generate_button = gr.Button(
                            "Generate",
                            variant="primary",
                            elem_id="generate-btn",
                            scale=3,
                        )
                        stop_button = gr.Button(
                            "Stop",
                            variant="stop",
                            elem_id="stop-btn",
                            scale=1,
                        )
                    with gr.Row():
                        btn_batch = gr.Button(
                            "Batch All Sources",
                            variant="secondary",
                            size="sm",
                            scale=3,
                        )
                        btn_retry = gr.Button(
                            "Retry Failed Step",
                            elem_id="retry-btn",
                            size="sm",
                            visible=False,
                            scale=1,
                        )
                    gr.HTML('<p class="kbd-hint"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> to generate</p>')

                    # Voice & advanced options
                    with gr.Accordion("Voice & Advanced", open=False, elem_classes="cyber-accordion"):
                        host_voice = gr.Textbox(
                            label="Host Voice",
                            placeholder="e.g. af_alloy",
                            info="TTS voice ID for Speaker 1",
                        )
                        cohost_voice = gr.Textbox(
                            label="Co-Host Voice",
                            placeholder="e.g. af_sky+af_bella",
                            info="TTS voice ID for Speaker 2",
                        )
                        btn_voice_preview = gr.Button(
                            "Preview Voice",
                            variant="secondary",
                            size="sm",
                        )
                        voice_preview_audio = gr.Audio(
                            label="Voice Preview",
                            type="filepath",
                            visible=True,
                        )
                        speaker_personality = gr.Textbox(
                            label="Speaker Personalities",
                            placeholder="e.g. Speaker 1 is enthusiastic and uses analogies. Speaker 2 is skeptical and probing.",
                            lines=3,
                            info="Describe each speaker's personality to shape the conversation",
                        )
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

        # ── Footer ────────────────────────────────────────────
        gr.HTML(FOOTER_HTML)

        # ── Hidden components for export / import ────────────
        with gr.Row(visible=False):
            export_download = gr.File(label="Export Download", visible=False)
        import_file = gr.File(
            label="Import Notebook (.zip)",
            file_types=[".zip"],
            visible=False,
        )

        # ── Keyboard shortcut JS ─────────────────────────────
        gr.HTML("""
        <script>
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                var btn = document.querySelector('#generate-btn button');
                if (btn) btn.click();
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
                e.preventDefault();
                var nbBtn = document.querySelectorAll('.nb-btn button');
                if (nbBtn.length > 0) nbBtn[0].click();
            }
        });
        </script>
        """)

        switch_outputs = [
            sources_display, source_selector, source_content_viewer,
            progress_display, audio_output, extracted_text, clean_text,
            audio_script, infographic_preview, infographic_download,
            png_preview, pptx_download,
            format_type, length, style, language, outputs_to_generate,
            output_dir, host_voice, cohost_voice, temperature_slider,
            log_viewer, history_display, speaker_personality,
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
            outputs=[sources_display, source_selector, source_content_viewer],
            show_progress="hidden",
        )

        url_input.submit(
            fn=_on_url_add,
            inputs=[url_input, notebook_selector],
            outputs=[sources_display, url_input, source_selector, source_content_viewer],
            show_progress="hidden",
        )

        # ── Wiring — Source selection & removal ──────────────
        source_selector.change(
            fn=_on_source_select,
            inputs=[source_selector, notebook_selector],
            outputs=[source_content_viewer],
            show_progress="hidden",
        )

        btn_remove_source.click(
            fn=_on_remove_source,
            inputs=[source_selector, notebook_selector],
            outputs=[sources_display, source_selector, source_content_viewer],
            show_progress="hidden",
        )

        # ── Wiring — Auto-save settings on change ────────────
        for setting_component in [format_type, length, style, language,
                                  outputs_to_generate, host_voice, cohost_voice,
                                  temperature_slider, speaker_personality]:
            setting_component.change(
                fn=_on_settings_change,
                inputs=[notebook_selector, format_type, length, style, language,
                        outputs_to_generate, host_voice, cohost_voice,
                        temperature_slider, speaker_personality],
                outputs=None,
                show_progress="hidden",
            )

        # ── Wiring — Generate ─────────────────────────────────
        generate_inputs = [
            pdf_file, url_input, config_file, format_type, length, style,
            language, additional_preference, output_dir, skip_to,
            outputs_to_generate, notebook_selector,
            host_voice, cohost_voice, temperature_slider,
            source_selector,
        ]
        generate_outputs = [
            progress_display, audio_output, extracted_text, clean_text,
            audio_script, infographic_preview, infographic_download,
            png_preview, pptx_download,
        ]

        gen_event = generate_button.click(
            fn=process_podcast,
            inputs=generate_inputs,
            outputs=generate_outputs,
            show_progress="hidden",
        ).then(
            fn=_post_generate,
            inputs=[notebook_selector],
            outputs=[log_viewer, history_display, btn_retry],
            show_progress="hidden",
        )

        # ── Wiring — Batch all sources ───────────────────────
        batch_event = btn_batch.click(
            fn=_process_batch,
            inputs=[config_file, format_type, length, style, language,
                    additional_preference, skip_to, outputs_to_generate,
                    notebook_selector, host_voice, cohost_voice, temperature_slider],
            outputs=generate_outputs,
            show_progress="hidden",
        ).then(
            fn=_post_generate,
            inputs=[notebook_selector],
            outputs=[log_viewer, history_display, btn_retry],
            show_progress="hidden",
        )

        # ── Wiring — Cancel / Stop ───────────────────────────
        stop_button.click(
            fn=_on_stop,
            inputs=[notebook_selector],
            outputs=None,
            cancels=[gen_event, batch_event],
        )

        # ── Wiring — Retry failed step ───────────────────────
        btn_retry.click(
            fn=_on_retry,
            inputs=generate_inputs,
            outputs=generate_outputs,
            show_progress="hidden",
        ).then(
            fn=_post_generate,
            inputs=[notebook_selector],
            outputs=[log_viewer, history_display, btn_retry],
            show_progress="hidden",
        )

        # ── Wiring — Preset selector ─────────────────────────
        preset_selector.change(
            fn=_on_preset_select,
            inputs=[preset_selector],
            outputs=[format_type, length, style, language, temperature_slider],
            show_progress="hidden",
        )

        # ── Wiring — Re-generate audio from edited script ────
        btn_regen_audio.click(
            fn=_on_regen_audio,
            inputs=[audio_script, notebook_selector, config_file,
                    host_voice, cohost_voice],
            outputs=[progress_display, audio_output, waveform_display],
            show_progress="hidden",
        )

        # ── Wiring — Download script as Markdown ──────────────
        btn_download_script.click(
            fn=_on_download_script,
            inputs=[audio_script, notebook_selector],
            outputs=[script_download_file],
            show_progress="hidden",
        )

        # ── Wiring — Export / Import ─────────────────────────
        btn_export.click(
            fn=_on_export_notebook,
            inputs=[notebook_selector],
            outputs=[export_download],
            show_progress="hidden",
        )

        btn_import.click(
            fn=lambda: gr.update(visible=True),
            inputs=None,
            outputs=[import_file],
            show_progress="hidden",
        )

        import_file.change(
            fn=_on_import_notebook,
            inputs=[import_file],
            outputs=[notebook_selector, import_file],
            show_progress="hidden",
        ).then(
            fn=_on_notebook_switch,
            inputs=[notebook_selector],
            outputs=switch_outputs,
            show_progress="hidden",
        )

        # ── Wiring — Audio waveform + metrics on playback ────
        audio_output.change(
            fn=lambda a: _build_waveform_html(a) if a else "",
            inputs=[audio_output],
            outputs=[waveform_display],
            show_progress="hidden",
        )
        audio_output.change(
            fn=_build_audio_metrics_html,
            inputs=[audio_output],
            outputs=[audio_metrics_display],
            show_progress="hidden",
        )

        # ── Wiring — Script word count + duration ────────────
        audio_script.change(
            fn=_build_script_stats_html,
            inputs=[audio_script],
            outputs=[script_stats_display],
            show_progress="hidden",
        )

        # ── Wiring — Temperature explainer ───────────────────
        temperature_slider.change(
            fn=_build_temp_explainer_html,
            inputs=[temperature_slider],
            outputs=[temp_explainer],
            show_progress="hidden",
        )

        # ── Wiring — Voice preview ───────────────────────────
        btn_voice_preview.click(
            fn=_on_voice_preview,
            inputs=[host_voice, cohost_voice, config_file],
            outputs=[voice_preview_audio],
            show_progress="minimal",
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
        ).then(
            fn=_check_provider_health,
            inputs=None,
            outputs=[health_banner],
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
