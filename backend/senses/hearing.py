import os
import tempfile
from faster_whisper import WhisperModel
from utils.logger import log
from core.config import Config

from core.settings import SettingsManager
stt_dev = SettingsManager.get("stt_device", "auto")
if stt_dev == "cloud_groq":
    log.info("Speech-to-Text Engine actively using Groq Cloud API.")
    model = None
else:
    compute_t = "int8" if stt_dev == "cpu" else "int8_float16"
    log.info(f"Loading Whisper model from local path (device={stt_dev})...")
    model = WhisperModel(Config.get_whisper_model_path(), device=stt_dev, compute_type=compute_t)

def transcribe_audio(audio_data: bytes) -> str:
    log.info("Transcribing audio...")
    try:
        if stt_dev == "cloud_groq":
            import requests
            api_key = SettingsManager.get("groq_api_key", "")
            stt_model = SettingsManager.get("groq_stt_model", "whisper-large-v3-turbo")
            if not api_key:
                log.error("Hearing: Groq API Key is missing!")
                return ""
                
            files = {"file": ("audio.webm", audio_data, "audio/webm")}
            data = {"model": stt_model, "language": "en"}
            headers = {"Authorization": f"Bearer {api_key}"}
            
            response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=10)
            if response.status_code == 200:
                user_text = response.json().get("text", "").strip()
            else:
                log.error(f"Groq API Error: {response.status_code} - {response.text}")
                user_text = ""
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as fp:
                fp.write(audio_data)
                temp_path = fp.name
                
            segments, info = model.transcribe(
                temp_path, 
                beam_size=5,
                initial_prompt="Open Spotify and play Believer. Close Chrome. Search for a song."
            )
            user_text = "".join([segment.text for segment in segments]).strip()
            os.unlink(temp_path)
        
        # Voro-like cleanup
        cleanup_phrases = {"Open is ": "Open ", "Open your ": "Open ", "Play a ": "Play "}
        for bad, good in cleanup_phrases.items():
            user_text = user_text.replace(bad, good).replace(bad.lower(), good.lower())
            
        log.info(f"Transcribed and Refined: '{user_text}'")
        return user_text
    except Exception as e:
        log.error(f"Hearing Error: {e}")
        return ""
