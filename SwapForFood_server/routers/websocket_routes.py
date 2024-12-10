import asyncio
import json
import time
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Creamos el router para manejar las conexiones WebSocket
router = APIRouter()

# Lista de websockets en la sala. Sólo se maneja una sala
sala: List[WebSocket] = []
# Mapa de WebSocket a información de usuario. Estructura:
# usuarios_sala[websocket] = {'username': str, 'is_leader': bool}
usuarios_sala: Dict[WebSocket, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------------
# FUNCIONES AUXILIARES DE NOTIFICACIÓN
# Estas funciones ayudan a notificar a todos o a un usuario en particular
# sobre eventos que suceden en la sala. Se construye el mensaje y se envía.
# ---------------------------------------------------------------------------------

async def notify_user_removed(websocket: WebSocket):
    # Notificar al usuario removido que ha sido sacado de la sala.
    message = "REMOVED"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    try:
        await websocket.send_text(response)
        await websocket.close()
    except Exception as e:
        # Error al notificar, probablemente el usuario ya se desconectó.
        pass


async def notify_room_closed():
    # Notificar a todos los usuarios que la sala ha sido cerrada.
    message = "ROOM_CLOSED"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    # Intentamos notificar a cada usuario.
    # Si falla es que ya se desconectó.
    for ws in sala:
        try:
            await ws.send_text(response)
        except:
            pass


async def notify_new_user(username: str, new_websocket: WebSocket):
    # Notificar a todos (excepto al que se une) que un nuevo usuario ha entrado.
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
            except:
                pass


async def notify_user_left(username: str):
    # Notificar a todos que un usuario ha salido de la sala.
    message = f"USER_LEFT.{username}"
    response = json.dumps({
        "id": 0,
        "message": message,
        "timestamp": int(time.time() * 1000)
    })
    for ws in sala:
        try:
            await ws.send_text(response)
        except:
            pass


async def broadcast_message(sender: str, content: str):
    # Enviar un mensaje de chat a todos en la sala.
    msg = json.dumps({
        "id": 0,
        "message": f"NEW_MESSAGE.{sender}:{content}",
        "timestamp": int(time.time() * 1000)
    })
    for ws in sala:
        try:
            await ws.send_text(msg)
        except:
            pass


# ---------------------------------------------------------------------------------
# PUNTO DE ENTRADA DEL WEBSOCKET
# Aquí se maneja la conexión entrante y se procesan los mensajes.
# ---------------------------------------------------------------------------------

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Aceptamos la conexión del WebSocket
    await websocket.accept()

    # Un contador para asignar IDs a los mensajes de respuesta
    message_id = 1

    try:
        while True:
            # Esperamos recibir un texto del cliente
            data = await websocket.receive_text()

            # Intentamos parsear el mensaje recibido como JSON
            # Esperamos un dict con al menos 'sender' y 'content'
            try:
                msg_data = json.loads(data)
                sender = msg_data.get('sender', 'unknown')
                content = msg_data.get('content', '')
                # Asignamos un timestamp actual en milisegundos
                timestamp = int(time.time() * 1000)
            except:
                # Si el mensaje no es un JSON válido o faltan campos, lo ignoramos
                continue

            # Revisamos el contenido del mensaje para determinar la acción
            if content.startswith("0"):
                # Prefijo "0" -> Crear o unirse a la sala única
                username = content[1:]  # El nombre de usuario después del '0'
                if websocket in usuarios_sala:
                    # Si el usuario ya está en la sala
                    response_message = "Error: Ya estás en la sala."
                elif len(sala) == 0:
                    # Si la sala está vacía, este usuario será el líder
                    sala.append(websocket)
                    usuarios_sala[websocket] = {'username': username, 'is_leader': True}
                    response_message = f"0000{username}"  # Indica que se creó la sala y se unió
                else:
                    # Sala ya existe, este usuario se une como no-líder
                    sala.append(websocket)
                    usuarios_sala[websocket] = {'username': username, 'is_leader': False}
                    # Notificamos a los demás que entró un nuevo usuario
                    await notify_new_user(username, websocket)
                    # Enviamos la lista de usuarios al que se une
                    user_list = [u['username'] for u in usuarios_sala.values()]
                    response_message = f"0001{len(user_list)}{'.'.join(user_list)}"

            elif content.startswith("1-"):
                # Prefijo "1-" -> Unirse a la sala (similar al caso "0", pero con otra lógica)
                # En este caso simplemente tomamos el resto como nombre de usuario
                # Eliminamos lógica redundante de "código de sala"
                username = content[2:]
                if websocket not in sala:
                    # Determinar si será líder (si la sala está vacía)
                    is_leader = (len(sala) == 0)
                    sala.append(websocket)
                    usuarios_sala[websocket] = {'username': username, 'is_leader': is_leader}
                    # Notificar a los demás que alguien se une
                    await notify_new_user(username, websocket)
                else:
                    # Si ya está en la sala, no hacemos nada especial
                    # Podríamos responder informando que ya está.
                    pass

                # Enviar la lista de usuarios actualizada
                user_list = [u['username'] for u in usuarios_sala.values()]
                response_message = f"0001{len(sala)}{'.'.join(user_list)}"

                # Enviamos la respuesta ahora y continuamos
                resp_json = json.dumps({
                    "id": message_id,
                    "message": response_message,
                    "timestamp": int(time.time() * 1000)
                })
                message_id += 1
                await websocket.send_text(resp_json)
                continue

            elif content.startswith("21"):
                # Prefijo "21" -> Solicitud para eliminar a un usuario por nombre
                username_to_remove = content[2:]
                # Buscamos el websocket de ese usuario
                ws_to_remove = None
                for w, info in usuarios_sala.items():
                    if info['username'] == username_to_remove:
                        ws_to_remove = w
                        break

                if ws_to_remove:
                    # Guardamos si era líder antes de eliminarlo
                    was_leader = usuarios_sala[ws_to_remove]['is_leader']
                    # Eliminamos al usuario
                    sala.remove(ws_to_remove)
                    del usuarios_sala[ws_to_remove]
                    await notify_user_removed(ws_to_remove)
                    # Notificar a los demás que un usuario salió
                    await notify_user_left(username_to_remove)

                    # Si era líder, reasignar el liderazgo
                    if was_leader and sala:
                        new_leader_ws = sala[0]
                        usuarios_sala[new_leader_ws]['is_leader'] = True
                        new_leader_username = usuarios_sala[new_leader_ws]['username']
                        # Notificar a todos el nuevo líder
                        nl_msg = json.dumps({
                            "id": 0,
                            "message": f"NEW_LEADER.{new_leader_username}",
                            "timestamp": int(time.time() * 1000)
                        })
                        for ws in sala:
                            try:
                                await ws.send_text(nl_msg)
                            except:
                                pass

                response_message = "Usuario eliminado."

            else:
                # Mensaje normal de chat, se retransmite a todos.
                await broadcast_message(sender, content)
                response_message = "Mensaje enviado a la sala."

            # Enviamos la respuesta (excepto en el caso del bloque '1-' ya enviado)
            if not content.startswith("1-"):
                resp_json = json.dumps({
                    "id": message_id,
                    "message": response_message,
                    "timestamp": int(time.time() * 1000)
                })
                message_id += 1
                await websocket.send_text(resp_json)

    except WebSocketDisconnect:
        # Si el usuario se desconecta inesperadamente
        pass
    finally:
        # Al desconectar, si estaba en la sala, lo removemos
        if websocket in usuarios_sala:
            username = usuarios_sala[websocket]['username']
            was_leader = usuarios_sala[websocket]['is_leader']
            sala.remove(websocket)
            del usuarios_sala[websocket]

            # Si era líder, cerramos la sala y notificamos
            if was_leader:
                await notify_room_closed()
                sala.clear()
                usuarios_sala.clear()
            else:
                # Notificamos que un usuario salió
                await notify_user_left(username)