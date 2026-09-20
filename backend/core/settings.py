import json
import os
from pathlib import Path

# Settings file lives at the Omnix project root (E:\Coding\Omnix\omnix_settings.json)
SETTINGS_PATH = Path(__file__).resolve().parent.parent.parent / "omnix_settings.json"

DEFAULTS = {
    "whisper_model_path": r"E:\Coding\Omnix\Omnix\Default_Downloads\model\medium.en",
    "whisper_compute_type": "int8",
    "wakeword_models_dir": r"E:\Coding\Omnix\backend\models\wakeword",
    "omniroute_base_url": "http://localhost:20128/v1",
    "omniroute_api_key": "",
    "fallback_models": [
        "antigravity/gemini-3.6-flash-high",
        "antigravity/claude-sonnet-4-6",
        "antigravity/claude-opus-4-6-thinking",
        "antigravity/gemini-3.6-flash-medium",
        "antigravity/gemini-3-flash-agent",
        "antigravity/gemini-3.1-flash-lite",
        "antigravity/gemini-2.5-flash"
    ],
    "wake_words": ["omnix", "hey omnix", "wake up omnix", "yo omnix", "wake up"],
    "sleep_timeout_seconds": 30,
    "tts_voice": "en-US-ChristopherNeural"
}

class SettingsManager:
    _instance = None
    _data = {}

    @classmethod
    def load(cls):
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r") as f:
                cls._data = json.load(f)
        else:
            cls._data = DEFAULTS.copy()
            cls.save()
        # Fill in any missing keys from defaults
        changed = False
        for k, v in DEFAULTS.items():
            if k not in cls._data:
                cls._data[k] = v
                changed = True
        if changed:
            cls.save()

    @classmethod
    def save(cls):
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(cls._data, f, indent=2)

    @classmethod
    def get(cls, key: str, default=None):
        if not cls._data:
            cls.load()
        return cls._data.get(key, default if default is not None else DEFAULTS.get(key))

    @classmethod
    def set(cls, key: str, value):
        if not cls._data:
            cls.load()
        cls._data[key] = value
        cls.save()

    @classmethod
    def all(cls) -> dict:
        if not cls._data:
            cls.load()
        return cls._data.copy()

# Load settings on import
SettingsManager.load()
