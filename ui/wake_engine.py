import threading
import time
import speech_recognition as sr
import io
from faster_whisper import WhisperModel
from utils.logger import log
from core.config import Config
from core.settings import SettingsManager

class WakeEngine:
    """
    Uses SpeechRecognition to detect when someone is talking, 
    and passes the audio to a tiny Whisper model to check for the wake word.
    """
    def __init__(self, on_wake_detected):
        self.on_wake_detected = on_wake_detected
        self._running = False
        self._awake = False
        self._model = None
        self._recognizer = sr.Recognizer()
        
        # Tune dynamic thresholding to ignore breathing/air but catch speech reliably
        self._recognizer.energy_threshold = 150 
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.dynamic_energy_ratio = 1.2  # Require a louder spike (speaking) to trigger, ignoring low noise (default is 1.5)
        self._recognizer.pause_threshold = 0.5  # Only wait 0.5s of silence before processing
        self._recognizer.phrase_threshold = 0.5 # Ignore sounds shorter than 0.5s (like a quick breath or cough)
        
        self._stop_listening_func = None

    @property
    def model(self):
        """Return the loaded WhisperModel so CommandListener can reuse it."""
        return self._model

    def set_awake(self, value: bool):
        self._awake = value

    def start(self):
        self._running = True
        threading.Thread(target=self._init_and_start, daemon=True).start()

    def stop(self):
        self._running = False
        if self._stop_listening_func:
            self._stop_listening_func(wait_for_stop=False)

    def _init_and_start(self):
        model_name = SettingsManager.get("wakeword_model", "tiny.en")
        import os
        base_dir = SettingsManager.get("default_download_location", "E:/Coding/Omnix/Omnix/Default_Downloads")
        local_path = os.path.join(base_dir, "model", model_name)
        
        if not os.path.exists(local_path):
            log.error(f"WakeEngine ERROR: Model '{model_name}' not found in {local_path}. Please download the model first from the Settings menu.")
            return

        log.info(f"WakeEngine actively using model: [{model_name}] (Loaded from: {local_path})")
        try:
            models_dir = Config.get_wakeword_models_dir()
                
            self._model = WhisperModel(
                local_path, 
                device="cpu", 
                compute_type=Config.get_whisper_compute_type(),
                download_root=models_dir
            )
            
            import sounddevice as sd
            device_name = SettingsManager.get("audio_input_device")
            dev_idx = None
            if device_name and device_name != "Default System Microphone":
                try:
                    for i, d in enumerate(sd.query_devices()):
                        if d['name'] == device_name and d['max_input_channels'] > 0:
                            dev_idx = i
                            break
                except:
                    pass
            mic = sr.Microphone(device_index=dev_idx)
            with mic as source:
                log.info("WakeEngine: Calibrating ambient noise for 1 second...")
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                
            log.info("WakeEngine: Ready! Listening for 'Hey Omnix'...")
            
            # Start background listener
            self._stop_listening_func = self._recognizer.listen_in_background(
                source=mic, 
                callback=self._audio_callback,
                phrase_time_limit=3  # Stop capturing after 3 seconds to process instantly
            )
            
            while self._running:
                time.sleep(1)
                
        except Exception as e:
            log.error(f"WakeEngine failed to start: {e}")

    def _audio_callback(self, recognizer, audio):
        if not SettingsManager.get("audio_input_enabled", True): return
        if self._awake or not self._running:
            return
            
        log.debug(f"WakeEngine: Sound detected! Processing through {SettingsManager.get('wakeword_model', 'tiny.en')}...")
        try:
            audio_io = io.BytesIO(audio.get_wav_data())
            
            # Use initial_prompt to heavily bias the model to recognize 'Omnix' instead of random words
            segments, info = self._model.transcribe(
                audio_io, 
                beam_size=1, 
                condition_on_previous_text=False,
                vad_filter=False,
                initial_prompt="Hey Omnix, Omnix, wake up." if SettingsManager.get("wakeword_phrase", "Any Wake Word") == "Any Wake Word" else f"{SettingsManager.get('wakeword_phrase')}, Omnix, wake up."
            )
            
            transcript = " ".join([segment.text for segment in segments]).lower()
            
            if transcript.strip():
                print(f"[DEBUG] Heard: '{transcript.strip()}'")
                
                # Ensure we use exactly the phrases requested
                hardcoded_wake_words = ["hey omnix", "omnix", "hello omnix", "omnix wake up", "wake up", "wake up omnix"]
                # Also include common misheard variations of "Omnix" and "wake up"
                fallback_words = ["ponniks", "v x", "onix", "amics", "week up", "next week up", "vehicle", "o, n, x"]
                
                selected_phrase = SettingsManager.get('wakeword_phrase', 'Any Wake Word').lower()
                if selected_phrase == 'any wake word':
                    valid_phrases = hardcoded_wake_words + fallback_words
                else:
                    valid_phrases = [selected_phrase] + fallback_words
                    
                if any(word in transcript for word in valid_phrases):
                    log.info(f"WakeEngine: Wake word detected! matched: '{transcript.strip()}'")
                    if self.on_wake_detected:
                        self.on_wake_detected()
                        
        except Exception as e:
            log.error(f"WakeEngine processing error: {e}")