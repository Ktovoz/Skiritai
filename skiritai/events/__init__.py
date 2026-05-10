"""Async event bus for decoupled event publishing and subscription.

Supports:
- In-memory pub-sub for real-time subscribers
- Optional file-based persistence for replay after reconnection
- History buffer for recently disconnected subscribers to catch up
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from skiritai.logger import logger


@dataclass
class Event:
    """A single event."""
    type: str                    # e.g. "step_started", "step_completed", "log_message"
    execution_id: str            # Which execution this belongs to
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "execution_id": self.execution_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        return cls(
            type=d["type"],
            execution_id=d["execution_id"],
            data=d.get("data", {}),
            timestamp=d.get("timestamp", 0),
        )


# Type alias for event handlers
EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Async pub-sub event bus with optional persistence and history buffer.

    Components publish events. Subscribers receive events matching their
    registered event types. Used to decouple execution logic from
    WebSocket transport.

    Features:
    - In-memory history buffer per execution_id (for catch-up after reconnect)
    - Optional file persistence (append-only JSONL log per execution)
    """

    # Maximum number of events to keep per execution in the history buffer
    DEFAULT_HISTORY_SIZE = 500

    def __init__(self, history_size: int = DEFAULT_HISTORY_SIZE) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._all_handlers: list[EventHandler] = []
        self._history_size = history_size
        # Per-execution event history (for catch-up after reconnection)
        self._history: dict[str, list[Event]] = {}
        # Optional persistence directory (set via enable_persistence)
        self._persist_dir: Path | None = None

    def enable_persistence(self, persist_dir: Path) -> None:
        """Enable file-based event persistence.

        Events are appended as JSONL to ``<persist_dir>/<execution_id>.jsonl``.
        Call this once at startup.
        """
        self._persist_dir = persist_dir
        persist_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[EventBus] Persistence enabled: {persist_dir}")

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

    def subscribed(self, handler: EventHandler, event_types: list[str] | None = None):
        """Context manager for temporary subscriptions — auto-unsubscribes on exit.

        Usage:
            async with event_bus.subscribed(my_handler):
                ...  # handler is active
            # handler is automatically removed here
        """
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            self.subscribe(handler, event_types)
            try:
                yield
            finally:
                self.unsubscribe(handler)
        return _ctx()

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers.

        Also stores the event in the history buffer and persists to disk
        if persistence is enabled.
        """
        # Store in history buffer
        self._append_history(event)

        # Persist to disk (best-effort, non-blocking)
        self._persist_event(event)

        # Deliver to in-memory subscribers
        handlers = list(self._all_handlers)
        handlers.extend(self._handlers.get(event.type, []))

        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.error(
                    f"[EventBus] Handler error for event '{event.type}': {handler}",
                    exc_info=True,
                )

    def get_history(self, execution_id: str) -> list[Event]:
        """Get the event history for a given execution.

        Returns a copy of the buffered events, newest last.
        Useful for catch-up after WebSocket reconnection.
        """
        return list(self._history.get(execution_id, []))

    def load_persisted_events(self, execution_id: str) -> list[Event]:
        """Load persisted events for an execution from disk.

        Returns events in chronological order. Empty list if no file exists.
        """
        if self._persist_dir is None:
            return []

        path = self._persist_dir / f"{execution_id}.jsonl"
        if not path.exists():
            return []

        events = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                events.append(Event.from_dict(json.loads(line)))
        except Exception as e:
            logger.warning(f"[EventBus] Error loading persisted events: {e}")

        return events

    def clear_history(self, execution_id: str) -> None:
        """Clear the in-memory history for an execution."""
        self._history.pop(execution_id, None)

    # ---- Internal helpers ----

    def _append_history(self, event: Event) -> None:
        """Append an event to the per-execution history buffer."""
        eid = event.execution_id
        buf = self._history.setdefault(eid, [])
        buf.append(event)
        # Trim oldest events if buffer exceeds max size
        if len(buf) > self._history_size:
            self._history[eid] = buf[-self._history_size:]

    def _persist_event(self, event: Event) -> None:
        """Append event to JSONL file (best-effort, fire-and-forget)."""
        if self._persist_dir is None:
            return

        try:
            path = self._persist_dir / f"{event.execution_id}.jsonl"
            line = json.dumps(event.to_dict(), ensure_ascii=False, default=str)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.debug(f"[EventBus] Persist failed: {e}")


# Module-level singleton
event_bus = EventBus()
