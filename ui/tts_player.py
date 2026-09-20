import base64
import io
import threading
import pygame
from utils.logger import log

from core.settings import SettingsManager

# Check output device
out_dev = SettingsManager.get("audio_output_device")
dev_name = None
if out_dev and out_dev != "Default System Speaker":
    dev_name = out_dev

# Initialize pygame mixer once
pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
try:
    pygame.mixer.init(devicename=dev_name)
except Exception as e:
    log.warning(f"Failed to init pygame mixer with device '{dev_name}': {e}. Falling back to default.")
    pygame.mixer.init()

def play_audio_b64(audio_b64: str):
    """Play a base64-encoded mp3 string through system speakers."""
    if not audio_b64:
        return
    if not SettingsManager.get("audio_output_enabled", True):
        log.info("Audio output disabled in settings, skipping TTS playback.")
        return
    try:
        audio_bytes = base64.b64decode(audio_b64)
        audio_io = io.BytesIO(audio_bytes)
        threading.Thread(target=_play, args=(audio_io,), daemon=True).start()
    except Exception as e:
        log.error(f"TTS Player error: {e}")

def _play(audio_io: io.BytesIO):
    try:
        # Detect format from magic bytes: WAV starts with b'RIFF', MP3 starts with b'ID3' or 0xFF
        header = audio_io.read(4)
        audio_io.seek(0)
        fmt = "wav" if header[:4] == b"RIFF" else "mp3"

        pygame.mixer.music.load(audio_io, fmt)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        log.error(f"Pygame playback error: {e}")

def is_playing() -> bool:
    return pygame.mixer.music.get_busy()
