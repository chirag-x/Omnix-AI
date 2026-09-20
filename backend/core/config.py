from core.settings import SettingsManager
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    # Load dynamic values from Settings (user-configurable)
    @classmethod
    def get_omniroute_base_url(cls):
        return os.getenv("OMNIROUTE_BASE_URL", SettingsManager.get("omniroute_base_url"))

    @classmethod
    def get_omniroute_api_key(cls):
        return os.getenv("OMNIROUTE_API_KEY", SettingsManager.get("omniroute_api_key"))

    @classmethod
    def get_fallback_models(cls):
        return SettingsManager.get("fallback_models")

    @classmethod
    def get_whisper_model_path(cls):
        return SettingsManager.get("whisper_model_path")

    @classmethod
    def get_whisper_compute_type(cls):
        return SettingsManager.get("whisper_compute_type")

    @classmethod
    def get_wakeword_models_dir(cls):
        return SettingsManager.get("wakeword_models_dir")

    @classmethod
    def get_tts_voice(cls):
        return SettingsManager.get("tts_voice")

    TEMP_DIR = BASE_DIR / "temp"

    @classmethod
    def ensure_dirs(cls):
        cls.TEMP_DIR.mkdir(exist_ok=True)
        # Ensure wakeword models dir is on E drive
        from pathlib import Path
        Path(cls.get_wakeword_models_dir()).mkdir(parents=True, exist_ok=True)
