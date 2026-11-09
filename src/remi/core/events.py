"""Event bus pattern for decoupled pub/sub events across the assistant suite."""
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class Event:
    """Base event payload."""
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventBus:
    """Thread-safe event bus for publishing and subscribing to system events."""

    _instance: "EventBus | None" = None
    _lock = threading.Lock()

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._sub_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EventBus":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        with self._sub_lock:
            self._subscribers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        with self._sub_lock:
            if event_name in self._subscribers and handler in self._subscribers[event_name]:
                self._subscribers[event_name].remove(handler)

    def publish(self, event_name: str, data: dict[str, Any] | None = None) -> Event:
        evt = Event(name=event_name, data=data or {})
        handlers: list[Callable[[Event], None]] = []
        with self._sub_lock:
            handlers.extend(self._subscribers.get(event_name, []))
            handlers.extend(self._subscribers.get("*", []))  # Wildcard subscribers

        for h in handlers:
            try:
                h(evt)
            except Exception:
                pass  # Event handlers must never crash the publisher
        return evt
