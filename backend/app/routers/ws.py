from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.engine.ws_manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/api/ws/cases/{case_id}")
async def case_ws(websocket: WebSocket, case_id: str):
    await ws_manager.connect(case_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(case_id, websocket)
