"""Tests for config validation."""

import copy
import pytest
from local_notebooklm.config import validate_config, ConfigValidationError, base_config


def _valid_config():
    """Return a config dict that passes validation."""
    return {
        "Host-Speaker-Voice": "alloy",
        "Co-Host-Speaker-Voice": "echo",
        "Co-Host-Speaker-1-Voice": "echo",
        "Co-Host-Speaker-2-Voice": "fable",
        "Co-Host-Speaker-3-Voice": "onyx",
        "Co-Host-Speaker-4-Voice": "nova",
        "Small-Text-Model": {
            "provider": {"name": "openai", "key": "sk-test"},
            "model": "gpt-4o-mini",
        },
        "Big-Text-Model": {
            "provider": {"name": "openai", "key": "sk-test"},
            "model": "gpt-4o",
        },
        "Text-To-Speech-Model": {
            "provider": {"name": "openai", "key": "sk-test"},
            "model": "tts-1",
            "audio_format": "wav",
        },
        "Step1": {"max_tokens": 1028, "temperature": 0.7, "chunk_size": 1000, "max_chars": 100000},
        "Step2": {"max_tokens": 8126, "temperature": 1},
        "Step3": {"max_tokens": 8126, "temperature": 1},
    }


class TestValidConfig:
    def test_valid_passes(self):
        validate_config(_valid_config())

    def test_base_config_passes(self):
        """The built-in base_config should also pass (all keys present, correct types)."""
        validate_config(base_config)


class TestMissingKeys:
    def test_missing_host_voice(self):
        cfg = _valid_config()
        del cfg["Host-Speaker-Voice"]
        with pytest.raises(ConfigValidationError, match="Host-Speaker-Voice"):
            validate_config(cfg)

    def test_missing_small_text_model(self):
        cfg = _valid_config()
        del cfg["Small-Text-Model"]
        with pytest.raises(ConfigValidationError, match="Small-Text-Model"):
            validate_config(cfg)

    def test_missing_provider_name(self):
        cfg = _valid_config()
        del cfg["Small-Text-Model"]["provider"]["name"]
        with pytest.raises(ConfigValidationError, match="provider.name"):
            validate_config(cfg)

    def test_missing_step1(self):
        cfg = _valid_config()
        del cfg["Step1"]
        with pytest.raises(ConfigValidationError, match="Step1"):
            validate_config(cfg)

    def test_missing_step1_max_tokens(self):
        cfg = _valid_config()
        del cfg["Step1"]["max_tokens"]
        with pytest.raises(ConfigValidationError, match="Step1.max_tokens"):
            validate_config(cfg)

    def test_missing_tts_model(self):
        cfg = _valid_config()
        del cfg["Text-To-Speech-Model"]["model"]
        with pytest.raises(ConfigValidationError, match="Text-To-Speech-Model.model"):
            validate_config(cfg)


class TestWrongTypes:
    def test_step1_max_tokens_string(self):
        cfg = _valid_config()
        cfg["Step1"]["max_tokens"] = "not_an_int"
        with pytest.raises(ConfigValidationError, match="Step1.max_tokens"):
            validate_config(cfg)

    def test_temperature_accepts_int_and_float(self):
        cfg = _valid_config()
        cfg["Step1"]["temperature"] = 1  # int should be valid
        validate_config(cfg)  # should not raise

        cfg["Step1"]["temperature"] = 0.7  # float also valid
        validate_config(cfg)

    def test_provider_name_not_string(self):
        cfg = _valid_config()
        cfg["Big-Text-Model"]["provider"]["name"] = 123
        with pytest.raises(ConfigValidationError, match="provider.name"):
            validate_config(cfg)

    def test_step_not_dict(self):
        cfg = _valid_config()
        cfg["Step2"] = "wrong"
        with pytest.raises(ConfigValidationError, match="Step2"):
            validate_config(cfg)


class TestMultipleErrors:
    def test_reports_all_problems(self):
        cfg = _valid_config()
        del cfg["Step1"]["max_tokens"]
        del cfg["Step2"]["temperature"]
        del cfg["Host-Speaker-Voice"]
        with pytest.raises(ConfigValidationError, match="3 problem"):
            validate_config(cfg)
