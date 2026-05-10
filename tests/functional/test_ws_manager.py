"""Functional tests for WSManager — no browser/LLM required."""
from __future__ import annotations

from skiritai.events import Event
from skiritai.web.ws_manager import WSManager


class TestWSManager:
    """Test WS manager message conversion and error propagation."""

    def test_step_started_message(self):
        mgr = WSManager()
        event = Event(type="step_started", execution_id="e1", data={"step_id": "login"})
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["type"] == "node_status"
        assert msg["node_id"] == "login"
        assert msg["status"] == "running"

    def test_step_completed_message_includes_mode_and_summary(self):
        mgr = WSManager()
        event = Event(
            type="step_completed",
            execution_id="e1",
            data={"step_id": "login", "mode": "replay", "summary": "done"},
        )
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["status"] == "success"
        assert msg["data"]["mode"] == "replay"
        assert msg["data"]["summary"] == "done"

    def test_step_failed_message_includes_error(self):
        mgr = WSManager()
        event = Event(
            type="step_failed",
            execution_id="e1",
            data={"step_id": "login", "error": "timeout", "summary": "failed"},
        )
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["status"] == "failed"
        assert msg["data"]["error"] == "timeout"
        assert msg["data"]["summary"] == "failed"

    def test_tool_called_message(self):
        mgr = WSManager()
        event = Event(
            type="tool_called",
            execution_id="e1",
            data={"tool_name": "click", "tool_args": {"selector": "#btn"}},
        )
        msg = mgr._event_to_ws_message(event)

        assert msg is not None
        assert msg["type"] == "log"
        assert "click" in msg["data"]["message"]

    def test_execution_started_and_completed(self):
        mgr = WSManager()

        started = mgr._event_to_ws_message(
            Event(type="execution_started", execution_id="e1", data={})
        )
        assert started["status"] == "running"

        completed = mgr._event_to_ws_message(
            Event(
                type="execution_completed",
                execution_id="e1",
                data={"report": {"status": "completed", "case_name": "test"}},
            )
        )
        assert completed["status"] == "completed"
        assert completed["data"]["report"]["case_name"] == "test"

    def test_unknown_event_type_returns_none(self):
        mgr = WSManager()
        msg = mgr._event_to_ws_message(Event(type="unknown", execution_id="e1"))
        assert msg is None

    def test_full_execution_event_sequence(self):
        """Simulate a full execution event sequence through WSManager."""
        mgr = WSManager()
        messages = []

        events = [
            Event(type="execution_started", execution_id="e1", data={}),
            Event(type="step_started", execution_id="e1", data={"step_id": "open"}),
            Event(type="tool_called", execution_id="e1",
                  data={"tool_name": "navigate", "tool_args": {"url": "http://x.com"}}),
            Event(type="step_completed", execution_id="e1",
                  data={"step_id": "open", "mode": "explore", "summary": "ok"}),
            Event(type="step_started", execution_id="e1", data={"step_id": "click"}),
            Event(type="step_completed", execution_id="e1",
                  data={"step_id": "click", "mode": "replay", "summary": "done"}),
            Event(type="execution_completed", execution_id="e1", data={"report": {"status": "completed"}}),
        ]

        for event in events:
            msg = mgr._event_to_ws_message(event)
            if msg:
                messages.append(msg)

        assert len(messages) == 7
        assert messages[0]["type"] == "execution_status"
        assert messages[0]["status"] == "running"
        assert messages[1]["type"] == "node_status"
        assert messages[1]["status"] == "running"
        assert messages[2]["type"] == "log"
        assert messages[3]["status"] == "success"
        assert messages[4]["status"] == "running"
        assert messages[5]["status"] == "success"
        assert messages[6]["type"] == "execution_status"
        assert messages[6]["status"] == "completed"

    def test_failed_execution_event_sequence(self):
        """Failed step generates correct WS message."""
        mgr = WSManager()

        failed_event = Event(
            type="step_failed",
            execution_id="e1",
            data={"step_id": "login", "error": "element not found", "summary": "timeout"},
        )
        msg = mgr._event_to_ws_message(failed_event)

        assert msg["type"] == "node_status"
        assert msg["status"] == "failed"
        assert msg["data"]["error"] == "element not found"
