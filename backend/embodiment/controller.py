import time
from typing import Optional
from .events import event_bus
from .models import OmnixEvent, EventTypes, EmbodimentSnapshot
from .state import OperationalState, Emotion, SpeechState
from utils.logger import log

class EmbodimentController:
    def __init__(self):
        self._state = OperationalState.SLEEPING
        self._emotion = Emotion.NEUTRAL
        self._speech_state = SpeechState.SILENT
        self._last_transition_time = time.time()
        self._current_task_id: Optional[str] = None
        self._subscribe_all()

    def _subscribe_all(self):
        event_bus.subscribe(EventTypes.OMNIX_BOOTING, self._on_booting)
        event_bus.subscribe(EventTypes.OMNIX_READY, self._on_ready)
        event_bus.subscribe(EventTypes.WAKE_STARTED, self._on_waking)
        event_bus.subscribe(EventTypes.WOKE, self._on_idle)
        event_bus.subscribe(EventTypes.SLEEP_STARTED, self._on_sleeping)
        event_bus.subscribe(EventTypes.SLEPT, self._on_sleeping)
        
        event_bus.subscribe(EventTypes.USER_SPEECH_STARTED, self._on_listening)
        event_bus.subscribe(EventTypes.THINKING_STARTED, self._on_thinking)
        event_bus.subscribe(EventTypes.TASK_STARTED, self._on_working)
        event_bus.subscribe(EventTypes.TASK_SUCCEEDED, self._on_success)
        event_bus.subscribe(EventTypes.TASK_FAILED, self._on_failure)
        event_bus.subscribe(EventTypes.TASK_INTERRUPTED, self._on_interrupted)
        event_bus.subscribe(EventTypes.ERROR_OCCURRED, self._on_error)
        
        event_bus.subscribe(EventTypes.TTS_GENERATION_STARTED, self._on_speech_preparing)
        event_bus.subscribe(EventTypes.TTS_PLAYBACK_STARTED, self._on_speech_started)
        event_bus.subscribe(EventTypes.TTS_PLAYBACK_FINISHED, self._on_speech_finished)
        
        event_bus.subscribe(EventTypes.EMOTION_CHANGED, self._on_emotion_changed)

    def _update_state(self, new_state: OperationalState, task_id: Optional[str] = None):
        if self._state != new_state:
            self._state = new_state
            self._last_transition_time = time.time()
        if task_id:
            self._current_task_id = task_id

    def _on_booting(self, event: OmnixEvent): self._update_state(OperationalState.BOOTING)
    def _on_ready(self, event: OmnixEvent): self._update_state(OperationalState.IDLE)
    def _on_waking(self, event: OmnixEvent): self._update_state(OperationalState.WAKING)
    def _on_idle(self, event: OmnixEvent): self._update_state(OperationalState.IDLE)
    def _on_sleeping(self, event: OmnixEvent): self._update_state(OperationalState.SLEEPING)
    
    def _on_listening(self, event: OmnixEvent): self._update_state(OperationalState.LISTENING)
    def _on_thinking(self, event: OmnixEvent):
        self._update_state(OperationalState.THINKING, event.correlation_id)
        
    def _on_working(self, event: OmnixEvent):
        self._update_state(OperationalState.WORKING, event.correlation_id)
        
    def _on_success(self, event: OmnixEvent):
        self._update_state(OperationalState.SUCCESS, event.correlation_id)
        self._update_state(OperationalState.IDLE) 

    def _on_failure(self, event: OmnixEvent):
        self._update_state(OperationalState.ERROR, event.correlation_id)
        self._update_state(OperationalState.IDLE)

    def _on_interrupted(self, event: OmnixEvent):
        self._update_state(OperationalState.INTERRUPTED, event.correlation_id)
        self._update_state(OperationalState.IDLE)
        
    def _on_error(self, event: OmnixEvent):
        self._update_state(OperationalState.ERROR)

    def _on_speech_preparing(self, event: OmnixEvent):
        self._speech_state = SpeechState.PREPARING
        
    def _on_speech_started(self, event: OmnixEvent):
        self._speech_state = SpeechState.SPEAKING
        
    def _on_speech_finished(self, event: OmnixEvent):
        self._speech_state = SpeechState.SILENT

    def _on_emotion_changed(self, event: OmnixEvent):
        raw_emotion = event.payload.get("emotion", "neutral")
        try:
            self._emotion = Emotion(raw_emotion.lower())
        except ValueError:
            log.warning(f"Unsupported emotion '{raw_emotion}', falling back to NEUTRAL")
            self._emotion = Emotion.NEUTRAL

    def get_snapshot(self) -> EmbodimentSnapshot:
        return EmbodimentSnapshot(
            operational_state=self._state,
            emotion=self._emotion,
            speech_state=self._speech_state,
            last_transition_time=self._last_transition_time,
            current_task_id=self._current_task_id
        )

# Global singleton controller
embodiment_controller = EmbodimentController()
