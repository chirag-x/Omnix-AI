import base64
import io
import threading
import pygame
from utils.logger import log
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes


from core.settings import SettingsManager
from core.task_control import register_stop_callback

_playback_lock = threading.Lock()
_state_lock = threading.Lock()
_generation = 0

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
    try:
        pygame.mixer.init()
    except Exception as fallback_error:
        log.error(f"Audio output unavailable: {fallback_error}")

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
        with _state_lock:
            generation = _generation
        threading.Thread(target=_play, args=(audio_io, generation), daemon=True).start()
    except Exception as e:
        log.error(f"TTS Player error: {e}")

import time
LAST_TTS_END_TIME = 0.0

def stop_audio():
    """Stop current speech and invalidate any playback waiting for the mixer."""
    global _generation, LAST_TTS_END_TIME
    with _state_lock:
        _generation += 1
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        LAST_TTS_END_TIME = time.time()
        event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_PLAYBACK_FINISHED))


register_stop_callback(stop_audio)


def _play(audio_io: io.BytesIO, generation: int):
    global LAST_TTS_END_TIME
    # One mixer channel: serialize responses instead of replacing mid-sentence.
    with _playback_lock:
        try:
            with _state_lock:
                if generation != _generation:
                    return
                if not pygame.mixer.get_init():
                    pygame.mixer.init(devicename=dev_name)
                header = audio_io.read(4)
                audio_io.seek(0)
                fmt = "wav" if header == b"RIFF" else "mp3"
                pygame.mixer.music.load(audio_io, fmt)
                pygame.mixer.music.play()
                event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_PLAYBACK_STARTED))
            while is_playing():
                with _state_lock:
                    if generation != _generation:
                        break
                pygame.time.Clock().tick(20)
        except Exception as e:
            log.error(f"Pygame playback error: {e}")
        finally:
            LAST_TTS_END_TIME = time.time()
            event_bus.publish(OmnixEvent(event_type=EventTypes.TTS_PLAYBACK_FINISHED))

def is_playing() -> bool:
    return bool(pygame.mixer.get_init()) and pygame.mixer.music.get_busy()

def recently_played(buffer_seconds=2.0) -> bool:
    """Returns True if TTS is playing OR just finished within the buffer window."""
    if is_playing():
        return True
    return (time.time() - LAST_TTS_END_TIME) < buffer_seconds
