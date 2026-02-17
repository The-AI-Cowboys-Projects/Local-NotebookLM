"""Multi-format document loaders for Local-NotebookLM.

Supports PDF, DOCX, PPTX, TXT, Markdown, and web URLs.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class LoaderError(Exception):
    pass


def extract_text_from_pdf(file_path: str, max_chars: int = 100000) -> str:
    import PyPDF2

    if not os.path.exists(file_path):
        raise LoaderError(f"File not found: {file_path}")

    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            logger.info(f"Processing PDF with {num_pages} pages")

            parts = []
            total = 0
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if total + len(text) > max_chars:
                    parts.append(text[: max_chars - total])
                    logger.info(f"Reached {max_chars} char limit at page {i + 1}")
                    break
                parts.append(text)
                total += len(text)

            result = "\n".join(parts)
            logger.info(f"PDF extraction complete. {len(result)} chars")
            return result
    except LoaderError:
        raise
    except Exception as e:
        raise LoaderError(f"Failed to extract text from PDF: {e}")


def extract_text_from_docx(file_path: str, max_chars: int = 100000) -> str:
    from docx import Document

    if not os.path.exists(file_path):
        raise LoaderError(f"File not found: {file_path}")

    try:
        doc = Document(file_path)
        parts = []
        total = 0
        for para in doc.paragraphs:
            text = para.text
            if not text:
                continue
            if total + len(text) + 1 > max_chars:
                parts.append(text[: max_chars - total])
                break
            parts.append(text)
            total += len(text) + 1

        result = "\n".join(parts)
        logger.info(f"DOCX extraction complete. {len(result)} chars")
        return result
    except LoaderError:
        raise
    except Exception as e:
        raise LoaderError(f"Failed to extract text from DOCX: {e}")


def extract_text_from_pptx(file_path: str, max_chars: int = 100000) -> str:
    from pptx import Presentation

    if not os.path.exists(file_path):
        raise LoaderError(f"File not found: {file_path}")

    try:
        prs = Presentation(file_path)
        parts = []
        total = 0
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if not text:
                        continue
                    if total + len(text) + 1 > max_chars:
                        parts.append(text[: max_chars - total])
                        result = "\n".join(parts)
                        logger.info(f"PPTX extraction complete. {len(result)} chars")
                        return result
                    parts.append(text)
                    total += len(text) + 1

        result = "\n".join(parts)
        logger.info(f"PPTX extraction complete. {len(result)} chars")
        return result
    except LoaderError:
        raise
    except Exception as e:
        raise LoaderError(f"Failed to extract text from PPTX: {e}")


def extract_text_from_txt(file_path: str, max_chars: int = 100000) -> str:
    if not os.path.exists(file_path):
        raise LoaderError(f"File not found: {file_path}")

    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                text = f.read(max_chars)
            logger.info(f"TXT extraction complete ({encoding}). {len(text)} chars")
            return text
        except UnicodeDecodeError:
            continue

    raise LoaderError(f"Could not decode {file_path} with any supported encoding")


def extract_text_from_markdown(file_path: str, max_chars: int = 100000) -> str:
    if not os.path.exists(file_path):
        raise LoaderError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read(max_chars)
        logger.info(f"Markdown extraction complete. {len(text)} chars")
        return text
    except Exception as e:
        raise LoaderError(f"Failed to read Markdown file: {e}")


def extract_text_from_url(url: str, max_chars: int = 100000) -> str:
    # Try trafilatura first (best article extraction)
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                text = text[:max_chars]
                logger.info(f"URL extraction (trafilatura) complete. {len(text)} chars")
                return text
    except Exception as e:
        logger.warning(f"trafilatura failed, falling back to bs4: {e}")

    # Fallback to requests + BeautifulSoup
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=30, headers={"User-Agent": "Local-NotebookLM/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = text[:max_chars]
        logger.info(f"URL extraction (bs4) complete. {len(text)} chars")
        return text
    except Exception as e:
        raise LoaderError(f"Failed to extract text from URL: {e}")


# Extension-to-loader mapping
_LOADERS = {
    ".pdf": extract_text_from_pdf,
    ".docx": extract_text_from_docx,
    ".pptx": extract_text_from_pptx,
    ".txt": extract_text_from_txt,
    ".md": extract_text_from_markdown,
}


def load_input(input_path: str, max_chars: int = 100000) -> str:
    """Dispatch to the correct loader based on file extension or URL prefix."""
    if not input_path:
        raise LoaderError("No input path provided")

    # URL detection
    if input_path.startswith(("http://", "https://")):
        return extract_text_from_url(input_path, max_chars)

    # File-based detection
    ext = Path(input_path).suffix.lower()
    loader = _LOADERS.get(ext)
    if loader is None:
        supported = ", ".join(sorted(_LOADERS.keys()))
        raise LoaderError(
            f"Unsupported file type '{ext}'. Supported: {supported} and URLs (http/https)"
        )

    return loader(input_path, max_chars)
