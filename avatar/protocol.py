import json
from dataclasses import dataclass, field

PROTOCOL_VERSION = 1

@dataclass
class AvatarMessage:
    type: str
    payload: dict = field(default_factory=dict)
    protocol: int = PROTOCOL_VERSION

    def to_json(self):
        return json.dumps({
            "protocol": self.protocol,
            "type": self.type,
            "payload": self.payload
        })

    @classmethod
    def from_json(cls, data_str: str):
        try:
            data = json.loads(data_str)
            return cls(
                type=data.get("type", "unknown"),
                payload=data.get("payload", {}),
                protocol=data.get("protocol", PROTOCOL_VERSION)
            )
        except json.JSONDecodeError:
            return cls(type="error", payload={"message": "Invalid JSON"})

class MessageTypes:
    HELLO = "renderer.hello"
    READY = "renderer.ready"
    SHUTDOWN = "renderer.shutdown"
    
    SHOW = "avatar.show"
    HIDE = "avatar.hide"
    STATE = "avatar.state"
    TRANSFORM = "avatar.transform"
    TEST = "avatar.test"
    
    MODEL_LOAD = "avatar.model.load"
    MODEL_LOADED = "avatar.model.loaded"
    MODEL_ERROR = "avatar.model.error"
