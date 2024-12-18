import json
import random
import time
from models.user import User
from models.room import Room


class RoomManager:

    def __init__(self):
        self.rooms = {}  # Mapa de salas {codigo_sala: Room}
        self.websocket_to_room = {}  # Mapa de Websockets {websocket: codigo_sala}

    async def join_room_with_prefix_0(self, websocket, content: str):
        # Comprobar si el WebSocket ya tiene una sala asignada
        if websocket in self.websocket_to_room:
            codigo_sala = self.websocket_to_room[websocket]
            return f"1000Error: El WebSocket ya tiene asignada la sala {codigo_sala}."

        # Extraer nombre de usuario
        username = content[1:]

        # Generar un código aleatorio de 5 dígitos único para la sala
        while True:
            codigo_sala = f"{random.randint(0, 99999):05}"
            if codigo_sala not in self.rooms:
                break

        # Crear una nueva sala
        nueva_sala = Room()
        self.rooms[codigo_sala] = nueva_sala
        self.websocket_to_room[websocket] = codigo_sala

        # Crear un nuevo usuario y hacerlo líder
        user = User(websocket)
        user.username = username
        user.is_leader = True
        nueva_sala.add_user(user)

        # Devolver respuesta con el código de sala y nombre del usuario
        return f"0000{codigo_sala}{username}"

    async def join_room_with_prefix_1(self, websocket, content: str):
        # content: "1roomCodeusername"

        roomCode = content[1:6]  # Del segundo carácter hasta el sexto
        username = content[6:]  # Del séptimo carácter en adelante

        # Verificar si la sala existe
        sala = self.rooms.get(roomCode)
        if not sala:
            return f"1000Error: La sala con código {roomCode} no existe."

        # Comprobar si el usuario ya está en la sala
        user = sala.get_user_by_websocket(websocket)
        if not user:
            # Si no está en la sala, lo agregamos
            new_user = User(websocket)
            new_user.username = username
            new_user.is_leader = False  # Solo el usuario que crea la sala es líder
            sala.add_user(new_user)
            self.websocket_to_room[websocket] = roomCode
            await sala.notify_new_user(username, websocket)

        # Lista de usuarios
        user_list = [u.username for u in sala.users]
        return f"0001{len(sala.users)}{'.'.join(user_list)}"

    async def remove_user_by_username(self, username: str, websocket):
        # Obtener la sala del usuario que realiza la solicitud
        roomCode = self.websocket_to_room.get(websocket)

        if not roomCode:
            return f"1000Error: No se encontró ninguna sala asociada al WebSocket."

        sala = self.rooms.get(roomCode)
        if not sala:
            return f"1000Error: La sala con código {roomCode} no existe."

        # Verificar si el usuario que realiza la acción es líder
        acting_user = sala.get_user_by_websocket(websocket)
        if not acting_user or not acting_user.is_leader:
            return "1000Error: Solo el líder puede eliminar usuarios de la sala."

        # Buscar al usuario a eliminar
        user_to_remove = sala.get_user_by_username(username)
        if not user_to_remove:
            return f"1000Error: El usuario {username} no está en la sala {roomCode}."

        was_leader = user_to_remove.is_leader

        # Notificar a todos que el usuario será eliminado
        await sala.broadcast_json({
            "id": 0,
            "message": f"USER_REMOVED.{username}",
            "timestamp": int(time.time() * 1000)
        })

        # Cerrar conexión del usuario eliminado
        try:
            await user_to_remove.websocket.close()
        except:
            pass  # Ignorar errores si el websocket ya estaba cerrado

        # Eliminar al usuario de la sala
        sala.remove_user(user_to_remove)
        del self.websocket_to_room[user_to_remove.websocket]

        # Si la sala está vacía, eliminarla
        if sala.is_empty():
            await sala.notify_room_closed()  # Notificar cierre de sala
            await self.remove_room(roomCode)
        else:
            # Si el usuario eliminado era líder, reasignar liderazgo
            if was_leader:
                new_leader = sala.users[0]  # Asignar al primer usuario restante
                new_leader.is_leader = True
                await sala.broadcast_json({
                    "id": 0,
                    "message": f"NEW_LEADER.{new_leader.username}",
                    "timestamp": int(time.time() * 1000)
                })

        # Si hay un juego en curso, verificar si ahora todos los votos están listos
        if sala.game is not None:
            await sala.game.check_results()

        return f"0000"

    async def handle_disconnect(self, websocket):
        # Buscar la sala a la que pertenece el usuario
        codigo_sala = self.websocket_to_room.get(websocket)
        if not codigo_sala:
            return  # El usuario no está asociado a ninguna sala

        sala = self.rooms.get(codigo_sala)
        if not sala:
            return  # La sala no existe (inconsistencia inesperada)

        # Encontrar al usuario en la sala
        user = sala.get_user_by_websocket(websocket)
        if not user:
            return  # El usuario no está en la sala (inconsistencia inesperada)

        # Notificar a los demás usuarios que el usuario ha abandonado la sala
        await sala.notify_user_left(user.username)

        # Eliminar al usuario de la sala
        was_leader = user.is_leader
        sala.remove_user(user)
        del self.websocket_to_room[websocket]

        # Si la sala está vacía, eliminarla
        if sala.is_empty():
            await sala.notify_room_closed()
            await self.remove_room(codigo_sala)
        else:
            # Si el usuario era líder, reasignar liderazgo
            if was_leader:
                new_leader = sala.users[0]
                new_leader.is_leader = True
                await sala.broadcast_json({
                    "id": 0,
                    "message": f"NEW_LEADER.{new_leader.username}",
                    "timestamp": int(time.time() * 1000)
                })

        # Si hay un juego en curso, verificar si ahora que se fue un usuario ya se cumplen las condiciones
        if sala.game is not None:
            await sala.game.check_results()

    async def remove_room(self, codigo_sala):
        if codigo_sala in self.rooms:
            del self.rooms[codigo_sala]
            self.websocket_to_room = {ws: room for ws, room in self.websocket_to_room.items() if room != codigo_sala}

    async def broadcast_chat_message(self, sender: str, content: str, websocket):
        # Obtener la sala del usuario que realiza la solicitud
        roomCode = self.websocket_to_room.get(websocket)
        if not roomCode:
            return f"1000Error: No se encontró ninguna sala asociada al WebSocket."

        sala = self.rooms.get(roomCode)
        if not sala:
            return f"1000Error: La sala con código {roomCode} no existe."

        await sala.broadcast_message(sender, content)
        return "0000"

    def get_room_by_websocket(self, websocket):
        codigo_sala = self.websocket_to_room.get(websocket)
        if not codigo_sala:
            return None
        return self.rooms.get(codigo_sala)
