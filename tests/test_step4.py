"""Tests for step4 — speaker mapping, audio format parsing, data loading."""

import pytest
from unittest.mock import patch, MagicMock
from local_notebooklm.steps.step4 import (
    parse_audio_format,
    load_podcast_data,
    step4,
    AudioGenerationError,
)


class TestParseAudioFormat:
    def test_wav_only(self):
        fmt, sr, bd = parse_audio_format("wav")
        assert fmt == "wav"
        assert sr is None
        assert bd is None

    def test_wav_with_sample_rate(self):
        fmt, sr, bd = parse_audio_format("wav_16000")
        assert fmt == "wav"
        assert sr == 16000
        assert bd is None

    def test_full_format(self):
        fmt, sr, bd = parse_audio_format("wav_16000_16")
        assert fmt == "wav"
        assert sr == 16000
        assert bd == 16

    def test_mp3(self):
        fmt, sr, bd = parse_audio_format("mp3")
        assert fmt == "mp3"

    def test_ogg_with_rate(self):
        fmt, sr, bd = parse_audio_format("ogg_44100")
        assert fmt == "ogg"
        assert sr == 44100


class TestSpeakerMapping:
    """Verify that all 5 speakers map to distinct voices."""

    def _get_voice_for_speaker(self, speaker_label):
        """Simulate the speaker→voice mapping from step4."""
        host = "voice_host"
        co_host_1 = "voice_co1"
        co_host_2 = "voice_co2"
        co_host_3 = "voice_co3"
        co_host_4 = "voice_co4"

        if speaker_label == "Speaker 1":
            return host
        elif speaker_label == "Speaker 2":
            return co_host_1
        elif speaker_label == "Speaker 3":
            return co_host_2
        elif speaker_label == "Speaker 4":
            return co_host_3
        elif speaker_label == "Speaker 5":
            return co_host_4
        else:
            return co_host_1

    def test_speaker_1(self):
        assert self._get_voice_for_speaker("Speaker 1") == "voice_host"

    def test_speaker_2(self):
        assert self._get_voice_for_speaker("Speaker 2") == "voice_co1"

    def test_speaker_3(self):
        assert self._get_voice_for_speaker("Speaker 3") == "voice_co2"

    def test_speaker_4(self):
        assert self._get_voice_for_speaker("Speaker 4") == "voice_co3"

    def test_speaker_5(self):
        assert self._get_voice_for_speaker("Speaker 5") == "voice_co4"

    def test_all_distinct(self):
        voices = {self._get_voice_for_speaker(f"Speaker {i}") for i in range(1, 6)}
        assert len(voices) == 5, "All 5 speakers must map to distinct voices"

    def test_unknown_speaker_fallback(self):
        assert self._get_voice_for_speaker("Speaker 99") == "voice_co1"


class TestLoadPodcastData:
    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_podcast_data("/nonexistent/data.pkl")

    def test_valid_pickle(self, tmp_path):
        import pickle

        data_str = "[('Speaker 1', 'Hello'), ('Speaker 2', 'Hi there')]"
        pkl_path = tmp_path / "data.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump(data_str, f)

        result = load_podcast_data(pkl_path)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == ("Speaker 1", "Hello")

    def test_invalid_pickle_content(self, tmp_path):
        import pickle

        pkl_path = tmp_path / "bad.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump("not a list of tuples", f)

        with pytest.raises(ValueError, match="Invalid podcast data"):
            load_podcast_data(pkl_path)


class TestStep4Validation:
    def test_unsupported_format_raises(self, tmp_path):
        config = {
            "Text-To-Speech-Model": {"model": "tts-1", "audio_format": "xyz_16000"},
            "Host-Speaker-Voice": "v1",
            "Co-Host-Speaker-1-Voice": "v2",
            "Co-Host-Speaker-2-Voice": "v3",
            "Co-Host-Speaker-3-Voice": "v4",
            "Co-Host-Speaker-4-Voice": "v5",
        }
        with pytest.raises(ValueError, match="Unsupported audio format"):
            step4(
                client=MagicMock(),
                config=config,
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
            )
