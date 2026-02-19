import logging as _logging
import os
import shutil
import subprocess
import time
import gradio as gr
import argparse
from local_notebooklm.steps.helpers import LengthType, FormatType, StyleType, SkipToOptions
from local_notebooklm.notebook_manager import NotebookManager

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
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root variables ──────────────────────────────────────────── */
:root {
    --neon-cyan: #00f0ff;
    --neon-teal: #3bd6c6;
    --neon-magenta: #ff00aa;
    --neon-pink: #dd368a;
    --neon-purple: #b400ff;
    --neon-red: #ff3a3a;
    --true-black: #000000;
    --dark-bg: #000000;
    --card-bg: #0a0a14;
    --card-border: #1a1a3a;
    --text-primary: #d8d8ec;
    --text-muted: #6e6e8e;
    --glow-cyan: 0 0 8px rgba(0,240,255,0.3), 0 0 24px rgba(0,240,255,0.1);
    --glow-teal: 0 0 8px rgba(59,214,198,0.3), 0 0 24px rgba(59,214,198,0.1);
    --glow-magenta: 0 0 8px rgba(255,0,170,0.3), 0 0 24px rgba(255,0,170,0.1);
    --glow-pink: 0 0 8px rgba(221,54,138,0.3), 0 0 24px rgba(221,54,138,0.1);
    --panel-bg: #04040c;
    --panel-border: #141430;
    --cut: 8px;
    --cut-lg: 14px;
}

/* ── Clipped corner utility ─────────────────────────────────── */
.cp-clip {
    clip-path: polygon(
        0 var(--cut), var(--cut) 0,
        calc(100% - var(--cut)) 0, 100% var(--cut),
        100% calc(100% - var(--cut)), calc(100% - var(--cut)) 100%,
        var(--cut) 100%, 0 calc(100% - var(--cut))
    );
}

/* ── Animated background ─────────────────────────────────────── */
.gradio-container {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(0,240,255,0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 90%, rgba(221,54,138,0.025) 0%, transparent 50%),
        #000000 !important;
    min-height: 100vh;
}

/* ── Scan-line + grid overlay ────────────────────────────────── */
.gradio-container::before {
    content: "";
    position: fixed;
    inset: 0;
    background:
        repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,240,255,0.012) 2px, rgba(0,240,255,0.012) 4px),
        repeating-linear-gradient(90deg, transparent, transparent 80px, rgba(0,240,255,0.015) 80px, rgba(0,240,255,0.015) 81px),
        repeating-linear-gradient(0deg, transparent, transparent 80px, rgba(0,240,255,0.015) 80px, rgba(0,240,255,0.015) 81px);
    pointer-events: none;
    z-index: 9999;
}

/* ── HUD Header bar ──────────────────────────────────────────── */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1.5rem;
    background: linear-gradient(180deg, rgba(0,240,255,0.04) 0%, var(--panel-bg) 100%);
    border-bottom: 2px solid var(--neon-cyan);
    position: relative;
}
.header-bar::after {
    content: "";
    position: absolute;
    bottom: -2px;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, var(--neon-cyan), transparent 30%, transparent 70%, var(--neon-pink));
    filter: blur(4px);
}
.header-bar .hud-label {
    font-family: 'Rajdhani', 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    color: var(--text-muted);
    letter-spacing: 0.25em;
    text-transform: uppercase;
}
.header-bar .title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--neon-cyan);
    text-shadow: 0 0 12px rgba(0,240,255,0.3);
}
.header-bar .title .accent {
    color: var(--neon-pink);
}
.header-bar .pipeline-chips {
    display: flex;
    gap: 0;
    align-items: center;
}
.header-bar .pipeline-chips .chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    color: var(--neon-cyan);
    padding: 0.25rem 0.6rem;
    border: 1px solid rgba(0,240,255,0.2);
    border-right: none;
    background: rgba(0,240,255,0.03);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    transition: all 0.3s;
}
.header-bar .pipeline-chips .chip:first-child {
    clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 50%, calc(100% - 6px) 100%, 0 100%);
    padding-right: 1rem;
}
.header-bar .pipeline-chips .chip:last-child {
    clip-path: polygon(6px 0, 100% 0, 100% 100%, 6px 100%, 0 50%);
    padding-left: 1rem;
    border-right: 1px solid rgba(0,240,255,0.2);
}
.header-bar .pipeline-chips .chip:not(:first-child):not(:last-child) {
    clip-path: polygon(6px 0, calc(100% - 6px) 0, 100% 50%, calc(100% - 6px) 100%, 6px 100%, 0 50%);
    padding-left: 1rem;
    padding-right: 1rem;
}
.header-bar .page-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.1em;
}

/* ── 3-Panel layout ──────────────────────────────────────────── */
.panel {
    background: var(--panel-bg) !important;
    border: none !important;
    min-height: calc(100vh - 100px);
    padding: 0 !important;
    position: relative;
}
.panel-left {
    border-right: 1px solid var(--panel-border) !important;
}
.panel-left::before {
    content: "";
    position: absolute;
    top: 0;
    right: -1px;
    width: 1px;
    height: 40px;
    background: var(--neon-cyan);
    box-shadow: 0 0 6px var(--neon-cyan);
}
.panel-right {
    border-left: 1px solid var(--panel-border) !important;
}
.panel-right::before {
    content: "";
    position: absolute;
    top: 0;
    left: -1px;
    width: 1px;
    height: 40px;
    background: var(--neon-pink);
    box-shadow: 0 0 6px var(--neon-pink);
}
.panel-header {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--neon-cyan);
    padding: 0.9rem 1rem 0.6rem;
    border-bottom: 1px solid rgba(0,240,255,0.15);
    margin-bottom: 0.5rem;
    position: relative;
}
.panel-header::before {
    content: "//";
    margin-right: 0.5rem;
    color: var(--neon-pink);
    opacity: 0.6;
}
.panel-content {
    padding: 0.5rem 0.8rem 1rem;
}
.panel-empty {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: center;
    padding: 2rem 1rem;
    line-height: 1.6;
    letter-spacing: 0.04em;
}

/* ── HUD Frame — decorative corner brackets on center panel ──── */
.panel:not(.panel-left):not(.panel-right) {
    position: relative;
}
.panel:not(.panel-left):not(.panel-right)::before,
.panel:not(.panel-left):not(.panel-right)::after {
    content: "";
    position: absolute;
    width: 20px;
    height: 20px;
    border-color: var(--neon-cyan);
    border-style: solid;
    opacity: 0.4;
    z-index: 1;
    pointer-events: none;
}
.panel:not(.panel-left):not(.panel-right)::before {
    top: 4px;
    left: 4px;
    border-width: 2px 0 0 2px;
}
.panel:not(.panel-left):not(.panel-right)::after {
    bottom: 4px;
    right: 4px;
    border-width: 0 2px 2px 0;
}

/* ── Section cards — angular ─────────────────────────────────── */
.cyber-card {
    background: var(--card-bg) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 0 !important;
    padding: 1.2rem !important;
    position: relative;
    clip-path: polygon(
        0 var(--cut), var(--cut) 0,
        100% 0, 100% calc(100% - var(--cut)),
        calc(100% - var(--cut)) 100%, 0 100%
    );
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.cyber-card:hover {
    border-color: rgba(59,214,198,0.3) !important;
    box-shadow: var(--glow-teal);
}
.cyber-card-label {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--neon-cyan) !important;
    margin-bottom: 0.8rem !important;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(0,240,255,0.15);
}
.cyber-card-label::before {
    content: "// ";
    color: var(--neon-pink);
    opacity: 0.6;
}

/* ── Generate button — angular HUD style ─────────────────────── */
#generate-btn {
    margin-top: 0.5rem;
}
#generate-btn button {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 0.9rem 1.5rem !important;
    border-radius: 0 !important;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease !important;
    background: var(--neon-cyan) !important;
    color: #000 !important;
    clip-path: polygon(
        0 0, calc(100% - 12px) 0, 100% 12px,
        100% 100%, 12px 100%, 0 calc(100% - 12px)
    );
}
#generate-btn button:hover {
    background: var(--neon-teal) !important;
    box-shadow: 0 0 20px rgba(0,240,255,0.4), 0 0 40px rgba(0,240,255,0.15) !important;
}
#generate-btn button::after {
    content: "";
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    animation: btnSweep 3s ease-in-out infinite;
}
@keyframes btnSweep {
    0% { left: -100%; }
    50% { left: 100%; }
    100% { left: 100%; }
}

/* ── Progress bar ───────────────────────────────────────────── */
.progress-hud {
    border: 1px solid var(--card-border);
    background: var(--card-bg);
    padding: 0.8rem 1rem;
    position: relative;
    clip-path: polygon(0 0, calc(100% - var(--cut)) 0, 100% var(--cut), 100% 100%, var(--cut) 100%, 0 calc(100% - var(--cut)));
}
.progress-steps {
    display: flex;
    gap: 0;
    margin-bottom: 0.6rem;
}
.progress-step {
    flex: 1;
    height: 4px;
    background: var(--panel-border);
    position: relative;
    transition: background 0.5s ease;
}
.progress-step.done {
    background: var(--neon-cyan);
    box-shadow: 0 0 6px rgba(0,240,255,0.4);
}
.progress-step.active {
    background: linear-gradient(90deg, var(--neon-cyan), var(--neon-teal));
    animation: progressPulse 1.5s ease-in-out infinite;
}
@keyframes progressPulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(0,240,255,0.3); }
    50% { opacity: 0.7; box-shadow: 0 0 12px rgba(0,240,255,0.6); }
}
.progress-step + .progress-step { margin-left: 3px; }
.progress-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-primary);
    letter-spacing: 0.04em;
}
.progress-eta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--neon-teal);
    float: right;
}
.progress-complete {
    color: var(--neon-cyan);
    text-shadow: 0 0 8px rgba(0,240,255,0.3);
}

/* ── Waveform container ────────────────────────────────────── */
.waveform-wrap {
    border: 1px solid var(--card-border);
    background: var(--card-bg);
    padding: 0.4rem;
    margin-top: 0.4rem;
    min-height: 48px;
    position: relative;
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
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border: 1px solid rgba(0,240,255,0.25) !important;
    background: rgba(0,240,255,0.04) !important;
    color: var(--neon-cyan) !important;
}
#regen-audio-btn button:hover {
    border-color: var(--neon-cyan) !important;
    box-shadow: var(--glow-cyan);
}

/* ── Keyboard hint ─────────────────────────────────────────── */
.kbd-hint {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--text-muted);
    text-align: center;
    padding: 0.3rem 0;
    letter-spacing: 0.06em;
    opacity: 0.6;
}
.kbd-hint kbd {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    padding: 0.1rem 0.35rem;
    font-size: 0.58rem;
    color: var(--neon-teal);
}

/* ── Status output (legacy compat) ─────────────────────────── */
#status-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
    border: 1px solid var(--card-border) !important;
    border-left: 3px solid var(--neon-cyan) !important;
    border-radius: 0 !important;
    background: var(--card-bg) !important;
    transition: border-color 0.3s, box-shadow 0.3s;
}

/* ── Audio player — angular ──────────────────────────────────── */
#audio-player {
    border: 1px solid var(--card-border) !important;
    border-radius: 0 !important;
    background: var(--card-bg) !important;
    overflow: hidden;
    clip-path: polygon(
        0 0, calc(100% - var(--cut)) 0, 100% var(--cut),
        100% 100%, var(--cut) 100%, 0 calc(100% - var(--cut))
    );
}
#audio-player audio {
    filter: hue-rotate(160deg) saturate(1.5);
}

/* ── Accordion — angular neon ────────────────────────────────── */
.cyber-accordion .label-wrap {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em;
    border-bottom: 1px solid transparent !important;
    border-left: 2px solid transparent !important;
    padding-left: 0.6rem !important;
    transition: all 0.3s ease;
    color: var(--text-muted) !important;
}
.cyber-accordion .label-wrap:hover {
    color: var(--neon-cyan) !important;
    border-left-color: var(--neon-cyan) !important;
}
.cyber-accordion .label-wrap .icon {
    color: var(--neon-teal) !important;
}

/* ── File upload — dashed angular ────────────────────────────── */
.cyber-upload .upload-container,
.cyber-upload [data-testid="droparea"] {
    border: 1px dashed rgba(0,240,255,0.25) !important;
    border-radius: 0 !important;
    background: rgba(0,240,255,0.015) !important;
    transition: all 0.3s ease;
}
.cyber-upload .upload-container:hover,
.cyber-upload [data-testid="droparea"]:hover {
    border-color: rgba(59,214,198,0.5) !important;
    background: rgba(59,214,198,0.03) !important;
    box-shadow: var(--glow-teal);
}

/* ── Dropdown / select ───────────────────────────────────────── */
.gradio-container select,
.gradio-container .wrap.svelte-1s0gk1z,
.gradio-container .secondary-wrap {
    background: var(--card-bg) !important;
    border-color: var(--card-border) !important;
    border-radius: 0 !important;
    color: var(--text-primary) !important;
}

/* ── Output selector — angular card grid ─────────────────────── */
.output-selector label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem !important;
    letter-spacing: 0.06em;
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
    padding: 0.55rem 0.65rem !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 0 !important;
    background: var(--card-bg) !important;
    cursor: pointer;
    transition: all 0.25s ease;
    clip-path: polygon(
        0 0, calc(100% - 6px) 0, 100% 6px,
        100% 100%, 6px 100%, 0 calc(100% - 6px)
    );
}
.output-selector .wrap > label:hover {
    border-color: var(--neon-teal) !important;
    box-shadow: var(--glow-teal);
}
.output-selector .wrap > label:has(input:checked) {
    border-color: var(--neon-cyan) !important;
    background: rgba(0,240,255,0.07) !important;
    box-shadow: inset 0 0 12px rgba(0,240,255,0.06);
}
.output-selector input[type="checkbox"] {
    accent-color: var(--neon-cyan) !important;
}

/* ── Scrollbar — thin neon ───────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--dark-bg); }
::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--neon-cyan), var(--neon-pink));
    border-radius: 0;
}

/* ── Footer — HUD line ───────────────────────────────────────── */
.cyber-footer {
    text-align: center;
    padding: 0.8rem 1rem 1.2rem;
    margin-top: 0;
    position: relative;
}
.cyber-footer .divider {
    height: 2px;
    background: var(--neon-pink);
    margin-bottom: 0.8rem;
    position: relative;
}
.cyber-footer .divider::before,
.cyber-footer .divider::after {
    content: "";
    position: absolute;
    top: -3px;
    width: 8px;
    height: 8px;
    border: 2px solid var(--neon-pink);
    background: var(--panel-bg);
    transform: rotate(45deg);
}
.cyber-footer .divider::before { left: 20px; }
.cyber-footer .divider::after { right: 20px; }
.cyber-footer p {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
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

/* ── Input fields — angular ──────────────────────────────────── */
.gradio-container textarea,
.gradio-container input[type="text"] {
    caret-color: var(--neon-cyan) !important;
    border-radius: 0 !important;
}
.gradio-container textarea:focus,
.gradio-container input[type="text"]:focus {
    border-color: var(--neon-cyan) !important;
    box-shadow: 0 0 8px rgba(0,240,255,0.15) !important;
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
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    line-height: 1.6;
}

/* ── Notebook bar — angular ──────────────────────────────────── */
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
    font-size: 0.68rem !important;
    padding: 0.3rem 0.65rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    clip-path: polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 5px 100%, 0 calc(100% - 5px));
}

/* ── Source list in left panel ───────────────────────────────── */
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
    border-left: 2px solid var(--neon-teal);
    border-radius: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-primary);
    transition: border-color 0.25s, box-shadow 0.25s;
}
.source-item:hover {
    border-color: rgba(59,214,198,0.4);
    border-left-color: var(--neon-cyan);
    box-shadow: var(--glow-teal);
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
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-muted);
    text-align: center;
    padding: 1rem 0.5rem;
    letter-spacing: 0.04em;
}

/* ── All Gradio labels — monospace ───────────────────────────── */
.gradio-container label span {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted) !important;
}

/* ── Secondary / stop buttons ────────────────────────────────── */
.gradio-container button.secondary {
    border-radius: 0 !important;
    border: 1px solid var(--card-border) !important;
    background: var(--card-bg) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.06em;
    transition: all 0.25s;
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
    box-shadow: 0 0 8px rgba(255,58,58,0.2);
}

/* ── Health banner ─────────────────────────────────── */
.health-banner {
    background: rgba(255,58,58,0.06);
    border: 1px solid rgba(255,58,58,0.25);
    padding: 8px 16px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: #ff8888;
    clip-path: polygon(0 0,100% 0,99.5% 100%,0.5% 100%);
}

/* ── Preset pills ──────────────────────────────────── */
#preset-selector .wrap { gap: 4px !important; }
#preset-selector label {
    font-size: 11px !important;
    padding: 3px 10px !important;
    border-radius: 0 !important;
    clip-path: polygon(4px 0,100% 0,calc(100% - 4px) 100%,0 100%);
}

/* ── Stop button ───────────────────────────────────── */
#stop-btn button {
    background: rgba(255,58,58,0.08) !important;
    border: 1px solid rgba(255,58,58,0.3) !important;
    color: #ff6666 !important;
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
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: 11px;
}
.log-viewer summary {
    cursor: pointer;
    color: var(--text-muted);
    padding: 4px 0;
}
.log-viewer pre {
    max-height: 200px;
    overflow-y: auto;
    background: rgba(0,0,0,0.4);
    padding: 8px;
    border: 1px solid #1e1e40;
    color: #8888aa;
    white-space: pre-wrap;
    word-break: break-all;
}

/* ── History timeline ──────────────────────────────── */
.history-timeline { display: flex; flex-direction: column; gap: 6px; }
.history-empty { color: var(--text-muted); font-size: 12px; padding: 8px 0; }
.hist-entry {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 6px 10px;
    border-left: 2px solid var(--neon-teal);
    background: rgba(0,240,255,0.02);
    font-family: var(--font-mono);
    font-size: 11px;
}
.hist-entry.fail { border-left-color: var(--neon-red); background: rgba(255,58,58,0.02); }
.hist-ts { color: var(--text-muted); min-width: 120px; }
.hist-badge {
    background: rgba(0,240,255,0.08);
    padding: 1px 6px;
    color: var(--neon-cyan);
}
.hist-dur { color: var(--text-muted); }
.hist-out { color: var(--neon-teal); }
.hist-err { color: #ff6666; font-size: 10px; width: 100%; }

/* ── Notebook tabs (Radio styled as tabs) ──────────── */
#notebook-tabs .wrap {
    gap: 0 !important;
    flex-wrap: nowrap !important;
    overflow-x: auto;
}
#notebook-tabs label {
    border-radius: 0 !important;
    border: 1px solid #1e1e40 !important;
    border-bottom: 2px solid transparent !important;
    padding: 6px 14px !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    color: var(--text-muted) !important;
    background: transparent !important;
    white-space: nowrap;
}
#notebook-tabs label.selected, #notebook-tabs input:checked + label {
    border-bottom-color: var(--neon-cyan) !important;
    color: var(--neon-cyan) !important;
    background: rgba(0,240,255,0.04) !important;
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
# Generation state (shared across callbacks)
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
            f'<ul style="margin:4px 0 0;padding-left:18px;font-size:11px;'
            f'color:var(--text-muted);list-style:disc">{warn_items}</ul>'
        )

    provider_msg = ""
    if not all(ok for _, ok in checks):
        provider_msg = (
            '<span style="color:var(--text-muted);margin-left:8px">'
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
                infographic_html = f'<iframe srcdoc="{f.read().replace(chr(34), "&quot;").replace(chr(10), "&#10;")}" style="width:100%;height:600px;border:1px solid #1e1e40;border-radius:8px;" sandbox="allow-same-origin"></iframe>'
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
    '<rect x="4" y="6" width="20" height="16" rx="1" stroke="var(--text-muted)" stroke-width="1" fill="none" opacity="0.4"/>'
    '<line x1="9" y1="12" x2="19" y2="12" stroke="var(--text-muted)" stroke-width="0.8" opacity="0.3"/>'
    '<line x1="9" y1="15" x2="16" y2="15" stroke="var(--text-muted)" stroke-width="0.8" opacity="0.3"/>'
    '<line x1="9" y1="18" x2="13" y2="18" stroke="var(--text-muted)" stroke-width="0.8" opacity="0.3"/>'
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
    """Build generation history timeline HTML."""
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
        items.append(
            f'<div class="hist-entry {status_cls}">'
            f'<span class="hist-ts">{ts}</span>'
            f'<span class="hist-badge">{fmt} / {style} / {length}</span>'
            f'<span class="hist-dur">{dur:.0f}s</span>'
            f'<span class="hist-out">{outputs}</span>'
            f'{err_html}'
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


def _post_generate(notebook_id):
    """Called after generation finishes.  Updates log viewer, history, and retry button."""
    global _last_log_text, _last_failed_step
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
              host_voice, cohost_voice, temperature):
    """Re-run the pipeline, skipping to the last failed step."""
    global _last_failed_step
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
    )


def _empty_outputs():
    """9-tuple of empty/cleared outputs."""
    return ("", None, "", "", "", None, None, None, None)


def _on_notebook_switch(notebook_id):
    """Load sources, results, and settings for the selected notebook.

    Returns updates for (23 values):
      sources_display, source_selector, source_content_viewer,
      progress_display, audio_output, extracted_text,
      clean_text, audio_script, infographic_preview, infographic_download,
      png_preview, pptx_download,
      format, length, style, language, outputs_to_generate, output_dir,
      host_voice, cohost_voice, temperature,
      log_viewer, history_display
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
        )

    _notebook_mgr.set_default_notebook_id(notebook_id)
    sources = _notebook_mgr.get_sources(notebook_id)
    settings = _notebook_mgr.get_settings(notebook_id)
    nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)

    sources_html = _build_sources_html(sources)
    src_choices = _source_dropdown_choices(sources)

    results = _load_results_from_dir(nb_dir)
    if results is None:
        results = _empty_outputs()

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
                        host_voice, cohost_voice, temperature):
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


def process_podcast(pdf_file, url_input, config_file, format_type, length, style,
                    language, additional_preference, output_dir, skip_to,
                    outputs_to_generate, notebook_id,
                    host_voice="", cohost_voice="", temperature=0.7,
                    _source_file_override=None):
    """Generator that yields step-by-step progress then a final result tuple."""
    global _last_failed_step, _last_log_text
    _last_failed_step = None

    # Install log capture for this run
    capture = _LogCapture()
    _logging.getLogger("local_notebooklm").addHandler(capture)
    gen_start = time.time()

    # ── Resolve input source ─────────────────────────────────
    # Priority: override > fresh URL > fresh file upload > notebook stored sources
    input_path = _source_file_override
    if input_path is None and url_input and url_input.strip():
        input_path = url_input.strip()
    elif input_path is None and pdf_file is not None:
        input_path = pdf_file.name if hasattr(pdf_file, 'name') else pdf_file
    elif input_path is None and notebook_id:
        sources = _notebook_mgr.get_sources(notebook_id)
        nb_dir = _notebook_mgr.get_notebook_dir(notebook_id)
        for src in sources:
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

    # ── Resolve output directory ─────────────────────────────
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

    # ── Disk space check ─────────────────────────────────
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
        pass  # disk_usage may not work on all platforms

    try:
        # ── Load config ──────────────────────────────────────
        import json as _json
        from pathlib import Path as _Path
        from local_notebooklm.config import validate_config, ConfigValidationError, base_config
        from local_notebooklm.steps.helpers import set_provider
        from local_notebooklm.steps.step1 import step1
        from local_notebooklm.steps.step2 import step2
        from local_notebooklm.steps.step3 import step3
        from local_notebooklm.steps.step4 import step4
        from local_notebooklm.steps.step5 import step5

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

        # ── Apply UI overrides (voice, temperature) ──────────
        if host_voice and str(host_voice).strip():
            config["Host-Speaker-Voice"] = str(host_voice).strip()
        if cohost_voice and str(cohost_voice).strip():
            config["Co-Host-Speaker-1-Voice"] = str(cohost_voice).strip()
        if temperature is not None:
            temp_val = float(temperature)
            for step_key in ["Step1", "Step2", "Step3"]:
                if step_key in config:
                    config[step_key]["temperature"] = temp_val

        # ── Determine outputs & total steps ──────────────────
        want_audio = "Podcast Audio" in outputs_to_generate
        want_html = "Infographic HTML" in outputs_to_generate
        want_png = "Infographic PNG" in outputs_to_generate
        want_pptx = "PPTX Slides" in outputs_to_generate
        want_any_infographic = want_html or want_png or want_pptx

        total_steps = 3
        if want_audio:
            total_steps += 1
        if want_any_infographic:
            total_steps += 1

        selected = ", ".join(outputs_to_generate)
        print(f"Processing with output_dir: {output_dir}")
        print(f"Generating: {selected}")

        # ── Create output directories ────────────────────────
        output_base = _Path(output_dir)
        output_dirs = {f"step{i}": output_base / f"step{i}" for i in range(1, 6)}
        for dp in output_dirs.values():
            dp.mkdir(parents=True, exist_ok=True)

        # ── Set up LLM / TTS clients ────────────────────────
        small_text_client = set_provider(config=config["Small-Text-Model"]["provider"])
        big_text_client = set_provider(config=config["Big-Text-Model"]["provider"])
        tts_client = set_provider(config=config["Text-To-Speech-Model"]["provider"])

        # ── System prompts per step ──────────────────────────
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
        step_start = time.time()

        # ── Step 1: Extract text ─────────────────────────────
        current_step += 1
        eta = _format_eta(step_times, current_step, total_steps)
        yield _empty_result(_build_progress_html(current_step, total_steps, "Extracting text from document...", eta))
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
                yield _empty_result("No output files from Step 1. Cannot skip.")
                return

        # ── Step 2: Generate transcript ──────────────────────
        step_times.append(time.time() - step_start)
        current_step += 1
        eta = _format_eta(step_times, current_step, total_steps)
        yield _empty_result(_build_progress_html(current_step, total_steps, "Generating transcript...", eta))
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
                preference_text=additional_preference if additional_preference else None,
                system_prompt=system_prompts["step2"],
            )
        else:
            step2_files = list(output_dirs["step2"].glob("*.pkl"))
            if step2_files:
                transcript_file = str(sorted(step2_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
            else:
                yield _empty_result("No output files from Step 2. Cannot skip.")
                return

        # ── Step 3: Optimize for TTS ─────────────────────────
        step_times.append(time.time() - step_start)
        current_step += 1
        eta = _format_eta(step_times, current_step, total_steps)
        yield _empty_result(_build_progress_html(current_step, total_steps, "Optimizing for text-to-speech...", eta))
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

        # ── Step 4: Generate audio ───────────────────────────
        step_times.append(time.time() - step_start)
        if want_audio:
            current_step += 1
            eta = _format_eta(step_times, current_step, total_steps)
            yield _empty_result(_build_progress_html(current_step, total_steps, "Generating audio...", eta))
            step_start = time.time()

            if not skip_to or skip_to <= 4:
                step4(
                    client=tts_client,
                    config=config,
                    input_dir=str(output_dirs["step3"]),
                    output_dir=str(output_dirs["step4"]),
                )

        # ── Step 5: Generate infographic ─────────────────────
        if want_audio:
            step_times.append(time.time() - step_start)
        if want_any_infographic:
            current_step += 1
            eta = _format_eta(step_times, current_step, total_steps)
            yield _empty_result(_build_progress_html(current_step, total_steps, "Generating infographic...", eta))
            step_start = time.time()

            if not skip_to or skip_to <= 5:
                try:
                    step5(
                        client=big_text_client,
                        config=config,
                        input_dir=str(output_dirs["step3"]),
                        output_dir=str(output_dirs["step5"]),
                        generate_html=want_html,
                        generate_png=want_png,
                        generate_pptx=want_pptx,
                    )
                except Exception as e:
                    _log.warning("Step 5 (infographic) failed (non-fatal): %s", e)

        # ── Collect results ──────────────────────────────────
        audio_path = None
        if want_audio:
            for subdir in [os.path.join(output_dir, "step4"), output_dir]:
                for ext in ["wav", "mp3", "ogg", "flac", "aac"]:
                    candidate = os.path.join(subdir, f"podcast.{ext}")
                    if os.path.exists(candidate):
                        audio_path = candidate
                        break
                if audio_path:
                    break

        file_contents = {}
        for rel in ["step1/extracted_text.txt", "step1/clean_extracted_text.txt", "step3/podcast_ready_data.txt"]:
            full_path = os.path.join(output_dir, rel)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_contents[rel] = content[:1000] + "..." if len(content) > 1000 else content
                except Exception as e:
                    _log.warning("Failed to read pipeline output %s: %s", rel, e)

        infographic_html = None
        infographic_file = None
        infographic_path = os.path.join(output_dir, "step5", "infographic.html")
        if os.path.exists(infographic_path):
            try:
                with open(infographic_path, 'r', encoding='utf-8') as f:
                    raw = f.read()
                    infographic_html = (
                        f'<iframe srcdoc="{raw.replace(chr(34), "&quot;").replace(chr(10), "&#10;")}"'
                        f' style="width:100%;height:600px;border:1px solid #1e1e40;border-radius:8px;"'
                        f' sandbox="allow-same-origin"></iframe>'
                    )
                infographic_file = infographic_path
            except Exception as e:
                _log.warning("Failed to read infographic HTML: %s", e)

        png_image = None
        png_path = os.path.join(output_dir, "step5", "infographic.png")
        if os.path.exists(png_path):
            png_image = png_path

        pptx_file = None
        pptx_path = os.path.join(output_dir, "step5", "infographic.pptx")
        if os.path.exists(pptx_path):
            pptx_file = pptx_path

        generated = []
        if audio_path:
            generated.append("Audio")
        if infographic_html:
            generated.append("Infographic HTML")
        if png_image:
            generated.append("Infographic PNG")
        if pptx_file:
            generated.append("PPTX")

        gen_label = f"Generated: {', '.join(generated)}" if generated else "Complete"
        status_msg = _build_progress_html(total_steps, total_steps, gen_label, complete=True)

        # Record success in history
        _last_log_text = capture.get_text()
        _logging.getLogger("local_notebooklm").removeHandler(capture)
        if notebook_id:
            from datetime import datetime, timezone
            _notebook_mgr.add_history_entry(notebook_id, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "format": format_type, "length": length, "style": style,
                "language": language,
                "duration_s": round(time.time() - gen_start, 1),
                "status": "success",
                "outputs": generated,
            })

        yield (
            status_msg,
            audio_path,
            file_contents.get("step1/extracted_text.txt", ""),
            file_contents.get("step1/clean_extracted_text.txt", ""),
            file_contents.get("step3/podcast_ready_data.txt", ""),
            infographic_html,
            infographic_file,
            png_image,
            pptx_file,
        )

    except Exception as e:
        import traceback
        # Determine which step failed for retry
        _last_failed_step = current_step
        _last_log_text = capture.get_text()
        _logging.getLogger("local_notebooklm").removeHandler(capture)

        if notebook_id:
            from datetime import datetime, timezone
            _notebook_mgr.add_history_entry(notebook_id, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "format": format_type, "length": length, "style": style,
                "language": language,
                "duration_s": round(time.time() - gen_start, 1),
                "status": "failed",
                "outputs": [],
                "error": str(e)[:200],
            })

        yield _empty_result(
            _build_progress_html(0, 0, f"Step {_last_failed_step or '?'} failed: {e}")
            + f'\n<details><summary>Full traceback</summary><pre>{traceback.format_exc()}</pre></details>'
        )


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

                    # Temperature
                    temperature_slider = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=0.7,
                        step=0.1,
                        label="Creativity",
                        info="Lower = precise, Higher = creative",
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
            log_viewer, history_display,
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
                                  temperature_slider]:
            setting_component.change(
                fn=_on_settings_change,
                inputs=[notebook_selector, format_type, length, style, language,
                        outputs_to_generate, host_voice, cohost_voice,
                        temperature_slider],
                outputs=None,
                show_progress="hidden",
            )

        # ── Wiring — Generate ─────────────────────────────────
        generate_inputs = [
            pdf_file, url_input, config_file, format_type, length, style,
            language, additional_preference, output_dir, skip_to,
            outputs_to_generate, notebook_selector,
            host_voice, cohost_voice, temperature_slider,
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
            fn=None,
            inputs=None,
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

        # ── Wiring — Audio waveform on playback ───────────────
        audio_output.change(
            fn=lambda a: _build_waveform_html(a) if a else "",
            inputs=[audio_output],
            outputs=[waveform_display],
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
