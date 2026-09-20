import threading
import time
import pyaudio
import numpy as np
from openwakeword.model import Model
from utils.logger import log
from core.settings import SettingsManager

class WakeEngine:
    """
    Uses openWakeWord to detect custom wake words with zero latency.
    """
    def __init__(self, on_wake_detected):
        self.on_wake_detected = on_wake_detected
        self._running = False
        self._awake = False
        self._oww_model = None
        self._audio = None
        self._mic_stream = None

    @property
    def model(self):
        """Return the loaded OWW model to signal app.py that it's ready."""
        return self._oww_model

    def set_awake(self, value: bool):
        self._awake = value
        # Clear any accumulated audio when we wake up or go to sleep so we don't process old data
        if not value and self._mic_stream:
            try:
                # Flush buffer
                available = self._mic_stream.get_read_available()
                if available > 0:
                    self._mic_stream.read(available, exception_on_overflow=False)
            except:
                pass

    def start(self):
        self._running = True
        threading.Thread(target=self._init_and_start, daemon=True).start()

    def stop(self):
        self._running = False
        if self._mic_stream:
            self._mic_stream.stop_stream()
            self._mic_stream.close()
        if self._audio:
            self._audio.terminate()

    def _init_and_start(self):
        log.info("WakeEngine: Initializing openWakeWord...")
        try:
            model_path = r"E:\Coding\Omnix\backend\models\wakeword\hey_jarvis_v0.1.onnx"
            self._oww_model = Model(wakeword_models=[model_path], inference_framework="onnx")
            
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            CHUNK = 1280
            
            self._audio = pyaudio.PyAudio()
            
            import sounddevice as sd
            device_name = SettingsManager.get("audio_input_device")
            dev_idx = None
            if device_name and device_name != "Default System Microphone":
                try:
                    for i in range(self._audio.get_device_count()):
                        d = self._audio.get_device_info_by_index(i)
                        name = d.get('name', '')
                        if (device_name in name or name in device_name) and d.get('maxInputChannels', 0) > 0:
                            dev_idx = i
                            log.info(f"WakeEngine: Selected Microphone [{i}]: {name}")
                            break
                except Exception as e:
                    log.warning(f"WakeEngine: Failed to match microphone: {e}")
            
            self._mic_stream = self._audio.open(
                format=FORMAT, 
                channels=CHANNELS, 
                rate=RATE, 
                input=True, 
                input_device_index=dev_idx,
                frames_per_buffer=CHUNK
            )
            
            log.info("WakeEngine: Ready! Listening for wake word (Hey Jarvis)...")
            
            while self._running:
                if not SettingsManager.get("audio_input_enabled", True):
                    time.sleep(1)
                    continue
                    
                if self._awake:
                    time.sleep(0.1)
                    continue
                    
                try:
                    raw_audio = self._mic_stream.read(CHUNK, exception_on_overflow=False)
                    audio_data = np.frombuffer(raw_audio, dtype=np.int16)
                    
                    # Log RMS occasionally to debug if mic is silent
                    rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                    
                    prediction = self._oww_model.predict(audio_data)
                    
                    for mdl, score in prediction.items():
                        # Debug: Print if it hears *something* close
                        if score > 0.05:
                            print(f"[DEBUG] OWW Score for {mdl}: {score:.4f} (Mic RMS: {rms:.1f})")
                            
                        # Standard openwakeword threshold is 0.5, but we lower it to 0.2 for easier triggering during testing
                        if score > 0.20:
                            log.info(f"WakeEngine: Wake word detected! ({mdl}: {score:.2f})")
                            if self.on_wake_detected:
                                self.on_wake_detected()
                            time.sleep(2)
                            
                except OSError as e:
                    log.error(f"WakeEngine read error: {e}")
                    time.sleep(0.1)
                        
        except Exception as e:
            log.error(f"WakeEngine failed to start: {e}")