import threading
import time
from dataclasses import dataclass, field


@dataclass
class Event:
    project_id: str
    event_type: str
    entity_id: str
    timestamp: float = field(default_factory=time.time)


class EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._events: list[Event] = []

    def publish(self, project_id: str, event_type: str, entity_id: str):
        with self._lock:
            self._events.append(Event(project_id=project_id, event_type=event_type, entity_id=entity_id))
            self._cleanup()

    def get_since(self, project_id: str, since: float) -> list[Event]:
        with self._lock:
            return [e for e in self._events if e.project_id == project_id and e.timestamp > since]

    def _cleanup(self):
        cutoff = time.time() - 300  # 5 minutes
        self._events = [e for e in self._events if e.timestamp > cutoff]


event_bus = EventBus()
