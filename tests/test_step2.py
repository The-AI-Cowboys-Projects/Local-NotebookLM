"""Tests for step2 — transcript generation from cleaned text."""

import pickle
import pytest
from unittest.mock import MagicMock, patch, call

from local_notebooklm.steps.step2 import (
    FileReadError,
    TranscriptError,
    TranscriptGenerationError,
    generate_transcript,
    read_input_file,
    step2,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_config():
    return {
        "Big-Text-Model": {"model": "test-model"},
        "Step2": {
            "max_tokens": 4096,
            "temperature": 0.7,
            "chunk_token_limit": 2000,
            "overlap_percent": 10,
        },
    }


# ---------------------------------------------------------------------------
# TestReadInputFile
# ---------------------------------------------------------------------------

class TestReadInputFile:
    def test_reads_utf8(self, tmp_path):
        p = tmp_path / "input.txt"
        p.write_text("Hello world", encoding="utf-8")
        assert read_input_file(str(p)) == "Hello world"

    def test_reads_utf8_with_bom(self, tmp_path):
        p = tmp_path / "bom.txt"
        p.write_bytes(b"\xef\xbb\xbfHello BOM")
        result = read_input_file(str(p))
        assert "Hello BOM" in result

    def test_falls_back_to_latin1(self, tmp_path):
        p = tmp_path / "latin.txt"
        p.write_bytes("caf\xe9 latt\xe9".encode("latin-1"))
        result = read_input_file(str(p))
        assert "caf" in result

    def test_file_not_found(self):
        with pytest.raises(FileReadError, match="not found"):
            read_input_file("/nonexistent/file.txt")

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("", encoding="utf-8")
        assert read_input_file(str(p)) == ""

    def test_multiline_content(self, tmp_path):
        p = tmp_path / "multi.txt"
        p.write_text("line1\nline2\nline3", encoding="utf-8")
        result = read_input_file(str(p))
        assert "line1" in result
        assert "line3" in result


# ---------------------------------------------------------------------------
# TestGenerateTranscript
# ---------------------------------------------------------------------------

class TestGenerateTranscript:
    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    def test_short_input_single_call(self, mock_gen, mock_wait):
        """Short input (under chunk limit) should use a single LLM call."""
        mock_gen.return_value = "Speaker 1: Hello\nSpeaker 2: Hi there"

        result = generate_transcript(
            client=MagicMock(),
            model_name="test-model",
            input_text="Short text",
            length="medium",
            style="normal",
            format_type="podcast",
            preference_text="nothing",
            system_prompt=None,
            max_tokens=4096,
            temperature=0.7,
            chunk_token_limit=2000,
            overlap_percent=10,
        )

        assert "Speaker 1" in result
        assert mock_gen.call_count == 1

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    def test_long_input_chunked(self, mock_gen, mock_wait):
        """Long input exceeding chunk limit should be split into chunks."""
        mock_gen.return_value = "Speaker 1: Chunk output"

        # chunk_token_limit=10 means char limit ~35, so 200 chars forces chunking
        long_text = "A" * 200
        result = generate_transcript(
            client=MagicMock(),
            model_name="test-model",
            input_text=long_text,
            length="medium",
            style="normal",
            format_type="podcast",
            preference_text="nothing",
            system_prompt=None,
            max_tokens=4096,
            temperature=0.7,
            chunk_token_limit=10,
            overlap_percent=10,
        )

        assert mock_gen.call_count > 1
        assert "Speaker 1" in result

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    def test_custom_system_prompt(self, mock_gen, mock_wait):
        """Custom system prompt should be passed through directly."""
        mock_gen.return_value = "Custom output"

        result = generate_transcript(
            client=MagicMock(),
            model_name="test-model",
            input_text="Some text",
            length="medium",
            style="normal",
            format_type="podcast",
            preference_text="nothing",
            system_prompt="My custom prompt",
            max_tokens=4096,
            temperature=0.7,
            chunk_token_limit=2000,
            overlap_percent=10,
        )

        assert result == "Custom output"
        # Verify the custom prompt was used in the messages
        call_args = mock_gen.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert messages[0]["content"] == "My custom prompt"

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text", side_effect=RuntimeError("API down"))
    def test_llm_failure_raises(self, mock_gen, mock_wait):
        with pytest.raises(TranscriptGenerationError, match="Failed to generate"):
            generate_transcript(
                client=MagicMock(),
                model_name="test-model",
                input_text="text",
                length="medium",
                style="normal",
                format_type="podcast",
                preference_text="nothing",
                system_prompt=None,
                max_tokens=4096,
                temperature=0.7,
                chunk_token_limit=2000,
                overlap_percent=10,
            )

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    @patch("local_notebooklm.steps.step2.time.sleep")
    def test_chunked_output_concatenated(self, mock_sleep, mock_gen, mock_wait):
        """Chunked output should be joined with newlines."""
        # Use a lambda to return distinct values per call
        call_count = {"n": 0}
        def _side_effect(**kwargs):
            call_count["n"] += 1
            return f"Chunk {call_count['n']}"
        mock_gen.side_effect = _side_effect

        long_text = "B" * 500
        result = generate_transcript(
            client=MagicMock(),
            model_name="test-model",
            input_text=long_text,
            length="medium",
            style="normal",
            format_type="podcast",
            preference_text="nothing",
            system_prompt=None,
            max_tokens=4096,
            temperature=0.7,
            chunk_token_limit=10,
            overlap_percent=10,
        )

        assert "Chunk 1" in result
        assert "Chunk 2" in result
        assert mock_gen.call_count > 2


# ---------------------------------------------------------------------------
# TestStep2Integration
# ---------------------------------------------------------------------------

class TestStep2Integration:
    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    def test_full_pipeline(self, mock_gen, mock_wait, tmp_path):
        mock_gen.return_value = "Speaker 1: Welcome\nSpeaker 2: Thanks"

        input_file = tmp_path / "input.txt"
        input_file.write_text("Raw content for processing", encoding="utf-8")
        output_dir = tmp_path / "step2_output"

        result = step2(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_file),
            output_dir=str(output_dir),
        )

        input_path, output_path = result
        assert str(input_file) == input_path
        assert output_path.endswith(".pkl")

        # Verify pkl file
        assert (output_dir / "data.pkl").exists()
        with open(output_dir / "data.pkl", "rb") as f:
            saved = pickle.load(f)
        assert "Speaker 1" in saved

        # Verify txt file
        assert (output_dir / "data.txt").exists()
        txt = (output_dir / "data.txt").read_text()
        assert "Speaker 1" in txt

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    def test_output_dir_created(self, mock_gen, mock_wait, tmp_path):
        """Output directory should be created if it doesn't exist."""
        mock_gen.return_value = "output"

        input_file = tmp_path / "input.txt"
        input_file.write_text("content", encoding="utf-8")
        output_dir = tmp_path / "nested" / "deep" / "output"

        step2(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_file),
            output_dir=str(output_dir),
        )

        assert output_dir.exists()
        assert (output_dir / "data.pkl").exists()

    def test_missing_input_file_raises(self, tmp_path):
        with pytest.raises(FileReadError, match="not found"):
            step2(
                client=MagicMock(),
                config=_make_config(),
                input_file="/nonexistent/file.txt",
                output_dir=str(tmp_path / "out"),
            )

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text")
    def test_format_type_passed_through(self, mock_gen, mock_wait, tmp_path):
        """Custom format_type should be used in system prompt generation."""
        mock_gen.return_value = "narration output"

        input_file = tmp_path / "input.txt"
        input_file.write_text("content", encoding="utf-8")

        step2(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_file),
            output_dir=str(tmp_path / "out"),
            format_type="narration",
            length="short",
            style="professional",
        )

        mock_gen.assert_called_once()

    @patch("local_notebooklm.steps.step2.wait_for_next_step")
    @patch("local_notebooklm.steps.step2.generate_text", side_effect=RuntimeError("fail"))
    def test_llm_error_wraps_as_transcript_error(self, mock_gen, mock_wait, tmp_path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("content", encoding="utf-8")

        with pytest.raises(TranscriptGenerationError):
            step2(
                client=MagicMock(),
                config=_make_config(),
                input_file=str(input_file),
                output_dir=str(tmp_path / "out"),
            )
