"""WebSocket connection manager."""
from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from app.engine.event_bus import Event
from app.logger import logger


class WSManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, execution_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections.setdefault(execution_id, []).append(websocket)

    def disconnect(self, execution_id: str, websocket: WebSocket):
        conns = self._connections.get(execution_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(execution_id, None)

    async def broadcast(self, execution_id: str, message: dict[str, Any]):
        conns = self._connections.get(execution_id, [])
        payload = json.dumps(message, ensure_ascii=False)
        dead = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(execution_id, ws)
        if dead:
            logger.warning(
                "[WSManager] Removed {} dead connections for execution {}",
                len(dead),
                execution_id,
            )

    async def handle_event(self, event: Event) -> None:
        """Convert an Event into a WSMessage and broadcast it."""
        ws_msg = self._event_to_ws_message(event)
        if ws_msg:
            await self.broadcast(event.execution_id, ws_msg)

    def _event_to_ws_message(self, event: Event) -> dict | None:
        if event.type == "step_started":
            return {
                "type": "node_status",
                "node_id": event.data.get("step_id"),
                "status": "running",
            }
        elif event.type == "step_completed":
            return {
                "type": "node_status",
                "node_id": event.data.get("step_id"),
                "status": "success",
                "data": {
                    "mode": event.data.get("mode", ""),
                    "summary": event.data.get("summary", ""),
                },
            }
        elif event.type == "step_failed":
            return {
                "type": "node_status",
                "node_id": event.data.get("step_id"),
                "status": "failed",
                "data": {
                    "error": event.data.get("error", ""),
                    "summary": event.data.get("summary", ""),
                },
            }
        elif event.type == "tool_called":
            return {
                "type": "log",
                "node_id": event.data.get("tool_name"),
                "data": {
                    "message": f"调用工具: {event.data['tool_name']}({event.data.get('tool_args', {})})",
                },
            }
        elif event.type == "execution_completed":
            return {
                "type": "execution_status",
                "status": event.data.get("report", {}).get("status", "unknown"),
                "data": {"report": event.data.get("report")},
            }
        elif event.type == "execution_started":
            return {
                "type": "execution_status",
                "status": "running",
            }
        elif event.type == "log_message":
            return {
                "type": "log",
                "data": {"message": event.data.get("message", "")},
            }
        return None


ws_manager = WSManager()
