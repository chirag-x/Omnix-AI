import edge_tts
import tempfile
import base64
import os
import asyncio
from utils.logger import log
from core.settings import SettingsManager

def _generate_local_audio_sync(text: str, voice_pref: str) -> str:
    """Uses pyttsx3 for completely offline TTS generation."""
    try:
        import pyttsx3
    except ImportError:
        log.error("pyttsx3 not installed. Cannot use Local TTS.")
        return ""
        
    log.info(f"Generating Local TTS for: {text}")
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
            
        engine.save_to_file(text, temp_path)
        engine.runAndWait()
        
        with open(temp_path, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")
            
        try:
            os.unlink(temp_path)
        except:
            pass
        return encoded_audio
    except Exception as e:
        log.error(f"Local TTS Error: {e}")
        return ""

async def generate_audio(text: str, voice_pref: str = None) -> str:
    engine_choice = SettingsManager.get("tts_engine", "Edge-TTS (Online)")
    voice = voice_pref or SettingsManager.get("voice_selection", "en-US-ChristopherNeural")
    
    if engine_choice == "Local":
        return await asyncio.to_thread(_generate_local_audio_sync, text, voice)
        
    log.info(f"Generating Edge-TTS for: {text} using voice: {voice}")
    try:
        communicate = edge_tts.Communicate(text, voice)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
            
        await communicate.save(temp_path)
        
        with open(temp_path, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")
            
        try:
            os.unlink(temp_path)
        except:
            pass
        return encoded_audio
    except Exception as e:
        log.error(f"Edge-TTS Error: {e}")
        return ""
