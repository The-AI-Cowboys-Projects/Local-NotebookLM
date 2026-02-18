"""Tests for step3 — transcript rewriting and TTS-ready formatting."""

import pickle
import pytest
from unittest.mock import MagicMock, patch

from local_notebooklm.steps.step3 import (
    FileReadError,
    TranscriptError,
    TranscriptGenerationError,
    generate_rewritten_transcript,
    generate_rewritten_transcript_with_overlap,
    read_pickle_file,
    step3,
    validate_transcript_format,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

VALID_TRANSCRIPT = "[('Speaker 1', 'Hello listeners'), ('Speaker 2', 'Welcome back')]"

VALID_TRANSCRIPT_3_SPEAKERS = (
    "[('Speaker 1', 'Hello'), ('Speaker 2', 'Hi'), ('Speaker 3', 'Hey')]"
)


def _make_config():
    return {
        "Big-Text-Model": {"model": "test-model"},
        "Step1": {"temperature": 0.7},
        "Step3": {
            "max_tokens": 4096,
            "chunk_size": 8000,
            "overlap_percent": 10,
        },
    }


def _write_pkl(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)


# ---------------------------------------------------------------------------
# TestReadPickleFile
# ---------------------------------------------------------------------------

class TestReadPickleFile:
    def test_reads_string_pickle(self, tmp_path):
        p = tmp_path / "data.pkl"
        _write_pkl(p, "Hello from pickle")
        assert read_pickle_file(str(p)) == "Hello from pickle"

    def test_reads_list_pickle(self, tmp_path):
        p = tmp_path / "data.pkl"
        data = [("Speaker 1", "Hello"), ("Speaker 2", "Hi")]
        _write_pkl(p, data)
        result = read_pickle_file(str(p))
        assert isinstance(result, list)
        assert result[0] == ("Speaker 1", "Hello")

    def test_file_not_found(self):
        with pytest.raises(FileReadError, match="not found"):
            read_pickle_file("/nonexistent/file.pkl")

    def test_corrupt_pickle(self, tmp_path):
        p = tmp_path / "bad.pkl"
        p.write_bytes(b"not a valid pickle at all")
        with pytest.raises(FileReadError, match="Failed to read"):
            read_pickle_file(str(p))


# ---------------------------------------------------------------------------
# TestValidateTranscriptFormat
# ---------------------------------------------------------------------------

class TestValidateTranscriptFormat:
    def test_valid_two_speaker(self):
        assert validate_transcript_format(VALID_TRANSCRIPT) is True

    def test_valid_three_speaker(self):
        assert validate_transcript_format(VALID_TRANSCRIPT_3_SPEAKERS) is True

    def test_single_entry(self):
        assert validate_transcript_format("[('Speaker 1', 'Solo')]") is True

    def test_empty_list(self):
        assert validate_transcript_format("[]") is True

    def test_not_a_list(self):
        assert validate_transcript_format("'just a string'") is False

    def test_dict_instead_of_list(self):
        assert validate_transcript_format("{'key': 'value'}") is False

    def test_tuples_wrong_length(self):
        assert validate_transcript_format("[('Speaker 1',)]") is False

    def test_triple_tuple(self):
        assert validate_transcript_format("[('Speaker 1', 'text', 'extra')]") is False

    def test_non_string_speaker(self):
        assert validate_transcript_format("[(1, 'text')]") is False

    def test_non_string_text(self):
        assert validate_transcript_format("[('Speaker 1', 123)]") is False

    def test_invalid_syntax(self):
        assert validate_transcript_format("this is not python") is False

    def test_nested_quotes(self):
        transcript = """[('Speaker 1', "He said \\"wow\\" to me"), ('Speaker 2', 'Right')]"""
        # May or may not parse depending on escaping — should not crash
        result = validate_transcript_format(transcript)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# TestGenerateRewrittenTranscript
# ---------------------------------------------------------------------------

class TestGenerateRewrittenTranscript:
    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_returns_llm_output(self, mock_gen, mock_wait):
        mock_gen.return_value = VALID_TRANSCRIPT

        result = generate_rewritten_transcript(
            client=MagicMock(),
            model_name="test-model",
            input_text="raw input",
            system_prompt=None,
            max_tokens=4096,
            temperature=0.7,
            format_type="podcast",
            language="english",
        )

        assert result == VALID_TRANSCRIPT
        mock_gen.assert_called_once()

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_custom_system_prompt(self, mock_gen, mock_wait):
        mock_gen.return_value = VALID_TRANSCRIPT

        generate_rewritten_transcript(
            client=MagicMock(),
            model_name="test-model",
            input_text="raw input",
            system_prompt="My custom prompt",
            max_tokens=4096,
            temperature=0.7,
            format_type="podcast",
            language="english",
        )

        call_args = mock_gen.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "My custom prompt" in messages[0]["content"]

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text", side_effect=RuntimeError("API error"))
    def test_llm_failure_raises(self, mock_gen, mock_wait):
        with pytest.raises(TranscriptGenerationError, match="Failed to generate"):
            generate_rewritten_transcript(
                client=MagicMock(),
                model_name="test-model",
                input_text="input",
                system_prompt=None,
                max_tokens=4096,
                temperature=0.7,
                format_type="podcast",
                language="english",
            )


# ---------------------------------------------------------------------------
# TestGenerateRewrittenTranscriptWithOverlap
# ---------------------------------------------------------------------------

class TestGenerateRewrittenTranscriptWithOverlap:
    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_single_chunk_no_split(self, mock_gen, mock_wait):
        """Short input should produce a single chunk."""
        mock_gen.return_value = VALID_TRANSCRIPT

        result = generate_rewritten_transcript_with_overlap(
            client=MagicMock(),
            model_name="test-model",
            input_text="Short text",
            max_tokens=4096,
            temperature=0.7,
            format_type="podcast",
            system_prompt=None,
            language="english",
            chunk_size=8000,
            overlap_percent=10,
        )

        assert mock_gen.call_count == 1
        assert "Speaker 1" in result

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_multiple_chunks(self, mock_gen, mock_wait):
        """Long input should be split into multiple chunks."""
        mock_gen.return_value = VALID_TRANSCRIPT

        long_text = "X" * 500
        result = generate_rewritten_transcript_with_overlap(
            client=MagicMock(),
            model_name="test-model",
            input_text=long_text,
            max_tokens=4096,
            temperature=0.7,
            format_type="podcast",
            system_prompt=None,
            language="english",
            chunk_size=100,
            overlap_percent=20,
        )

        assert mock_gen.call_count > 1
        assert "Speaker 1" in result

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_goodbye_filtering_non_final_chunks(self, mock_gen, mock_wait):
        """Goodbye phrases should be filtered from non-final chunks."""
        # First chunk returns text with goodbye, second is final chunk
        goodbye_transcript = "[('Speaker 1', 'Great discussion, goodbye everyone'), ('Speaker 2', 'Normal text')]"
        normal_transcript = "[('Speaker 1', 'Final thoughts'), ('Speaker 2', 'Bye for now')]"
        # Use only 2 chunks: chunk_size=200 with 250 chars + 10% overlap
        mock_gen.side_effect = [goodbye_transcript, normal_transcript]

        long_text = "Y" * 250
        result = generate_rewritten_transcript_with_overlap(
            client=MagicMock(),
            model_name="test-model",
            input_text=long_text,
            max_tokens=4096,
            temperature=0.7,
            format_type="podcast",
            system_prompt=None,
            language="english",
            chunk_size=200,
            overlap_percent=10,
        )

        # The goodbye should be replaced with continuation prompt
        assert "let's continue our discussion" in result

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_parse_failure_triggers_fix_attempt(self, mock_gen, mock_wait):
        """If initial parse fails, should attempt LLM fix."""
        # First call returns unparseable text, second returns valid format
        mock_gen.side_effect = ["not valid python", VALID_TRANSCRIPT]

        result = generate_rewritten_transcript_with_overlap(
            client=MagicMock(),
            model_name="test-model",
            input_text="short",
            max_tokens=4096,
            temperature=0.7,
            format_type="podcast",
            system_prompt=None,
            language="english",
            chunk_size=8000,
            overlap_percent=10,
        )

        assert mock_gen.call_count == 2  # original + fix attempt
        assert "Speaker 1" in result

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_parse_failure_both_attempts_raises(self, mock_gen, mock_wait):
        """If both parse attempts fail, should raise TranscriptGenerationError."""
        mock_gen.side_effect = ["invalid python", "still invalid python"]

        with pytest.raises(TranscriptGenerationError, match="Failed"):
            generate_rewritten_transcript_with_overlap(
                client=MagicMock(),
                model_name="test-model",
                input_text="short",
                max_tokens=4096,
                temperature=0.7,
                format_type="podcast",
                system_prompt=None,
                language="english",
                chunk_size=8000,
                overlap_percent=10,
            )


# ---------------------------------------------------------------------------
# TestStep3Integration
# ---------------------------------------------------------------------------

class TestStep3Integration:
    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_full_pipeline_valid_format(self, mock_gen, mock_wait, tmp_path):
        """Valid transcript format should be saved directly."""
        mock_gen.return_value = VALID_TRANSCRIPT

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "Speaker 1: Hello\nSpeaker 2: Hi")
        output_dir = tmp_path / "step3_output"

        result = step3(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_pkl),
            output_dir=str(output_dir),
        )

        input_path, output_path = result

        # Verify pkl output
        pkl_path = output_dir / "podcast_ready_data.pkl"
        assert pkl_path.exists()
        with open(pkl_path, "rb") as f:
            saved = pickle.load(f)
        assert "Speaker 1" in saved

        # Verify txt output
        txt_path = output_dir / "podcast_ready_data.txt"
        assert txt_path.exists()
        assert "Speaker 1" in txt_path.read_text()

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_invalid_format_triggers_fix(self, mock_gen, mock_wait, tmp_path):
        """Invalid transcript format should trigger a fix attempt."""
        # First call returns bad format, second returns valid
        mock_gen.side_effect = [
            "Speaker 1: Hello\nSpeaker 2: Hi",  # not tuple format
            VALID_TRANSCRIPT,  # fix attempt succeeds
        ]

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "raw input text")
        output_dir = tmp_path / "step3_output"

        result = step3(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_pkl),
            output_dir=str(output_dir),
        )

        assert mock_gen.call_count == 2  # original + fix
        txt = (output_dir / "podcast_ready_data.txt").read_text()
        assert "Speaker 1" in txt

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_fix_also_fails_raises(self, mock_gen, mock_wait, tmp_path):
        """If fix attempt also produces invalid format, should raise."""
        mock_gen.side_effect = [
            "not tuple format",
            "still not tuple format",
        ]

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "raw text")
        output_dir = tmp_path / "step3_output"

        with pytest.raises(TranscriptGenerationError):
            step3(
                client=MagicMock(),
                config=_make_config(),
                input_file=str(input_pkl),
                output_dir=str(output_dir),
            )

    def test_missing_input_file_raises(self, tmp_path):
        with pytest.raises(FileReadError, match="not found"):
            step3(
                client=MagicMock(),
                config=_make_config(),
                input_file="/nonexistent/data.pkl",
                output_dir=str(tmp_path / "out"),
            )

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_output_dir_created(self, mock_gen, mock_wait, tmp_path):
        mock_gen.return_value = VALID_TRANSCRIPT

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "input")
        output_dir = tmp_path / "nested" / "deep" / "output"

        step3(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_pkl),
            output_dir=str(output_dir),
        )

        assert output_dir.exists()
        assert (output_dir / "podcast_ready_data.pkl").exists()

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_large_input_uses_overlap_path(self, mock_gen, mock_wait, tmp_path):
        """Input exceeding chunk_size should use the overlap chunking path."""
        mock_gen.return_value = VALID_TRANSCRIPT

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "X" * 10000)  # exceeds default 8000 chunk_size
        output_dir = tmp_path / "step3_output"

        step3(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_pkl),
            output_dir=str(output_dir),
        )

        # With overlap, at least 2 LLM calls should happen
        assert mock_gen.call_count >= 2

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_language_parameter(self, mock_gen, mock_wait, tmp_path):
        """Language parameter should be passed to system prompt generation."""
        mock_gen.return_value = VALID_TRANSCRIPT

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "some text")
        output_dir = tmp_path / "step3_output"

        step3(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_pkl),
            output_dir=str(output_dir),
            language="spanish",
        )

        call_args = mock_gen.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "spanish" in messages[0]["content"].lower()

    @patch("local_notebooklm.steps.step3.wait_for_next_step")
    @patch("local_notebooklm.steps.step3.generate_text")
    def test_format_type_podcast(self, mock_gen, mock_wait, tmp_path):
        """Default format_type 'podcast' should appear in system prompt."""
        mock_gen.return_value = VALID_TRANSCRIPT

        input_pkl = tmp_path / "data.pkl"
        _write_pkl(input_pkl, "some text")

        step3(
            client=MagicMock(),
            config=_make_config(),
            input_file=str(input_pkl),
            output_dir=str(tmp_path / "out"),
            format_type="podcast",
        )

        call_args = mock_gen.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "podcast" in messages[0]["content"].lower()
