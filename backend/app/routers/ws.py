import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.engine.execution_manager import cancel_execution
from app.engine.ws_manager import ws_manager
from app.logger import logger

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/cases/{case_id}")
async def case_ws(websocket: WebSocket, case_id: str):
    await ws_manager.connect(case_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("command") == "stop":
                    await cancel_execution(case_id)
                    await websocket.send_text(json.dumps({
                        "type": "execution_status",
                        "status": "cancelled",
                        "data": {"message": "Execution cancelled by user"},
                    }))
            except json.JSONDecodeError:
                logger.warning("[WS] Received invalid JSON from client")
    except WebSocketDisconnect:
        ws_manager.disconnect(case_id, websocket)
