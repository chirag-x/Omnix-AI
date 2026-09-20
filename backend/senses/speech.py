import io
import re
import base64
import asyncio
import tempfile
import os
import soundfile as sf
import edge_tts
from utils.logger import log
from core.settings import SettingsManager

# ─── Kokoro model paths ───────────────────────────────────────────────────────

_KOKORO_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "kokoro")
_MODEL_PATH  = os.path.join(_KOKORO_DIR, "kokoro-v1.0.onnx")
_VOICES_PATH = os.path.join(_KOKORO_DIR, "voices-v1.0.bin")

_MODEL_URL  = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx"
_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin"

# ─── Emotion → Voice + Speed mapping ─────────────────────────────────────────
# Each emotion maps to a distinct Kokoro voice character + a speed multiplier.
# af_sky   = bright, upbeat, energetic
# af_bella = warm, expressive, natural  (best all-rounder)
# af_heart = soft, gentle, calm
# am_adam  = deep, measured, serious
# am_michael = conversational, natural male

_EMOTION_PROFILE = {
    "happy":    {"voice": "af_sky",    "speed": 1.15},
    "excited":  {"voice": "af_sky",    "speed": 1.25},
    "neutral":  {"voice": "af_bella",  "speed": 1.0},
    "confused": {"voice": "af_bella",  "speed": 0.92},
    "sad":      {"voice": "af_heart",  "speed": 0.88},
    "angry":    {"voice": "am_adam",   "speed": 1.05},
    "thinking": {"voice": "af_bella",  "speed": 0.95},
}

_DEFAULT_PROFILE = {"voice": "af_bella", "speed": 1.0}

# ─── Text preprocessor (Fix 3) ───────────────────────────────────────────────

def _preprocess_text(text: str, emotion: str) -> str:
    """
    Clean and reshape text so it sounds natural when spoken aloud.
    - Splits run-on sentences into shorter breathable chunks
    - Removes markdown symbols that TTS would read literally
    - Normalises punctuation for natural pacing
    """
    # Strip markdown bold/italic/code
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'#+\s*', '', text)

    # Replace em-dashes / double-dashes with a comma pause
    text = text.replace('—', ', ').replace(' -- ', ', ')

    # Replace " - " used as a list bullet with a comma
    text = re.sub(r'\s+-\s+', ', ', text)

    # Collapse multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()

    # Split sentences longer than ~120 chars at natural break points
    # so Kokoro doesn't rush through a wall of words
    sentences = re.split(r'(?<=[.!?])\s+', text)
    processed = []
    for sentence in sentences:
        if len(sentence) > 120:
            # Try to split at a comma midpoint
            halves = sentence.split(', ', 1)
            if len(halves) == 2:
                processed.append(halves[0] + ',')
                processed.append(halves[1])
            else:
                processed.append(sentence)
        else:
            processed.append(sentence)

    return ' '.join(processed)


# ─── Auto-download helper ─────────────────────────────────────────────────────

def _download_file(url: str, dest: str):
    import urllib.request
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    log.info(f"Kokoro: Downloading {os.path.basename(dest)} from GitHub... (this happens once)")
    try:
        urllib.request.urlretrieve(url, dest)
        log.info(f"Kokoro: Downloaded {os.path.basename(dest)} ({os.path.getsize(dest) // 1024 // 1024} MB)")
    except Exception as e:
        log.error(f"Kokoro: Download failed for {os.path.basename(dest)}: {e}")
        raise

def _ensure_models():
    if not os.path.exists(_MODEL_PATH):
        _download_file(_MODEL_URL, _MODEL_PATH)
    if not os.path.exists(_VOICES_PATH):
        _download_file(_VOICES_URL, _VOICES_PATH)

# ─── Kokoro lazy singleton ────────────────────────────────────────────────────

_kokoro_instance = None

def _get_kokoro():
    global _kokoro_instance
    if _kokoro_instance is None:
        _ensure_models()
        from kokoro_onnx import Kokoro
        _kokoro_instance = Kokoro(_MODEL_PATH, _VOICES_PATH)
        log.info("Kokoro: Model loaded and ready.")
    return _kokoro_instance


# ─── Kokoro engine ────────────────────────────────────────────────────────────

def _generate_kokoro_sync(text: str, emotion: str) -> str:
    """Generate audio with Kokoro (offline, neural). Returns base64-encoded WAV."""
    try:
        # Fix 3: preprocess text for natural speech
        clean_text = _preprocess_text(text, emotion)

        # Fix 2: pick voice + speed from emotion profile
        profile = _EMOTION_PROFILE.get(emotion, _DEFAULT_PROFILE)
        voice   = profile["voice"]
        speed   = profile["speed"]

        log.info(f"Kokoro TTS [{emotion}] voice={voice} speed={speed}: {clean_text}")
        kokoro = _get_kokoro()
        samples, sample_rate = kokoro.create(clean_text, voice=voice, speed=speed, lang="en-us")

        buf = io.BytesIO()
        sf.write(buf, samples, sample_rate, format="WAV")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    except Exception as e:
        log.error(f"Kokoro TTS Error: {e}")
        return ""


# ─── Edge-TTS engine (Script mode) ───────────────────────────────────────────

async def _generate_edge_tts(text: str, voice: str) -> str:
    """Generate audio with Microsoft Edge-TTS (online). Returns base64-encoded MP3."""
    log.info(f"Edge-TTS generating (voice={voice}): {text}")
    try:
        communicate = edge_tts.Communicate(text, voice)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
        await communicate.save(temp_path)
        with open(temp_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        try:
            os.unlink(temp_path)
        except:
            pass
        return encoded
    except Exception as e:
        log.error(f"Edge-TTS Error: {e}")
        return ""


# ─── Public API ───────────────────────────────────────────────────────────────

async def generate_audio(text: str, voice_pref: str = None, emotion: str = "neutral") -> str:
    """
    Generate TTS audio and return it as a base64-encoded string.

    audio_mode setting:
        "Natural"  → Kokoro (offline neural, emotion-aware, no internet needed)
        "Script"   → Edge-TTS (online, Microsoft voices)
    """
    if not text or not text.strip():
        return ""

    audio_mode = SettingsManager.get("audio_mode", "Natural")

    if audio_mode == "Natural":
        return await asyncio.to_thread(_generate_kokoro_sync, text, emotion)
    else:
        voice = voice_pref or SettingsManager.get("voice_selection", "en-US-ChristopherNeural")
        return await _generate_edge_tts(text, voice)
