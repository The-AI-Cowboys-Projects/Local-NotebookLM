"""Tests for helpers — retry logic, response validation, provider routing."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestGenerateTextRetry:
    """Test retry + validation behavior in generate_text()."""

    @patch("local_notebooklm.steps.helpers._call_llm")
    def test_success_first_try(self, mock_call):
        from local_notebooklm.steps.helpers import generate_text

        mock_call.return_value = "good response"
        result = generate_text(
            client=MagicMock(),
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result == "good response"
        assert mock_call.call_count == 1

    @patch("local_notebooklm.steps.helpers.time.sleep")
    @patch("local_notebooklm.steps.helpers._call_llm")
    def test_retries_on_failure(self, mock_call, mock_sleep):
        from local_notebooklm.steps.helpers import generate_text

        mock_call.side_effect = [ConnectionError("timeout"), "recovered"]
        result = generate_text(
            client=MagicMock(),
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result == "recovered"
        assert mock_call.call_count == 2
        mock_sleep.assert_called_once()  # slept once between attempts

    @patch("local_notebooklm.steps.helpers.time.sleep")
    @patch("local_notebooklm.steps.helpers._call_llm")
    def test_fails_after_max_retries(self, mock_call, mock_sleep):
        from local_notebooklm.steps.helpers import generate_text

        mock_call.side_effect = RuntimeError("always fails")
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            generate_text(
                client=MagicMock(),
                messages=[{"role": "user", "content": "hi"}],
            )
        assert mock_call.call_count == 3

    @patch("local_notebooklm.steps.helpers.time.sleep")
    @patch("local_notebooklm.steps.helpers._call_llm")
    def test_empty_response_triggers_retry(self, mock_call, mock_sleep):
        from local_notebooklm.steps.helpers import generate_text

        mock_call.side_effect = ["", "   ", "actual content"]
        result = generate_text(
            client=MagicMock(),
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result == "actual content"
        assert mock_call.call_count == 3

    @patch("local_notebooklm.steps.helpers.time.sleep")
    @patch("local_notebooklm.steps.helpers._call_llm")
    def test_all_empty_raises(self, mock_call, mock_sleep):
        from local_notebooklm.steps.helpers import generate_text

        mock_call.return_value = ""
        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            generate_text(
                client=MagicMock(),
                messages=[{"role": "user", "content": "hi"}],
            )

    def test_no_client_raises(self):
        from local_notebooklm.steps.helpers import generate_text

        with pytest.raises(ValueError, match="Client is required"):
            generate_text(client=None, messages=[{"role": "user", "content": "hi"}])

    def test_no_messages_raises(self):
        from local_notebooklm.steps.helpers import generate_text

        with pytest.raises(ValueError, match="Messages are required"):
            generate_text(client=MagicMock(), messages=None)

    def test_empty_messages_raises(self):
        from local_notebooklm.steps.helpers import generate_text

        with pytest.raises(ValueError, match="Messages are required"):
            generate_text(client=MagicMock(), messages=[])


class TestGenerateSpeechRetry:
    @patch("local_notebooklm.steps.helpers.time.sleep")
    def test_retries_on_tts_failure(self, mock_sleep):
        from local_notebooklm.steps.helpers import generate_speech

        mock_client = MagicMock()
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_client.audio.speech.with_streaming_response.create.side_effect = [
            ConnectionError("net error"),
            mock_response,
        ]

        generate_speech(
            client=mock_client,
            text="hello",
            voice="alloy",
            model_name="tts-1",
            response_format="wav",
            output_path="/tmp/test",
        )
        assert mock_client.audio.speech.with_streaming_response.create.call_count == 2

    @patch("local_notebooklm.steps.helpers.time.sleep")
    def test_fails_after_max_retries_speech(self, mock_sleep):
        from local_notebooklm.steps.helpers import generate_speech

        mock_client = MagicMock()
        mock_client.audio.speech.with_streaming_response.create.side_effect = RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="failed after 3 attempts"):
            generate_speech(
                client=mock_client,
                text="hello",
                voice="alloy",
                model_name="tts-1",
                response_format="wav",
                output_path="/tmp/test",
            )


class TestExponentialBackoff:
    @patch("local_notebooklm.steps.helpers._call_llm", side_effect=[RuntimeError, RuntimeError, "ok"])
    @patch("local_notebooklm.steps.helpers.time.sleep")
    def test_delay_doubles(self, mock_sleep, mock_call):
        from local_notebooklm.steps.helpers import generate_text

        generate_text(
            client=MagicMock(),
            messages=[{"role": "user", "content": "hi"}],
        )
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [2, 4]  # base=2, then 4
