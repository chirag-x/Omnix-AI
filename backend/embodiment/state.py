from enum import Enum

class OperationalState(Enum):
    BOOTING = "booting"
    SLEEPING = "sleeping"
    WAKING = "waking"
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    SUCCESS = "success"
    ERROR = "error"
    INTERRUPTED = "interrupted"

class Emotion(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    CONFUSED = "confused"
    ANGRY = "angry"
    
class SpeechState(Enum):
    SILENT = "silent"
    PREPARING = "preparing"
    SPEAKING = "speaking"
