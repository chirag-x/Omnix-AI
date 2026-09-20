import os
import tempfile
from faster_whisper import WhisperModel
from utils.logger import log
from core.config import Config

log.info("Loading Whisper model from local path...")
model = WhisperModel(Config.get_whisper_model_path(), device="cpu", compute_type=Config.get_whisper_compute_type())

def transcribe_audio(audio_data: bytes) -> str:
    log.info("Transcribing audio...")
    try:
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
