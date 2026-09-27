from dataclasses import dataclass, field
from typing import Any, Optional
import time
from .state import OperationalState, Emotion, SpeechState

@dataclass
class EmbodimentSnapshot:
    operational_state: OperationalState
    emotion: Emotion
    speech_state: SpeechState
    last_transition_time: float
    current_task_id: Optional[str] = None
    
@dataclass
class OmnixEvent:
    event_type: str
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    payload: dict = field(default_factory=dict)
    correlation_id: Optional[str] = None

class EventTypes:
    OMNIX_BOOTING = "OMNIX_BOOTING"
    OMNIX_READY = "OMNIX_READY"
    WAKE_STARTED = "WAKE_STARTED"
    WOKE = "WOKE"
    SLEEP_STARTED = "SLEEP_STARTED"
    SLEPT = "SLEPT"
    USER_SPEECH_STARTED = "USER_SPEECH_STARTED"
    USER_SPEECH_RECOGNIZED = "USER_SPEECH_RECOGNIZED"
    USER_SPEECH_ENDED = "USER_SPEECH_ENDED"
    THINKING_STARTED = "THINKING_STARTED"
    THINKING_ENDED = "THINKING_ENDED"
    TASK_STARTED = "TASK_STARTED"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_SUCCEEDED = "TASK_SUCCEEDED"
    TASK_FAILED = "TASK_FAILED"
    TASK_INTERRUPTED = "TASK_INTERRUPTED"
    RESPONSE_STARTED = "RESPONSE_STARTED"
    RESPONSE_COMPLETED = "RESPONSE_COMPLETED"
    EMOTION_CHANGED = "EMOTION_CHANGED"
    TTS_GENERATION_STARTED = "TTS_GENERATION_STARTED"
    TTS_GENERATION_COMPLETED = "TTS_GENERATION_COMPLETED"
    TTS_PLAYBACK_STARTED = "TTS_PLAYBACK_STARTED"
    TTS_PLAYBACK_FINISHED = "TTS_PLAYBACK_FINISHED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
