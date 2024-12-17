import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from managers.room_manager import RoomManager
from models.game import Game


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

            elif content.startswith("4"):
                # Iniciar el juego en la sala (solo el líder puede hacerlo)
                room = room_manager.get_room_by_websocket(websocket)
                if room:
                    acting_user = room.get_user_by_websocket(websocket)
                    if acting_user and acting_user.is_leader:
                        # Obtener ubicación del líder para buscar restaurantes
                        leader_location = content[1:]  # Ejemplo: "4lat,lng"
                        game = Game(leader_location, room)
                        await game.start()
                        response_message = "0000GAME_STARTED"
                    else:
                        response_message = "1000ERROR: Only the leader can start the game."
                else:
                    response_message = "1000ERROR: Room not found."

            elif content.startswith("5"):
                # Registrar un voto del usuario
                room = room_manager.get_room_by_websocket(websocket)
                if room:
                    acting_user = room.get_user_by_websocket(websocket)
                    if acting_user:
                        vote = content[1:]  # Ejemplo: "5like" o "5dislike"
                        await room.game.register_vote(acting_user.username, vote)
                        response_message = "VOTE_REGISTERED"
                    else:
                        response_message = "ERROR: User not found."
                else:
                    response_message = "ERROR: Room not found."

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
