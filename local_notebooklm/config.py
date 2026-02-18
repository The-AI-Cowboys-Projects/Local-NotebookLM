from typing import Dict, Any, List


class ConfigValidationError(Exception):
    pass


def validate_config(config: Dict[str, Any]) -> None:
    """Validate that a config dict has all required keys with correct types.

    Raises ConfigValidationError with a summary of every problem found.
    """
    errors: List[str] = []

    def _require(path: str, expected_type: type):
        keys = path.split(".")
        obj = config
        for k in keys:
            if not isinstance(obj, dict):
                errors.append(f"'{path}': parent is not a dict")
                return
            if k not in obj:
                errors.append(f"'{path}': missing required key")
                return
            obj = obj[k]
        if not isinstance(obj, expected_type):
            errors.append(f"'{path}': expected {expected_type.__name__}, got {type(obj).__name__}")

    # Model provider sections
    for section in ("Small-Text-Model", "Big-Text-Model"):
        _require(section, dict)
        _require(f"{section}.provider", dict)
        _require(f"{section}.provider.name", str)
        _require(f"{section}.model", str)

    # TTS section
    _require("Text-To-Speech-Model", dict)
    _require("Text-To-Speech-Model.provider", dict)
    _require("Text-To-Speech-Model.provider.name", str)
    _require("Text-To-Speech-Model.model", str)

    # Voice keys
    _require("Host-Speaker-Voice", str)

    # Step parameters
    for step, required_keys in {
        "Step1": {"max_tokens": int, "temperature": (int, float), "chunk_size": int, "max_chars": int},
        "Step2": {"max_tokens": int, "temperature": (int, float)},
        "Step3": {"max_tokens": int, "temperature": (int, float)},
    }.items():
        _require(step, dict)
        if isinstance(config.get(step), dict):
            for key, typ in required_keys.items():
                full = f"{step}.{key}"
                if key not in config[step]:
                    errors.append(f"'{full}': missing required key")
                elif not isinstance(config[step][key], typ):
                    errors.append(f"'{full}': expected {typ}, got {type(config[step][key]).__name__}")

    if errors:
        raise ConfigValidationError(
            f"Config has {len(errors)} problem(s):\n  - " + "\n  - ".join(errors)
        )


base_config: Dict[str, Any] = {
    "Co-Host-Speaker-Voice": "",
    "Host-Speaker-Voice": "",
    "Co-Host-Speaker-1-Voice": "",
    "Co-Host-Speaker-2-Voice": "",
    "Co-Host-Speaker-3-Voice": "",
    "Co-Host-Speaker-4-Voice": "",

    "Small-Text-Model": {
        "provider": {
            "name": "",
            "key": ""
        },
        "model": ""
    },

    "Big-Text-Model": {
        "provider": {
            "name": "",
            "key": ""
        },
        "model": ""
    },

    "Text-To-Speech-Model": {
        "provider": {
            "name": "",
            "endpoint": "",
            "key": ""
        },
        "model": "",
        "audio_format": ""
    },

    "Step1": {
        "max_tokens": 1028,
        "temperature": 0.7,
        "chunk_size": 1000,
        "max_chars": 100000
    },

    "Step2": {
        "max_tokens": 8126,
        "temperature": 1
    },

    "Step3": {
        "max_tokens": 8126,
        "temperature": 1
    },

    "Step5": {
        "max_tokens": 4096,
        "temperature": 0.4
    }
}
