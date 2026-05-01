from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


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


ws_manager = WSManager()
