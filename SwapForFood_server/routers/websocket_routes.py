import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from managers.room_manager import RoomManager

router = APIRouter()

# Instancia del administrador de salas
room_manager = RoomManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    message_id = 1

    try:
        while True:
            # Recibir mensaje del cliente
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

            # Procesar el mensaje según el prefijo
            if content.startswith("0"):
                # Crear una sala o unirse a una nueva
                response_message = await room_manager.join_room_with_prefix_0(websocket, content)

            elif content.startswith("1"):
                # Unirse a una sala existente
                response_message = await room_manager.join_room_with_prefix_1(websocket, content)

            elif content.startswith("21"):
                # Eliminar a un usuario por nombre
                username_to_remove = content[2:]
                response_message = await room_manager.remove_user_by_username(username_to_remove, websocket)

            elif content.startswith("3"):
                # Enviar un mensaje de chat a la sala
                message_content = content[1:]  # Eliminar el prefijo "3"
                response_message = await room_manager.broadcast_chat_message(sender, message_content, websocket)

            else:
                # Comando no reconocido
                response_message = "1000Error: Comando no reconocido."

            # Enviar la respuesta al cliente
            resp_json = json.dumps({
                "id": message_id,
                "message": response_message,
                "timestamp": timestamp
            })
            message_id += 1
            await websocket.send_text(resp_json)

    except WebSocketDisconnect:
        # Manejar la desconexión del cliente
        await room_manager.handle_disconnect(websocket)
