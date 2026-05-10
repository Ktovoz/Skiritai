"""Functional tests for EventBus — no browser/LLM required."""
from __future__ import annotations

import asyncio

import pytest


class TestEventBus:
    """Test event bus pub-sub, error handling, and unsubscription."""

    def test_subscribe_and_publish(self):
        from skiritai.events import Event, EventBus

        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(handler, event_types=["test_type"])
        asyncio.run(bus.publish(Event(type="test_type", execution_id="e1", data={"key": "val"})))

        assert len(received) == 1
        assert received[0].type == "test_type"
        assert received[0].execution_id == "e1"
        assert received[0].data["key"] == "val"

    def test_all_handler_receives_all_events(self):
        from skiritai.events import Event, EventBus

        bus = EventBus()
        received: list[str] = []

        async def handler(event: Event):
            received.append(event.type)

        bus.subscribe(handler)  # no filter = all events
        asyncio.run(bus.publish(Event(type="foo", execution_id="e1")))
        asyncio.run(bus.publish(Event(type="bar", execution_id="e1")))

        assert received == ["foo", "bar"]

    def test_unsubscribe_removes_handler(self):
        from skiritai.events import Event, EventBus

        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(handler, event_types=["t1"])
        bus.unsubscribe(handler)
        asyncio.run(bus.publish(Event(type="t1", execution_id="e1")))

        assert len(received) == 0

    def test_handler_error_is_logged_not_raised(self):
        from skiritai.events import Event, EventBus

        bus = EventBus()

        async def failing_handler(event: Event):
            raise RuntimeError("boom")

        bus.subscribe(failing_handler, event_types=["test"])
        # Should not raise
        asyncio.run(bus.publish(Event(type="test", execution_id="e1")))
