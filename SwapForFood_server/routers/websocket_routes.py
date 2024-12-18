# routers/websocket_routes.py

import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from managers.room_manager import RoomManager
from models.game import Game

router = APIRouter()

room_manager = RoomManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    message_id = 1

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
                sender = msg_data.get('sender', 'unknown')
                content = msg_data.get('content', '')
                timestamp = int(time.time() * 1000)
            except:
                continue

            # Procesar el mensaje según el prefijo
            if content.startswith("0"):
                response_message = await room_manager.join_room_with_prefix_0(websocket, content)

            elif content.startswith("1"):
                response_message = await room_manager.join_room_with_prefix_1(websocket, content)

            elif content.startswith("21"):
                username_to_remove = content[2:]
                response_message = await room_manager.remove_user_by_username(username_to_remove, websocket)

            elif content.startswith("3"):
                # Mensaje de chat
                message_content = content[1:]
                response_message = await room_manager.broadcast_chat_message(sender, message_content, websocket)

            elif content.startswith("4"):
                # Iniciar el juego
                room = room_manager.get_room_by_websocket(websocket)
                if room:
                    acting_user = room.get_user_by_websocket(websocket)
                    if acting_user and acting_user.is_leader:
                        leader_location = content[1:]  # "4lat,lng"
                        game = Game(leader_location, room)
                        room.game = game
                        await game.start()
                        response_message = "0000GAME_STARTED"
                    else:
                        response_message = "1000ERROR: Only the leader can start the game."
                else:
                    response_message = "1000ERROR: Room not found."

            elif content.startswith("5"):
                # Votar: "5{0|1}{IDRestaurante}"
                # Ejemplo: "5012" => "5" prefijo, "0" like, "12" id del restaurante
                # Extraer voto y ID del restaurante
                # Voto es el segundo caracter, ID del restaurante es el resto
                # 5 (prefijo) + {0 o 1} + {IDRestaurante}
                room = room_manager.get_room_by_websocket(websocket)
                if room and room.game:
                    acting_user = room.get_user_by_websocket(websocket)
                    if acting_user:
                        vote_char = content[1]  # '0' o '1'
                        restaurant_id = content[2:]  # El resto del string es la ID
                        await room.game.register_vote(acting_user.username, vote_char, restaurant_id)
                        response_message = "VOTE_REGISTERED"
                    else:
                        response_message = "ERROR: User not found."
                else:
                    response_message = "ERROR: Room or Game not found."

            else:
                response_message = "1000Error: Comando no reconocido."

            resp_json = json.dumps({
                "id": message_id,
                "message": response_message,
                "timestamp": timestamp
            })
            message_id += 1
            await websocket.send_text(resp_json)

    except WebSocketDisconnect:
        await room_manager.handle_disconnect(websocket)
