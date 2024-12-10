import json
import time
from typing import Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from managers.room_manager import RoomManager

router = APIRouter()

room_manager = RoomManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    message_id = 1

    try:
        while True:
            data = await websocket.receive_text()

            # Intentar parsear JSON
            try:
                msg_data = json.loads(data)
                sender = msg_data.get('sender', 'unknown')
                content = msg_data.get('content', '')
                timestamp = int(time.time() * 1000)
            except:
                # Ignorar mensajes no válidos
                continue

            if content.startswith("0"):
                # Crear/unirse a la sala
                response_message = await room_manager.join_room_with_prefix_0(websocket, content)

            elif content.startswith("1-"):
                # Unirse a la sala (similar a '0')
                response_message = await room_manager.join_room_with_prefix_1(websocket, content)
                # Enviar respuesta y continuar
                resp_json = json.dumps({
                    "id": message_id,
                    "message": response_message,
                    "timestamp": timestamp
                })
                message_id += 1
                await websocket.send_text(resp_json)
                continue

            elif content.startswith("21"):
                # Eliminar a un usuario por nombre
                username_to_remove = content[2:]
                response_message = await room_manager.remove_user_by_username(username_to_remove)

            else:
                # Mensaje normal de chat
                response_message = await room_manager.broadcast_chat_message(sender, content)

            # Enviar respuesta si no es el caso de prefijo "1-" ya enviado
            if not content.startswith("1-"):
                resp_json = json.dumps({
                    "id": message_id,
                    "message": response_message,
                    "timestamp": timestamp
                })
                message_id += 1
                await websocket.send_text(resp_json)

    except WebSocketDisconnect:
        pass
    finally:
        await room_manager.handle_disconnect(websocket)
