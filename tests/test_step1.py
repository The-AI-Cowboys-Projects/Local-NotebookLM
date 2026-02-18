"""Tests for step1 — chunking algorithm and processing pipeline."""

import pytest
from unittest.mock import patch, MagicMock
from local_notebooklm.steps.step1 import (
    create_word_bounded_chunks,
    process_chunk,
    step1,
    DocumentProcessingError,
    ChunkProcessingError,
)


class TestWordBoundedChunks:
    def test_single_chunk(self):
        chunks = create_word_bounded_chunks("hello world", 100)
        assert chunks == ["hello world"]

    def test_splits_on_boundary(self):
        text = "one two three four five six"
        chunks = create_word_bounded_chunks(text, 10)
        # Each chunk should be <= 10 chars
        for chunk in chunks:
            assert len(chunk) <= 10

    def test_preserves_all_words(self):
        words = ["alpha", "bravo", "charlie", "delta", "echo"]
        text = " ".join(words)
        chunks = create_word_bounded_chunks(text, 15)
        reassembled = " ".join(chunks)
        for w in words:
            assert w in reassembled

    def test_empty_text(self):
        chunks = create_word_bounded_chunks("", 100)
        assert chunks == []

    def test_single_word_exceeds_size(self):
        chunks = create_word_bounded_chunks("superlongword", 5)
        # The word is bigger than chunk_size, but since there's no prior chunk
        # it gets added to current_chunk anyway
        assert len(chunks) == 1
        assert chunks[0] == "superlongword"

    def test_chunk_count_grows_with_text(self):
        short = create_word_bounded_chunks("a b c", 100)
        long = create_word_bounded_chunks("a " * 200, 10)
        assert len(long) > len(short)

    def test_no_empty_chunks(self):
        text = "word " * 50
        chunks = create_word_bounded_chunks(text.strip(), 20)
        for chunk in chunks:
            assert chunk.strip() != ""


class TestProcessChunk:
    @patch("local_notebooklm.steps.step1.generate_text")
    def test_returns_llm_output(self, mock_gen):
        mock_gen.return_value = "cleaned text"
        result = process_chunk(
            client=MagicMock(),
            text_chunk="raw text",
            system_prompt=None,
            chunk_num=0,
            model_name="test-model",
            max_tokens=512,
            temperature=0.7,
            format_type="podcast",
        )
        assert result == "cleaned text"
        mock_gen.assert_called_once()

    @patch("local_notebooklm.steps.step1.generate_text")
    def test_custom_system_prompt(self, mock_gen):
        mock_gen.return_value = "ok"
        process_chunk(
            client=MagicMock(),
            text_chunk="raw",
            system_prompt="custom prompt",
            chunk_num=0,
            model_name="m",
            max_tokens=100,
            temperature=0.5,
            format_type="podcast",
        )
        call_args = mock_gen.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["content"] == "custom prompt"

    @patch("local_notebooklm.steps.step1.generate_text", side_effect=RuntimeError("API down"))
    def test_wraps_error(self, mock_gen):
        with pytest.raises(ChunkProcessingError, match="Failed to process chunk"):
            process_chunk(
                client=MagicMock(),
                text_chunk="x",
                system_prompt=None,
                chunk_num=3,
                model_name="m",
                max_tokens=100,
                temperature=0.5,
                format_type="podcast",
            )


class TestStep1Integration:
    @patch("local_notebooklm.steps.step1.generate_text")
    @patch("local_notebooklm.steps.step1.load_input")
    def test_end_to_end(self, mock_load, mock_gen, tmp_path):
        mock_load.return_value = "word " * 50
        mock_gen.return_value = "cleaned"

        config = {
            "Step1": {"max_chars": 10000, "chunk_size": 100, "max_tokens": 512, "temperature": 0.7},
            "Small-Text-Model": {"model": "test"},
        }
        result = step1(
            input_path="dummy.pdf",
            client=MagicMock(),
            config=config,
            output_dir=str(tmp_path),
            format_type="podcast",
        )
        assert "clean_extracted_text.txt" in result
        assert (tmp_path / "extracted_text.txt").exists()

    @patch("local_notebooklm.steps.step1.load_input", return_value="")
    def test_empty_extraction_raises(self, mock_load, tmp_path):
        config = {
            "Step1": {"max_chars": 10000, "chunk_size": 100, "max_tokens": 512, "temperature": 0.7},
            "Small-Text-Model": {"model": "test"},
        }
        with pytest.raises(DocumentProcessingError, match="No text extracted"):
            step1(
                input_path="dummy.pdf",
                client=MagicMock(),
                config=config,
                output_dir=str(tmp_path),
            )

    @patch("local_notebooklm.steps.step1.generate_text")
    @patch("local_notebooklm.steps.step1.load_input")
    def test_parallel_preserves_order(self, mock_load, mock_gen, tmp_path):
        """With multiple chunks, output is written in original order."""
        # 3 chunks of distinct content
        mock_load.return_value = "aaa " * 40 + "bbb " * 40 + "ccc " * 40

        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            chunk = kwargs.get("messages", [{}])[0].get("content", "")
            if "aaa" in chunk:
                return "CLEANED_A"
            elif "bbb" in chunk:
                return "CLEANED_B"
            else:
                return "CLEANED_C"

        mock_gen.side_effect = side_effect

        config = {
            "Step1": {"max_chars": 10000, "chunk_size": 60, "max_tokens": 512, "temperature": 0.7},
            "Small-Text-Model": {"model": "test"},
        }
        result_path = step1(
            input_path="dummy.txt",
            client=MagicMock(),
            config=config,
            output_dir=str(tmp_path),
            format_type="podcast",
        )
        content = open(result_path).read()
        # All 3 cleaned chunks should appear
        assert "CLEANED_A" in content
        assert "CLEANED_B" in content
        assert "CLEANED_C" in content
        # Order matters: A before B before C
        assert content.index("CLEANED_A") < content.index("CLEANED_B")
        assert content.index("CLEANED_B") < content.index("CLEANED_C")
