import json
import os
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULT_SETTINGS = {
    "brain": {
        "active_provider": "ollama",  # options: ollama, openai, anthropic, gemini
        "ollama": {
            "model": "llama3.2",
            "base_url": "http://localhost:11434/v1" 
        },
        "openai": {
            "model": "gpt-4o",
            "api_key": ""
        },
        "anthropic": {
            "model": "claude-3-5-sonnet-20240620",
            "api_key": ""
        },
        "gemini": {
            "model": "gemini-1.5-pro",
            "api_key": ""
        }
    }
}

class ConfigManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                try:
                    loaded = json.load(f)
                    # Simple merge to keep defaults if keys are missing
                    self._merge_dicts(self.settings, loaded)
                except json.JSONDecodeError:
                    print("Error parsing settings.json. Using defaults.")
        else:
            self.save_settings()

    def save_settings(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def _merge_dicts(self, default_dict, new_dict):
        for k, v in new_dict.items():
            if isinstance(v, dict) and k in default_dict and isinstance(default_dict[k], dict):
                self._merge_dicts(default_dict[k], v)
            else:
                default_dict[k] = v

    def get(self, *keys):
        val = self.settings
        for key in keys:
            val = val.get(key, {})
        return val if val != {} else None

    def update_provider(self, provider_name):
        if provider_name in ["ollama", "openai", "anthropic", "gemini"]:
            self.settings["brain"]["active_provider"] = provider_name
            self.save_settings()

    def update_ollama_model(self, model_name):
        self.settings["brain"]["ollama"]["model"] = model_name
        self.save_settings()

config = ConfigManager()
