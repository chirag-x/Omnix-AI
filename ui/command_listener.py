import threading
import io
import speech_recognition as sr
from utils.logger import log
from core.settings import SettingsManager


class CommandListener:
    """
    Continuously listens for voice commands while Omnix is awake.

    Lifecycle:
        - start_listening()  ← called when wake word is detected
        - Background listener captures audio phrases
        - Each phrase is transcribed; non-empty → on_command(text)
        - on_speech_start fires when audio arrives (for LISTENING UI state)
        - Silence timer resets on every detected phrase
        - When silence timer fires → on_silence() → Omnix goes to sleep
        - stop_listening()   ← called when Omnix sleeps

    TTS Guard:
        All audio is discarded while TTS is playing so Omnix
        never hears its own voice as a user command.
    """

    # Recognizer tuning — optimised for desktop use near a mic
    _ENERGY_THRESHOLD = 150
    _DYNAMIC_ENERGY_RATIO = 1.2
    _PAUSE_THRESHOLD = 0.5       # Silence before treating phrase as complete
    _PHRASE_THRESHOLD = 0.4      # Minimum duration to trigger capture
    _PHRASE_TIME_LIMIT = 8       # Max seconds captured per phrase
    _AMBIENT_CALIBRATION_S = 0.5

    def __init__(
        self,
        on_command,
        on_silence,
        on_speech_start=None,
        on_speech_end=None,
    ):
        """
        Args:
            on_command:    Callable(text: str) — fired when a transcript is ready.
            on_silence:    Callable() — fired after silence_timeout with no speech.
            on_speech_start: Optional Callable() — fired when audio arrives
                              (before transcription, for LISTENING UI state).
            on_speech_end:   Optional Callable() — fired after transcription
                              completes with no usable text (back to IDLE state).
        """
        self._model = None
        self._on_command = on_command
        self._on_silence = on_silence
        self._on_speech_start = on_speech_start
        self._on_speech_end = on_speech_end

        self._running = False
        self._is_processing = False  # True while a command task is executing
        self._should_pulse = False

        self._silence_timer: threading.Timer | None = None
        self._stop_listening_func = None
        self._mic: sr.Microphone | None = None

        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = self._ENERGY_THRESHOLD
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.dynamic_energy_ratio = self._DYNAMIC_ENERGY_RATIO
        self._recognizer.pause_threshold = self._PAUSE_THRESHOLD
        self._recognizer.phrase_threshold = self._PHRASE_THRESHOLD

    # ─── Public API ────────────────────────────────────────────────────────────

    def start_listening(self):
        """Start continuous background listening. Safe to call from any thread."""
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._init_listener, daemon=True).start()
        self._reset_silence_timer()
        log.info("CommandListener: Continuous listening started.")

    def stop_listening(self):
        """Stop the background listener and cancel silence timer."""
        self._running = False
        self._cancel_silence_timer()
        if self._stop_listening_func:
            try:
                self._stop_listening_func(wait_for_stop=False)
            except Exception:
                pass
            self._stop_listening_func = None
        log.info("CommandListener: Stopped.")

    def set_processing(self, is_processing: bool):
        """
        Notify the listener whether a command is currently being executed.
        While processing:
          - silence timer is paused (don't sleep mid-task)
          - new commands from audio are ignored
        After processing ends, silence timer restarts.
        """
        self._is_processing = is_processing
        if not is_processing:
            self._reset_silence_timer()

    # ─── Background listener init ──────────────────────────────────────────────

    def _init_listener(self):
        try:
            stt_device = SettingsManager.get("stt_device", "auto")
            if stt_device == "cloud_groq":
                self._model = "cloud_groq"
                log.info("Speech-to-Text Engine actively using Groq Cloud API.")
            elif self._model is None:
                import os
                from faster_whisper import WhisperModel
                from core.config import Config
                model_name = SettingsManager.get("stt_model", "medium")
                base_dir = SettingsManager.get("default_download_location", "E:/Coding/Omnix/Omnix/Default_Downloads")
                local_path = os.path.join(base_dir, "model", model_name)
                
                if not os.path.exists(local_path):
                    log.error(f"CommandListener ERROR: Model '{model_name}' not found in {local_path}. Please download the model first from the Settings menu.")
                    return
                    
                log.info(f"Speech-to-Text Engine actively using model: [{model_name}] (Loaded from: {local_path})")
                compute_t = "int8" if stt_device == "cpu" else "int8_float16"
                
                self._model = WhisperModel(
                    local_path,
                    device=stt_device,
                    compute_type=compute_t,
                    download_root=Config.get_wakeword_models_dir()
                )
        except Exception as e:
            log.error(f"CommandListener: Failed to load STT model: {e}")
            return

        try:
            mic_name = SettingsManager.get("audio_input_device", "Default System Microphone")
            mic_idx = None
            if mic_name and mic_name != "Default System Microphone":
                import pyaudio
                pa = pyaudio.PyAudio()
                try:
                    for i in range(pa.get_device_count()):
                        d = pa.get_device_info_by_index(i)
                        name = d.get('name', '')
                        if (mic_name in name or name in mic_name) and d.get('maxInputChannels', 0) > 0:
                            mic_idx = i
                            log.info(f"CommandListener: Selected Microphone [{i}]: {name}")
                            break
                finally:
                    pa.terminate()
            
            self._mic = sr.Microphone(device_index=mic_idx)
            with self._mic as source:
                log.info("CommandListener: Calibrating ambient noise...")
                self._recognizer.adjust_for_ambient_noise(
                    source, duration=self._AMBIENT_CALIBRATION_S
                )
            log.info("CommandListener: Ready — listening for commands.")
            self._stop_listening_func = self._recognizer.listen_in_background(
                self._mic,
                callback=self._audio_callback,
                phrase_time_limit=self._PHRASE_TIME_LIMIT,
            )
        except Exception as e:
            log.error(f"CommandListener: Failed to start mic listener: {e}")

    # ─── Audio callback (runs in SR background thread) ─────────────────────────

    def _audio_callback(self, recognizer, audio):
        """Called by SpeechRecognition for every captured audio phrase."""
        if not self._running:
            return

        # ── TTS guard: never hear own voice ────────────────────────────────────
        try:
            from tts_player import recently_played
            if recently_played(buffer_seconds=2.0):
                log.debug("CommandListener: Ignoring audio — TTS was recently playing.")
                return
        except Exception:
            pass  # If tts_player import fails, continue anyway

        # ── Notify UI: speech arrived (for LISTENING orb state) ────────────────
        if self._on_speech_start:
            try:
                self._on_speech_start()
            except Exception:
                pass

        # ── Transcribe ─────────────────────────────────────────────────────────
        try:
            if not self._model: return
            
            if self._model == "cloud_groq":
                import requests
                api_key = SettingsManager.get("groq_api_key", "")
                stt_model = SettingsManager.get("groq_stt_model", "whisper-large-v3-turbo")
                if not api_key:
                    log.error("CommandListener: Groq API Key is missing!")
                    self._notify_speech_end()
                    return
                
                # Send to Groq
                wav_data = audio.get_wav_data()
                files = {"file": ("audio.wav", wav_data, "audio/wav")}
                data = {"model": stt_model, "language": "en"}
                headers = {"Authorization": f"Bearer {api_key}"}
                
                response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=10)
                if response.status_code == 200:
                    transcript = response.json().get("text", "").strip()
                else:
                    log.error(f"Groq API Error: {response.status_code} - {response.text}")
                    transcript = ""
            else:
                audio_io = io.BytesIO(audio.get_wav_data())
                segments, _ = self._model.transcribe(
                    audio_io,
                    beam_size=1,
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 400},
                )
                transcript = " ".join(s.text for s in segments).strip()
        except Exception as e:
            log.error(f"CommandListener: Transcription error: {e}")
            self._notify_speech_end()
            return

        # ── Route result ────────────────────────────────────────────────────────
        hallucinations = {"thank you.", "thank you", "thanks for watching.", "subscribe.", "subscribe", "you.", "you", "thanks.", "thanks"}
        if transcript and transcript.strip().lower() in hallucinations:
            log.debug(f"CommandListener: Ignored hallucination -> '{transcript}'")
            transcript = ""

        if transcript and len(transcript) > 2:
            log.info(f"CommandListener: Heard → '{transcript}'")
            # Reset silence timer — user is active
            self._reset_silence_timer()
            # Don't stack commands while one is running
            if not self._is_processing:
                try:
                    self._on_command(transcript)
                except Exception as e:
                    log.error(f"CommandListener: on_command error: {e}")
        else:
            # Empty or noise — go back to idle visual state
            self._notify_speech_end()

    def _notify_speech_end(self):
        if self._on_speech_end:
            try:
                self._on_speech_end()
            except Exception:
                pass

    # ─── Silence timer ─────────────────────────────────────────────────────────

    def _reset_silence_timer(self):
        """Cancel existing timer and start a fresh countdown."""
        self._cancel_silence_timer()

        if not self._running:
            return

        # Pause countdown while a task is executing
        if self._is_processing:
            return

        timeout = SettingsManager.get("sleep_timeout_seconds") or 45
        self._silence_timer = threading.Timer(timeout, self._on_silence_timeout)
        self._silence_timer.daemon = True
        self._silence_timer.start()

    def _cancel_silence_timer(self):
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None

    def _on_silence_timeout(self):
        if self._running and not self._is_processing:
            log.info("CommandListener: Silence timeout — signalling sleep.")
            try:
                self._on_silence()
            except Exception as e:
                log.error(f"CommandListener: on_silence error: {e}")
