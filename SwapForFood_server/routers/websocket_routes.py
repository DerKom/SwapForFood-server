from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models.room import RoomManager
from models.user import User
import json

router = APIRouter()

room_manager = RoomManager()

@router.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    await websocket.accept()
    user = User(websocket)
    await room_manager.connect_user(room_code, user)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Manejar diferentes tipos de mensajes aquí
            await room_manager.broadcast(room_code, message)
    except WebSocketDisconnect:
        await room_manager.disconnect_user(room_code, user)
