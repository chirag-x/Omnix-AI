import threading
from typing import Callable, Dict, List
from .models import OmnixEvent
from utils.logger import log

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[OmnixEvent], None]]] = {}
        self._all_events_subscribers: List[Callable[[OmnixEvent], None]] = []
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, callback: Callable[[OmnixEvent], None]):
        with self._lock:
            if event_type == "*":
                self._all_events_subscribers.append(callback)
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[OmnixEvent], None]):
        with self._lock:
            if event_type == "*":
                if callback in self._all_events_subscribers:
                    self._all_events_subscribers.remove(callback)
            else:
                if event_type in self._subscribers:
                    if callback in self._subscribers[event_type]:
                        self._subscribers[event_type].remove(callback)

    def publish(self, event: OmnixEvent):
        handlers = []
        with self._lock:
            if event.event_type in self._subscribers:
                handlers.extend(self._subscribers[event.event_type])
            handlers.extend(self._all_events_subscribers)
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                log.error(f"EventBus: Subscriber {handler} failed handling event {event.event_type}: {e}")

# Global singleton event bus
event_bus = EventBus()
