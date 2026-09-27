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
        # We can just listen to the same events the controller listens to, 
        # or we can poll the controller. Listening to events is more reactive.
        event_bus.subscribe("*", self._on_any_event)

    def _on_any_event(self, event: OmnixEvent):
        # We let the controller update first. 
        # (Event bus handlers run synchronously in order of subscription, 
        # or we can just read the latest state from the controller).
        # Actually, let's map states to OrbState.
        
        # OrbState mapping
        # LOADING = "loading"
        # SLEEPING = "sleeping"
        # AWAKE_IDLE = "awake_idle"
        # LISTENING = "listening"
        # THINKING = "thinking"
        # SPEAKING = "speaking"
        # ERROR = "error"

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
            orb_state = "thinking" # map working to thinking visually for now
        elif snapshot.operational_state == OperationalState.SUCCESS:
            orb_state = "awake_idle"
        elif snapshot.operational_state == OperationalState.ERROR:
            orb_state = "error"
        elif snapshot.operational_state == OperationalState.INTERRUPTED:
            orb_state = "awake_idle"

        # Speech state overrides
        if snapshot.speech_state == SpeechState.SPEAKING:
            orb_state = "speaking"

        emotion_str = snapshot.emotion.value
        
        # We don't want to spam updates, so we only update if it changed
        # or if the event is a specific UI-triggering event.
        try:
            # We call the existing method
            self.app._set_orb_state(orb_state, emotion_str)
        except Exception as e:
            log.error(f"FletUIAdapter failed to update UI: {e}")

