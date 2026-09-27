import asyncio
import threading
import sys
import os
import time
import atexit

from utils.logger import log

from core.config import Config
from core.settings import SettingsManager
from backend.embodiment.events import event_bus
from backend.embodiment.models import OmnixEvent, EventTypes
from backend.embodiment.controller import embodiment_controller

# Avatar subsystems
from avatar.bridge import AvatarBridge
from avatar.process_manager import avatar_process_manager

# Voice subsystems
import sys
ui_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ui'))
if ui_path not in sys.path:
    sys.path.append(ui_path)

from backend.senses.voice_service import VoiceService

# System Tray
from tray_manager import TrayManager

class OmnixRuntime:
    """Canonical owner of the Omnix application lifecycle."""
    def __init__(self):
        self._loop = None
        self._loop_thread = None
        self._is_running = False

        self.voice_service = None
        self.avatar_bridge = None
        self.tray = None

    def initialize(self):
        log.info("Initializing OmnixRuntime...")
        Config.ensure_dirs()
        SettingsManager.load()

        # Start the Event Loop inside a background thread (so main thread can keep UI alive or block)
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True, name="OmnixEventLoop")
        self._loop_thread.start()

        # Wait until loop is actually running
        while not self._loop.is_running():
            time.sleep(0.01)

        self._init_brain()
        self._init_voice()
        self._init_avatar()
        self._init_tray()
        
        # Self-subscribe to shutdown events if we want
        event_bus.publish(OmnixEvent(EventTypes.OMNIX_READY))
        
        atexit.register(self.shutdown)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _init_brain(self):
        log.info("Initializing brain/models...")
        try:
            from brain.llm_provider import initialize_models
            initialize_models()
        except Exception as e:
            log.warning(f"Brain initialization error (may be offline): {e}")

    def _init_voice(self):
        self.voice_service = VoiceService(self._loop)
        self.voice_service.start()

    def _init_avatar(self):
        log.info("Initializing Avatar system...")
        self.avatar_bridge = AvatarBridge()
        # Start bridge server asynchronously
        asyncio.run_coroutine_threadsafe(self.avatar_bridge.start(), self._loop)
        # Start renderer process
        avatar_process_manager.start()

    def _init_tray(self):
        log.info("Initializing System Tray...")
        self.tray = TrayManager(
            on_wake=self._on_tray_wake,
            on_sleep=self._on_tray_sleep,
            on_open=self._on_tray_open,
            on_quit=self.shutdown
        )
        self.tray.start()

    def _on_tray_wake(self):
        if self.voice_service:
            self.voice_service.set_awake(True)

    def _on_tray_sleep(self):
        if self.voice_service:
            self.voice_service.set_awake(False)

    def _on_tray_open(self):
        # We need a way to restore the Flet window. Flet might be hidden.
        # But we shouldn't rely on it. Just emit an event.
        event_bus.publish(OmnixEvent(EventTypes.TEST_EVENT, payload={"action": "show_ui"}))

    def shutdown(self):
        if not self._is_running:
            return
        self._is_running = False
        log.info("Shutting down OmnixRuntime...")
        
        # Stop Voice
        if self.voice_service:
            self.voice_service.stop()

        # Stop Avatar
        avatar_process_manager.stop()
        if self.avatar_bridge and self._loop:
            asyncio.run_coroutine_threadsafe(self.avatar_bridge.stop(), self._loop)

        # Stop Tray
        if self.tray:
            self.tray.stop()
            
        # Stop loop
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            
        log.info("Omnix shutdown complete.")

    def run_forever(self):
        self._is_running = True
        try:
            while self._is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

omnix_runtime = OmnixRuntime()
