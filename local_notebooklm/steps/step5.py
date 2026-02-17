"""Step 5 — Visual Companion Infographic.

Reads the podcast transcript from Step 3, asks the LLM to extract structured
metadata (topics, quotes, speakers, flow), then renders a self-contained HTML
infographic.  Optional PNG export via Playwright.

Step 5 failure is **non-fatal** — the pipeline still returns audio.
"""

import html
import json
import logging
import pickle
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .helpers import generate_text
from .prompts import step5_system_prompt

try:
    from .step5_pptx import render_infographic_pptx, render_video
    _HAS_PPTX_MODULE = True
except ImportError:
    _HAS_PPTX_MODULE = False

logger = logging.getLogger(__name__)


class InfographicError(Exception):
    pass


# ---------------------------------------------------------------------------
# 5a — Load transcript
# ---------------------------------------------------------------------------

def load_transcript_text(input_dir: str) -> str:
    """Load the podcast transcript produced by Step 3.

    Prefers ``podcast_ready_data.txt``; falls back to ``.pkl``.
    """
    input_path = Path(input_dir)

    txt_path = input_path / "podcast_ready_data.txt"
    if txt_path.exists():
        text = txt_path.read_text(encoding="utf-8")
        if text.strip():
            return text

    pkl_path = input_path / "podcast_ready_data.pkl"
    if pkl_path.exists():
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return "\n".join(f"{spk}: {line}" for spk, line in data)
        return str(data)

    raise InfographicError(
        f"No transcript found in {input_dir}. "
        "Expected podcast_ready_data.txt or .pkl"
    )


# ---------------------------------------------------------------------------
# 5b — LLM extraction
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = {"title", "summary", "topics", "key_takeaways",
                  "notable_quotes", "speakers", "conversation_flow"}


def extract_structured_data(
    client: Any,
    config: Dict[str, Any],
    transcript: str,
) -> Dict[str, Any]:
    """Single LLM call → structured JSON with podcast metadata."""

    step_cfg = config.get("Step5", {})
    model = config["Big-Text-Model"]["model"]
    max_tokens = step_cfg.get("max_tokens", 4096)
    temperature = step_cfg.get("temperature", 0.4)

    messages = [
        {"role": "system", "content": step5_system_prompt},
        {"role": "user", "content": transcript},
    ]

    raw = generate_text(
        client=client,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # Strip markdown fences if the model wraps the JSON
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise InfographicError(f"LLM returned invalid JSON: {exc}\n{cleaned[:500]}")

    missing = _REQUIRED_KEYS - set(data.keys())
    if missing:
        raise InfographicError(f"LLM response missing keys: {missing}")

    return data


# ---------------------------------------------------------------------------
# 5c — HTML renderer
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """HTML-escape user-supplied text to prevent XSS."""
    return html.escape(str(text), quote=True)


def render_infographic_html(data: Dict[str, Any]) -> str:
    """Generate a self-contained HTML infographic from structured data."""

    title = _esc(data.get("title", "Podcast Infographic"))
    summary = _esc(data.get("summary", ""))

    # Topics grid
    topics_html = ""
    for t in data.get("topics", []):
        importance = int(t.get("importance", 3))
        pct = min(importance * 20, 100)
        topics_html += f"""
        <div class="topic-card">
            <h3>{_esc(t.get('name', ''))}</h3>
            <p>{_esc(t.get('description', ''))}</p>
            <div class="importance-bar">
                <div class="importance-fill" style="width:{pct}%"></div>
            </div>
            <span class="importance-label">Importance: {importance}/5</span>
        </div>"""

    # Key takeaways
    takeaways_html = ""
    for i, kt in enumerate(data.get("key_takeaways", []), 1):
        takeaways_html += f'<li><span class="num">{i}</span> {_esc(kt)}</li>\n'

    # Notable quotes
    quotes_html = ""
    for q in data.get("notable_quotes", []):
        quotes_html += f"""
        <div class="quote-card">
            <span class="quote-mark">&ldquo;</span>
            <p class="quote-text">{_esc(q.get('quote', ''))}</p>
            <p class="quote-speaker">&mdash; {_esc(q.get('speaker', ''))}</p>
        </div>"""

    # Speakers
    speakers_html = ""
    for s in data.get("speakers", []):
        speakers_html += f"""
        <div class="speaker-badge">
            <div class="speaker-label">{_esc(s.get('label', ''))}</div>
            <div class="speaker-role">{_esc(s.get('role', ''))}</div>
            <div class="speaker-lines">{_esc(str(s.get('line_count', '?')))} turns</div>
        </div>"""

    # Conversation flow timeline
    flow_html = ""
    for entry in data.get("conversation_flow", []):
        flow_html += f"""
        <div class="flow-entry">
            <div class="flow-dot"></div>
            <div class="flow-info">
                <span class="flow-speaker">{_esc(entry.get('speaker', ''))}</span>
                <span class="flow-topic">{_esc(entry.get('topic', ''))}</span>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: #0a0a14;
    color: #e0e0f0;
    line-height: 1.6;
    padding: 2rem;
    max-width: 960px;
    margin: 0 auto;
}}

/* Header */
.header {{
    text-align: center;
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #1e1e40;
}}
.header h1 {{
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #00f0ff, #3bd6c6, #dd368a, #ff00aa);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.75rem;
}}
.header .summary {{
    color: #8888aa;
    font-size: 0.95rem;
    max-width: 700px;
    margin: 0 auto;
}}

/* Section titles */
.section-title {{
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: #00f0ff;
    margin-bottom: 1rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(0, 240, 255, 0.15);
}}

/* Topics grid */
.topics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1rem;
    margin-bottom: 2.5rem;
}}
.topic-card {{
    background: #0f0f1e;
    border: 1px solid #1e1e40;
    border-radius: 8px;
    padding: 1rem;
}}
.topic-card h3 {{
    color: #3bd6c6;
    font-size: 0.95rem;
    margin-bottom: 0.4rem;
}}
.topic-card p {{
    color: #8888aa;
    font-size: 0.85rem;
    margin-bottom: 0.6rem;
}}
.importance-bar {{
    height: 4px;
    background: #1e1e40;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 0.3rem;
}}
.importance-fill {{
    height: 100%;
    background: linear-gradient(90deg, #00f0ff, #ff00aa);
    border-radius: 2px;
}}
.importance-label {{
    font-size: 0.7rem;
    color: #555577;
}}

/* Key takeaways */
.takeaways {{
    margin-bottom: 2.5rem;
    border-left: 3px solid #ff00aa;
    padding-left: 1.2rem;
}}
.takeaways ul {{
    list-style: none;
}}
.takeaways li {{
    padding: 0.5rem 0;
    font-size: 0.9rem;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
}}
.takeaways li .num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    height: 22px;
    border-radius: 50%;
    background: rgba(0, 240, 255, 0.1);
    border: 1px solid #00f0ff;
    color: #00f0ff;
    font-size: 0.7rem;
    font-weight: 700;
    flex-shrink: 0;
}}

/* Quotes */
.quotes {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
    margin-bottom: 2.5rem;
}}
.quote-card {{
    background: #0f0f1e;
    border: 1px solid #1e1e40;
    border-radius: 8px;
    padding: 1.2rem;
    position: relative;
}}
.quote-mark {{
    font-size: 3rem;
    color: rgba(0, 240, 255, 0.2);
    line-height: 1;
    position: absolute;
    top: 0.5rem;
    left: 0.8rem;
}}
.quote-text {{
    font-style: italic;
    color: #e0e0f0;
    font-size: 0.9rem;
    margin-top: 1.5rem;
    margin-bottom: 0.6rem;
}}
.quote-speaker {{
    color: #dd368a;
    font-size: 0.8rem;
    text-align: right;
}}

/* Speakers */
.speakers {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2.5rem;
}}
.speaker-badge {{
    background: #0f0f1e;
    border: 1px solid #1e1e40;
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    text-align: center;
    min-width: 120px;
}}
.speaker-label {{
    color: #00f0ff;
    font-weight: 700;
    font-size: 0.9rem;
}}
.speaker-role {{
    color: #8888aa;
    font-size: 0.78rem;
    margin: 0.2rem 0;
}}
.speaker-lines {{
    color: #3bd6c6;
    font-size: 0.75rem;
}}

/* Conversation flow */
.flow {{
    display: flex;
    align-items: flex-start;
    gap: 0;
    overflow-x: auto;
    padding-bottom: 1rem;
    margin-bottom: 2.5rem;
}}
.flow-entry {{
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 90px;
    position: relative;
    flex-shrink: 0;
}}
.flow-entry:not(:last-child)::after {{
    content: "";
    position: absolute;
    top: 8px;
    left: calc(50% + 8px);
    width: calc(100% - 16px);
    height: 2px;
    background: linear-gradient(90deg, #00f0ff, #ff00aa);
    opacity: 0.4;
}}
.flow-dot {{
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #0a0a14;
    border: 2px solid #00f0ff;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
    z-index: 1;
}}
.flow-info {{
    text-align: center;
}}
.flow-speaker {{
    display: block;
    color: #3bd6c6;
    font-size: 0.7rem;
    font-weight: 700;
}}
.flow-topic {{
    display: block;
    color: #8888aa;
    font-size: 0.68rem;
}}

/* Footer */
.footer {{
    text-align: center;
    padding-top: 1.5rem;
    border-top: 1px solid #1e1e40;
    color: #555577;
    font-size: 0.75rem;
}}

/* Responsive */
@media (max-width: 600px) {{
    body {{ padding: 1rem; }}
    .header h1 {{ font-size: 1.4rem; }}
    .topics-grid {{ grid-template-columns: 1fr; }}
    .quotes {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>{title}</h1>
    <p class="summary">{summary}</p>
</div>

<div class="section-title">// Topics</div>
<div class="topics-grid">{topics_html}
</div>

<div class="section-title">// Key Takeaways</div>
<div class="takeaways">
    <ul>
{takeaways_html}    </ul>
</div>

<div class="section-title">// Notable Quotes</div>
<div class="quotes">{quotes_html}
</div>

<div class="section-title">// Speakers</div>
<div class="speakers">{speakers_html}
</div>

<div class="section-title">// Conversation Flow</div>
<div class="flow">{flow_html}
</div>

<div class="footer">Generated by Local-NotebookLM</div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# 5d — Optional PNG via Playwright
# ---------------------------------------------------------------------------

def render_png(html_path: str, png_path: str) -> Optional[str]:
    """Render the HTML infographic to PNG using Playwright.

    Returns the PNG path on success, or *None* if Playwright is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.info("Playwright not installed — skipping PNG export.")
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.goto(f"file://{html_path}")
            page.wait_for_load_state("networkidle")
            full_height = page.evaluate("document.body.scrollHeight")
            page.set_viewport_size({"width": 1024, "height": full_height})
            page.screenshot(path=png_path, full_page=True)
            browser.close()
        logger.info(f"PNG infographic saved to {png_path}")
        return png_path
    except Exception as exc:
        logger.warning(f"PNG export failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def step5(
    client: Any,
    config: Dict[str, Any],
    input_dir: str,
    output_dir: str,
) -> str:
    """Generate a visual infographic from the podcast transcript.

    Returns the path to the generated HTML infographic.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 5a — Load transcript
    logger.info("Step 5a: Loading transcript...")
    transcript = load_transcript_text(input_dir)

    # 5b — Extract structured data via LLM
    logger.info("Step 5b: Extracting structured data via LLM...")
    data = extract_structured_data(client, config, transcript)

    # Save intermediate JSON
    json_path = output_path / "infographic_data.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Saved structured data to {json_path}")

    # 5c — Render HTML
    logger.info("Step 5c: Rendering infographic HTML...")
    html_content = render_infographic_html(data)
    html_path = output_path / "infographic.html"
    html_path.write_text(html_content, encoding="utf-8")
    logger.info(f"Saved infographic to {html_path}")

    # 5d — Optional PNG
    png_path = output_path / "infographic.png"
    render_png(str(html_path.resolve()), str(png_path))

    # 5e — Optional PPTX
    if _HAS_PPTX_MODULE:
        try:
            pptx_path = output_path / "infographic.pptx"
            pptx_result = render_infographic_pptx(data, str(pptx_path))
            if pptx_result:
                logger.info(f"PPTX infographic saved to {pptx_result}")

                # 5f — Optional video from PPTX
                try:
                    video_path = output_path / "infographic.mp4"
                    render_video(str(pptx_path), str(video_path))
                except Exception as exc:
                    logger.warning(f"Video generation failed: {exc}")
        except Exception as exc:
            logger.warning(f"PPTX generation failed: {exc}")

    return str(html_path)
