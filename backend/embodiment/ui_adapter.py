from typing import Callable, Any
from .events import event_bus
from .models import EventTypes, OmnixEvent
from .controller import embodiment_controller
from .state import OperationalState, SpeechState, Emotion
from utils.logger import log

class FletUIAdapter:
    """Adapts Omnix embodiment events to the existing Flet UI without breaking it."""
    def __init__(self, app: Any):
        self.app = app
        self._subscribe()

    def _subscribe(self):
        event_bus.subscribe("*", self._on_any_event)

    def _on_any_event(self, event: OmnixEvent):
        try:
            snapshot = embodiment_controller.get_snapshot()
            orb_state = "awake_idle" # default fallback
            
            if snapshot.operational_state == OperationalState.BOOTING:
                orb_state = "loading"
            elif snapshot.operational_state == OperationalState.SLEEPING:
                orb_state = "sleeping"
            elif snapshot.operational_state == OperationalState.WAKING:
                orb_state = "awake_idle"
            elif snapshot.operational_state == OperationalState.IDLE:
                orb_state = "awake_idle"
            elif snapshot.operational_state == OperationalState.LISTENING:
                orb_state = "listening"
            elif snapshot.operational_state == OperationalState.THINKING:
                orb_state = "thinking"
            elif snapshot.operational_state == OperationalState.WORKING:
                orb_state = "thinking"
            elif snapshot.operational_state == OperationalState.SUCCESS:
                orb_state = "awake_idle"
            elif snapshot.operational_state == OperationalState.ERROR:
                orb_state = "error"
            elif snapshot.operational_state == OperationalState.INTERRUPTED:
                orb_state = "awake_idle"

            if snapshot.speech_state == SpeechState.SPEAKING:
                orb_state = "speaking"

            emotion_str = snapshot.emotion.value
            
            self.app._set_orb_state(orb_state, emotion_str)
            
            # Synchronize wake state
            if snapshot.operational_state in [OperationalState.WAKING, OperationalState.IDLE]:
                if not getattr(self.app, 'is_awake', False):
                    self.app.is_awake = True
                    self.app._set_awake_ui(True)
            elif snapshot.operational_state == OperationalState.SLEEPING:
                if getattr(self.app, 'is_awake', True):
                    self.app.is_awake = False
                    self.app._set_awake_ui(False)

            # Handle explicit test events meant for UI
            if event.event_type == EventTypes.TEST_EVENT:
                action = event.payload.get('action')
                if action == 'chat_response':
                    text = event.payload.get('text', '')
                    emotion = event.payload.get('emotion', 'neutral')
                    audio_b64 = event.payload.get('audio_b64', '')
                    self.app._on_response(text, emotion, audio_b64)
                elif action == 'show_ui':
                    self.app._restore_window()

        except Exception as e:
            log.error(f"FletUIAdapter failed to update UI: {e}")
