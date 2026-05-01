"""Async event bus for decoupled event publishing and subscription."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class Event:
    """A single event."""
    type: str                    # e.g. "step_started", "step_completed", "log_message"
    execution_id: str            # Which execution this belongs to
    data: dict[str, Any] = field(default_factory=dict)


# Type alias for event handlers
EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Async pub-sub event bus.

    Components publish events. Subscribers receive events matching their
    registered event types. Used to decouple execution logic from
    WebSocket transport.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._all_handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler, event_types: list[str] | None = None) -> None:
        """Subscribe to specific event types, or all events if None."""
        if event_types is None:
            self._all_handlers.append(handler)
        else:
            for et in event_types:
                self._handlers.setdefault(et, []).append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        """Remove a handler from all subscriptions."""
        for handlers in self._handlers.values():
            if handler in handlers:
                handlers.remove(handler)
        if handler in self._all_handlers:
            self._all_handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers."""
        handlers = list(self._all_handlers)
        handlers.extend(self._handlers.get(event.type, []))

        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                pass


# Module-level singleton
event_bus = EventBus()
