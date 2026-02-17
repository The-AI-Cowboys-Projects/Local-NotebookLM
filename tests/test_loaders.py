"""Tests for local_notebooklm.loaders — all 6 extraction formats + error handling."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from local_notebooklm.loaders import (
    load_input,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_pptx,
    extract_text_from_txt,
    extract_text_from_markdown,
    extract_text_from_url,
    LoaderError,
)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def tmp_txt(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("Hello world from a text file", encoding="utf-8")
    return str(p)


@pytest.fixture
def tmp_md(tmp_path):
    p = tmp_path / "sample.md"
    p.write_text("# Heading\n\nSome **markdown** content", encoding="utf-8")
    return str(p)


@pytest.fixture
def tmp_docx(tmp_path):
    from docx import Document

    p = tmp_path / "sample.docx"
    doc = Document()
    doc.add_paragraph("First paragraph")
    doc.add_paragraph("Second paragraph")
    doc.save(str(p))
    return str(p)


@pytest.fixture
def tmp_pptx(tmp_path):
    from pptx import Presentation

    p = tmp_path / "sample.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Slide Title"
    slide.placeholders[1].text = "Bullet content"
    prs.save(str(p))
    return str(p)


# ── TXT Tests ───────────────────────────────────────────────────────


class TestTxtLoader:
    def test_basic_read(self, tmp_txt):
        text = extract_text_from_txt(tmp_txt)
        assert text == "Hello world from a text file"

    def test_max_chars(self, tmp_txt):
        text = extract_text_from_txt(tmp_txt, max_chars=5)
        assert text == "Hello"

    def test_missing_file(self):
        with pytest.raises(LoaderError, match="File not found"):
            extract_text_from_txt("/nonexistent/path.txt")

    def test_encoding_fallback(self, tmp_path):
        p = tmp_path / "latin.txt"
        p.write_bytes("caf\xe9".encode("latin-1"))
        text = extract_text_from_txt(str(p))
        assert "caf" in text

    def test_via_dispatcher(self, tmp_txt):
        text = load_input(tmp_txt)
        assert "Hello" in text


# ── Markdown Tests ──────────────────────────────────────────────────


class TestMarkdownLoader:
    def test_basic_read(self, tmp_md):
        text = extract_text_from_markdown(tmp_md)
        assert "# Heading" in text
        assert "**markdown**" in text

    def test_max_chars(self, tmp_md):
        text = extract_text_from_markdown(tmp_md, max_chars=10)
        assert len(text) == 10

    def test_missing_file(self):
        with pytest.raises(LoaderError, match="File not found"):
            extract_text_from_markdown("/nonexistent/path.md")

    def test_via_dispatcher(self, tmp_md):
        text = load_input(tmp_md)
        assert "Heading" in text


# ── DOCX Tests ──────────────────────────────────────────────────────


class TestDocxLoader:
    def test_basic_read(self, tmp_docx):
        text = extract_text_from_docx(tmp_docx)
        assert "First paragraph" in text
        assert "Second paragraph" in text

    def test_max_chars(self, tmp_docx):
        text = extract_text_from_docx(tmp_docx, max_chars=10)
        assert len(text) <= 10

    def test_missing_file(self):
        with pytest.raises(LoaderError, match="File not found"):
            extract_text_from_docx("/nonexistent/path.docx")

    def test_via_dispatcher(self, tmp_docx):
        text = load_input(tmp_docx)
        assert "paragraph" in text


# ── PPTX Tests ──────────────────────────────────────────────────────


class TestPptxLoader:
    def test_basic_read(self, tmp_pptx):
        text = extract_text_from_pptx(tmp_pptx)
        assert "Slide Title" in text
        assert "Bullet content" in text

    def test_max_chars(self, tmp_pptx):
        text = extract_text_from_pptx(tmp_pptx, max_chars=8)
        assert len(text) <= 8

    def test_missing_file(self):
        with pytest.raises(LoaderError, match="File not found"):
            extract_text_from_pptx("/nonexistent/path.pptx")

    def test_via_dispatcher(self, tmp_pptx):
        text = load_input(tmp_pptx)
        assert "Slide" in text


# ── PDF Tests ───────────────────────────────────────────────────────


class TestPdfLoader:
    def test_missing_file(self):
        with pytest.raises(LoaderError, match="File not found"):
            extract_text_from_pdf("/nonexistent/path.pdf")

    def test_example_pdf(self):
        pdf = "./examples/MoshiVis.pdf"
        if not os.path.exists(pdf):
            pytest.skip("Example PDF not available")
        text = extract_text_from_pdf(pdf, max_chars=200)
        assert len(text) > 0
        assert len(text) <= 200

    def test_via_dispatcher_extension(self, tmp_path):
        """Dispatcher routes .pdf to PDF loader."""
        p = tmp_path / "fake.pdf"
        p.write_bytes(b"not a real pdf")
        with pytest.raises(LoaderError):
            load_input(str(p))


# ── URL Tests ───────────────────────────────────────────────────────


class TestUrlLoader:
    def test_trafilatura_extraction(self):
        """Mock trafilatura at the function level (no reload needed)."""
        mock_traf = MagicMock()
        mock_traf.fetch_url.return_value = "<html>article</html>"
        mock_traf.extract.return_value = "Extracted article content"

        with patch.dict("local_notebooklm.loaders.__builtins__", {}):
            with patch("local_notebooklm.loaders.extract_text_from_url") as mock_fn:
                mock_fn.return_value = "Extracted article content"
                text = load_input("https://example.com/article")
                assert text == "Extracted article content"

    def test_url_via_dispatcher(self):
        with patch("local_notebooklm.loaders.extract_text_from_url", return_value="url content"):
            text = load_input("https://example.com/article")
            assert text == "url content"

    def test_url_max_chars(self):
        with patch("local_notebooklm.loaders.extract_text_from_url", return_value="x" * 100):
            text = load_input("https://example.com", max_chars=100)
            assert len(text) <= 100


# ── Dispatcher Tests ────────────────────────────────────────────────


class TestDispatcher:
    def test_empty_path(self):
        with pytest.raises(LoaderError, match="No input path"):
            load_input("")

    def test_none_path(self):
        with pytest.raises(LoaderError, match="No input path"):
            load_input(None)

    def test_unsupported_extension(self, tmp_path):
        p = tmp_path / "file.xyz"
        p.write_text("data")
        with pytest.raises(LoaderError, match="Unsupported file type"):
            load_input(str(p))

    def test_http_routes_to_url(self):
        with patch("local_notebooklm.loaders.extract_text_from_url", return_value="ok") as mock:
            load_input("http://example.com")
            mock.assert_called_once()

    def test_https_routes_to_url(self):
        with patch("local_notebooklm.loaders.extract_text_from_url", return_value="ok") as mock:
            load_input("https://example.com")
            mock.assert_called_once()
