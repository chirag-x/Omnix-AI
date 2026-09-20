import threading
import pyaudio
import wave
import io
from utils.logger import log

class AudioRecorder:
    """Records audio from mic and returns WAV bytes when stopped."""
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024

    def __init__(self):
        self._audio = pyaudio.PyAudio()
        self._stream = None
        self._frames = []
        self._recording = False

    @property
    def is_recording(self):
        return self._recording

    def start(self):
        self._frames = []
        self._recording = True
        self._stream = self._audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        log.info("AudioRecorder: Recording started.")
        threading.Thread(target=self._record_loop, daemon=True).start()

    def _record_loop(self):
        while self._recording:
            try:
                data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                self._frames.append(data)
            except Exception as e:
                log.error(f"AudioRecorder error: {e}")
                break

    def stop(self) -> bytes:
        self._recording = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        log.info("AudioRecorder: Recording stopped.")
        return self._to_wav_bytes()

    def _to_wav_bytes(self) -> bytes:
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self._audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self._frames))
        return wav_io.getvalue()
