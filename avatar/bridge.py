import asyncio
import websockets
import json
from .protocol import AvatarMessage, MessageTypes
from backend.embodiment.events import event_bus
from backend.embodiment.models import EventTypes, OmnixEvent
from backend.embodiment.controller import embodiment_controller
from core.settings import SettingsManager
from utils.logger import log

class AvatarBridge:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = SettingsManager.get("avatar_renderer_port", 21212)
        self.active_connections = set()
        self._server = None
        self._loop = None
        self._subscribe_embodiment()

    def _subscribe_embodiment(self):
        event_bus.subscribe("*", self._on_any_event)

    def _on_any_event(self, event: OmnixEvent):
        relevant_events = {
            EventTypes.OMNIX_READY, EventTypes.WAKE_STARTED, EventTypes.WOKE,
            EventTypes.SLEEP_STARTED, EventTypes.SLEPT,
            EventTypes.USER_SPEECH_STARTED, EventTypes.USER_SPEECH_ENDED,
            EventTypes.THINKING_STARTED, EventTypes.THINKING_ENDED,
            EventTypes.TASK_STARTED, EventTypes.TASK_SUCCEEDED, EventTypes.TASK_FAILED,
            EventTypes.TASK_INTERRUPTED, EventTypes.EMOTION_CHANGED,
            EventTypes.TTS_PLAYBACK_STARTED, EventTypes.TTS_PLAYBACK_FINISHED
        }
        if event.event_type in relevant_events:
            self._broadcast_snapshot()

    def _broadcast_snapshot(self):
        snapshot = embodiment_controller.get_snapshot()
        msg = AvatarMessage(
            type=MessageTypes.STATE,
            payload={
                "operational_state": snapshot.operational_state.value,
                "emotion": snapshot.emotion.value,
                "speech_state": snapshot.speech_state.value
            }
        )
        self.broadcast(msg)

    async def _handler(self, websocket):
        log.info("Avatar renderer connected.")
        self.active_connections.add(websocket)
        try:
            self._broadcast_snapshot()
            async for message in websocket:
                msg = AvatarMessage.from_json(message)
                if msg.type == MessageTypes.READY:
                    log.info("Avatar renderer reported READY.")
                    self._broadcast_snapshot()
        except websockets.exceptions.ConnectionClosed:
            log.info("Avatar renderer disconnected.")
        except Exception as e:
            log.error(f"Avatar bridge error: {e}")
        finally:
            self.active_connections.discard(websocket)

    def broadcast(self, message: AvatarMessage):
        if not self.active_connections or not self._loop:
            return
        data = message.to_json()
        for conn in list(self.active_connections):
            try:
                asyncio.run_coroutine_threadsafe(conn.send(data), self._loop)
            except Exception:
                pass

    async def start(self):
        self._loop = asyncio.get_running_loop()
        log.info(f"Starting Avatar Bridge on ws://{self.host}:{self.port}")
        self._server = await websockets.serve(self._handler, self.host, self.port)

    async def stop(self):
        self.broadcast(AvatarMessage(type=MessageTypes.SHUTDOWN))
        if self._server:
            self._server.close()
            await self._server.wait_closed()
