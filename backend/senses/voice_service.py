import threading
import sys
import os
import asyncio

from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes
from utils.logger import log

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ui')))
from wake_engine import WakeEngine
from command_listener import CommandListener
from backend.brain.orchestrator import process_command

class VoiceService:
    def __init__(self, loop):
        self._loop = loop
        self.wake_engine = None
        self.command_listener = None
        self.is_awake = False
        self.is_processing = False

    def start(self):
        log.info("Starting VoiceService...")
        event_bus.subscribe(EventTypes.USER_SPEECH_RECOGNIZED, self._on_bus_speech_recognized)
        self.wake_engine = WakeEngine(on_wake_detected=self._on_wake_detected)
        self.wake_engine.start()
        
        self.command_listener = CommandListener(
            on_command=self._on_voice_command,
            on_silence=self._on_voice_silence,
            on_speech_start=self._on_voice_speech_start,
            on_speech_end=self._on_voice_speech_end,
        )

    def stop(self):
        if self.wake_engine:
            self.wake_engine.stop()
        if self.command_listener:
            self.command_listener.stop_listening()

    def set_awake(self, awake: bool):
        if self.is_awake == awake:
            return
        self.is_awake = awake
        if awake:
            event_bus.publish(OmnixEvent(event_type=EventTypes.WAKE_STARTED))
            event_bus.publish(OmnixEvent(event_type=EventTypes.WOKE))
            self.wake_engine.set_awake(True)
            self.command_listener.start_listening()
        else:
            event_bus.publish(OmnixEvent(event_type=EventTypes.SLEEP_STARTED))
            event_bus.publish(OmnixEvent(event_type=EventTypes.SLEPT))
            self.wake_engine.set_awake(False)
            self.command_listener.stop_listening()

    def _on_wake_detected(self):
        self.set_awake(True)

    def _on_voice_silence(self):
        self.set_awake(False)

    def _on_voice_speech_start(self):
        event_bus.publish(OmnixEvent(event_type=EventTypes.USER_SPEECH_STARTED))

    def _on_voice_speech_end(self):
        event_bus.publish(OmnixEvent(event_type=EventTypes.USER_SPEECH_ENDED))

    def _on_bus_speech_recognized(self, event: OmnixEvent):
        text = event.payload.get("text")
        if text:
            asyncio.run_coroutine_threadsafe(self._process_request(text), self._loop)

    def _on_voice_command(self, text: str):
        # The wake engine just emits the event now, allowing UI or voice to funnel into one place
        event_bus.publish(OmnixEvent(event_type=EventTypes.USER_SPEECH_RECOGNIZED, payload={"text": text}))

    async def _process_request(self, text: str):
        if self.is_processing:
            log.warning("VoiceService: A task is already running. Ignoring new voice command.")
            return
        
        self.is_processing = True
        if self.command_listener:
            self.command_listener.set_processing(True)

        try:
            await process_command(text, self._on_response)
        except Exception as e:
            import traceback
            log.error(f"VoiceService process_command crashed: {e}\n{traceback.format_exc()}")
        finally:
            self.is_processing = False
            if self.command_listener:
                self.command_listener.set_processing(False)

    def _on_response(self, text: str, emotion: str, audio_b64: str):
        # Notify Flet to show text (don't send audio to Flet)
        event_bus.publish(OmnixEvent(EventTypes.TEST_EVENT, payload={"action": "chat_response", "text": text, "emotion": emotion, "audio_b64": ""}))
        if audio_b64:
            from ui.tts_player import play_audio_b64
            play_audio_b64(audio_b64)
