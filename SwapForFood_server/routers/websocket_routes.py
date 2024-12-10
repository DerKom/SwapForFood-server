import asyncio
import json
import time
from dataclasses import dataclass
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# ===== Código del segundo snippet integrado =====

@dataclass
class Message:
    sender: str
    content: str
    timestamp: int

@dataclass
class ResponseData:
    id: int
    message: str
    timestamp: int

# Sala única (puedes modificar esto para múltiples salas si es necesario)
sala: List[WebSocket] = []  # Lista de websockets en la sala
usuarios_sala: Dict[WebSocket, Dict[str, Any]] = {}  # Websocket -> {'username': str, 'is_leader': bool}

async def notify_user_removed(websocket: WebSocket):
    """Notificar al usuario que ha sido removido de la sala."""
    message = "REMOVED"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    try:
        await websocket.send_text(response)
        print(f"Notificado al usuario {websocket.client} sobre su eliminación.")
        await websocket.close()  # Opcional: cerrar la conexión del usuario eliminado
    except Exception as e:
        print(f"Error al notificar al usuario removido: {e}")

async def notify_room_closed():
    """Notificar a todos los usuarios que la sala ha sido cerrada."""
    message = "ROOM_CLOSED"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    for ws in sala:
        try:
            await ws.send_text(response)
            print(f"Notificado a {ws.client} que la sala ha sido cerrada.")
        except Exception as e:
            print(f"Error al notificar a {ws.client} sobre el cierre de la sala: {e}")

async def notify_new_user(username: str, new_websocket: WebSocket):
    """Notificar a todos los usuarios en la sala sobre un nuevo usuario."""
    message = f"USER_JOINED.{username}"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    for ws in sala:
        if ws != new_websocket:
            try:
                await ws.send_text(response)
                print(f"Notificado a {ws.client} sobre la unión de {username}.")
            except Exception as e:
                print(f"Error al notificar a {ws.client}: {e}")

async def notify_user_left(username: str):
    """Notificar a todos los usuarios en la sala que un usuario ha salido."""
    message = f"USER_LEFT.{username}"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    for ws in sala:
        try:
            await ws.send_text(response)
            print(f"Notificado a {ws.client} sobre la salida de {username}.")
        except Exception as e:
            print(f"Error al notificar a {ws.client}: {e}")

async def broadcast_message(sender: str, content: str):
    """Enviar un mensaje de chat a todos los usuarios en la sala."""
    message = json.dumps({
        "id": 0,
        "message": f"NEW_MESSAGE.{sender}:{content}",
        "timestamp": int(time.time() * 1000)
    })
    for ws in sala:
        try:
            await ws.send_text(message)
        except Exception as e:
            print(f"Error al enviar mensaje a {ws.client}: {e}")

def get_websocket_by_username(username: str) -> WebSocket:
    for ws, info in usuarios_sala.items():
        if info['username'] == username:
            return ws
    return None

# ===== Código del primer snippet adaptado e integrado con el segundo =====

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    message_id = 1

    print(f"Cliente conectado: {websocket.client}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Mensaje recibido: {data}")

            # Parsear el mensaje
            try:
                msg_data = json.loads(data)
                msg = Message(
                    sender=msg_data.get('sender', 'unknown'),
                    content=msg_data.get('content', ''),
                    timestamp=msg_data.get('timestamp', int(time.time() * 1000))
                )
                print(f"Mensaje parseado: Sender={msg.sender}, Content={msg.content}, Timestamp={msg.timestamp}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error al parsear el mensaje: {e}")
                continue  # Ignorar mensajes malformados

            # Manejo de mensajes según su prefijo
            if msg.content.startswith("0"):
                # Crear o unirse a la sala única
                username = msg.content[1:]  # Extraer username después del "0"
                if websocket in usuarios_sala:
                    response_message = "Error: Ya estás en la sala."
                elif len(sala) == 0:
                    # Si la sala está vacía, el usuario será el líder
                    sala.append(websocket)
                    usuarios_sala[websocket] = {'username': username, 'is_leader': True}
                    print(f"Usuario '{username}' creó la sala y se unió como líder.")
                    response_message = f"0000{username}"  # Indicar que se ha creado la sala
                else:
                    # Sala ya existe, unirse a la sala
                    sala.append(websocket)
                    usuarios_sala[websocket] = {'username': username, 'is_leader': False}
                    print(f"Usuario '{username}' se unió a la sala existente.")

                    # Notificar a los demás usuarios de la nueva incorporación
                    await notify_new_user(username, websocket)

                    # Enviar lista de usuarios al nuevo cliente
                    user_list = [user_info['username'] for user_info in usuarios_sala.values()]
                    response_message = f"0001{len(user_list)}{'.'.join(user_list)}"

            elif msg.content.startswith("1-"):
                try:
                    ip = websocket.client[0] if websocket.client else "desconocida"
                    content = msg.content[2:]
                    codigo_sala = content[:5]
                    username = content[5:]

                    # Verificar si el usuario ya está en la sala
                    if websocket not in sala:
                        # Determinar si el usuario será el líder
                        is_leader = len(sala) == 0
                        sala.append(websocket)
                        usuarios_sala[websocket] = {'username': username, 'is_leader': is_leader}
                        role = "líder" if is_leader else "miembro"
                        print(f"Sala = {sala}")
                        await notify_new_user(username, websocket)
                        print(f"Usuario '{username}' se unió a la sala '{codigo_sala}' desde IP '{ip}' como {role}.")
                    else:
                        existing_username = usuarios_sala[websocket]['username']
                        print(f"Usuario '{existing_username}' ya está en la sala '{codigo_sala}'.")

                    user_list = ".".join([user_info['username'] for user_info in usuarios_sala.values()]).strip()
                    response_message = f"0001{len(sala)}{user_list}"

                    # Responder de inmediato
                    response = ResponseData(
                        id=message_id,
                        message=response_message,
                        timestamp=int(time.time() * 1000)
                    )
                    message_id += 1
                    response_json = json.dumps({
                        "id": response.id,
                        "message": response.message,
                        "timestamp": response.timestamp
                    })
                    await websocket.send_text(response_json)
                    print(f"Mensaje de respuesta: {response_message}")
                    print(f"Usuarios actuales en la sala '{codigo_sala}': {[user_info['username'] for user_info in usuarios_sala.values()]}")
                    # Pasar a la siguiente iteración (para no recrear el response abajo)
                    continue

                except Exception as e:
                    print(f"Error al unir usuario a la sala: {e}")
                    response_message = f"Error al procesar el mensaje: {e}"
                    response = ResponseData(
                        id=message_id,
                        message=response_message,
                        timestamp=int(time.time() * 1000)
                    )
                    message_id += 1
                    response_json = json.dumps({
                        "id": response.id,
                        "message": response.message,
                        "timestamp": response.timestamp
                    })
                    await websocket.send_text(response_json)
                    continue

            elif msg.content.startswith("21"):
                # Manejo para eliminación de usuario
                username_to_remove = msg.content[2:]
                print(f"Solicitud para eliminar al usuario: {username_to_remove}")

                ws_to_remove = get_websocket_by_username(username_to_remove)
                if ws_to_remove:
                    # Verificar si el usuario es el líder
                    is_leader = usuarios_sala[ws_to_remove]['is_leader']

                    # Eliminar al usuario de la sala
                    sala.remove(ws_to_remove)
                    del usuarios_sala[ws_to_remove]
                    print(f"Usuario '{username_to_remove}' eliminado de la sala.")
                    await notify_user_removed(ws_to_remove)

                    # Notificar a los demás usuarios sobre la eliminación
                    await notify_user_left(username_to_remove)

                    # Si el usuario eliminado era el líder, reasignar liderazgo
                    if is_leader and sala:
                        new_leader_ws = sala[0]
                        usuarios_sala[new_leader_ws]['is_leader'] = True
                        new_leader_username = usuarios_sala[new_leader_ws]['username']
                        print(f"Usuario '{new_leader_username}' reasignado como líder.")

                        # Notificar a todos sobre el nuevo líder
                        response_message = f"NEW_LEADER.{new_leader_username}"
                        nl_response = json.dumps({
                            "id": 0,
                            "message": response_message,
                            "timestamp": int(time.time() * 1000)
                        })
                        for ws in sala:
                            try:
                                await ws.send_text(nl_response)
                                print(f"Notificado a {ws.client} sobre el nuevo líder: {new_leader_username}.")
                            except Exception as e:
                                print(f"Error al notificar a {ws.client}: {e}")

                response_message = "Usuario eliminado."

            else:
                # Mensaje normal de chat
                await broadcast_message(msg.sender, msg.content)
                response_message = "Mensaje enviado a la sala."

            # Crear y enviar la respuesta (excepto en el caso del bloque '1-' ya manejado arriba)
            if not msg.content.startswith("1-"):
                response = ResponseData(
                    id=message_id,
                    message=response_message,
                    timestamp=int(time.time() * 1000)
                )
                message_id += 1
                response_json = json.dumps({
                    "id": response.id,
                    "message": response.message,
                    "timestamp": response.timestamp
                })
                await websocket.send_text(response_json)
                print(f"Respuesta enviada: {response_json}")

    except WebSocketDisconnect:
        print(f"Cliente desconectado: {websocket.client}")
    finally:
        # Manejar la desconexión del cliente
        if websocket in usuarios_sala:
            username = usuarios_sala[websocket]['username']
            is_leader = usuarios_sala[websocket]['is_leader']

            # Eliminar al usuario de la sala
            sala.remove(websocket)
            del usuarios_sala[websocket]
            print(f"Usuario '{username}' salió de la sala.")

            # Si el usuario es el líder, eliminar la sala y notificar a los usuarios restantes
            if is_leader:
                print("El líder ha salido. Cerrando la sala y notificando a los usuarios restantes.")
                await notify_room_closed()
                sala.clear()
                usuarios_sala.clear()
            else:
                # Notificar a los demás usuarios que un usuario ha salido
                await notify_user_left(username)
