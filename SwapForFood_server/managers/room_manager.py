import json
import random
import time
from models.user import User
from models.room import Room

class RoomManager:

    def __init__(self):
        self.rooms = {}  # Mapa de salas {codigo_sala: Room}
        self.ip_to_room = {}  # Mapa de IPs {ip: codigo_sala}

    async def join_room_with_prefix_0(self, websocket, content: str):
        # Obtener IP del cliente
        client_ip = websocket.client.host

        # Comprobar si la IP ya tiene una sala asignada
        if client_ip in self.ip_to_room:
            codigo_sala = self.ip_to_room[client_ip]
            return f"1000Error: La IP {client_ip} ya tiene asignada la sala {codigo_sala}."

        # Extraer nombre de usuario
        username = content[1:]

        # Generar un código aleatorio de 5 dígitos único para la sala
        while True:
            codigo_sala = f"{random.randint(00000, 99999)}"
            if codigo_sala not in self.rooms:
                break

        # Crear una nueva sala
        nueva_sala = Room()
        self.rooms[codigo_sala] = nueva_sala
        self.ip_to_room[client_ip] = codigo_sala

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
            await sala.notify_new_user(username, websocket)

        # Lista de usuarios
        user_list = [u.username for u in sala.users]
        return f"0001{len(sala.users)}{'.'.join(user_list)}"

    async def remove_user_by_username(self, username: str, websocket):
        # Obtener la sala del usuario que realiza la solicitud
        client_ip = websocket.client.host
        roomCode = self.ip_to_room.get(client_ip)

        print("Usuario que vamos a borrar: ", username)
        print("RoomCode del supuesto lider: ", roomCode)

        if not roomCode:
            return f"1000Error: No se encontró ninguna sala asociada a la IP {client_ip}."

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

        return f"0000"

    async def broadcast_chat_message(self, sender: str, content: str, websocket):
        # Obtener la sala del usuario que envía el mensaje
        client_ip = websocket.client.host
        roomCode = self.ip_to_room.get(client_ip)

        if not roomCode:
            return f"1000Error: No se encontró ninguna sala asociada a la IP {client_ip}."

        sala = self.rooms.get(roomCode)
        if not sala:
            return f"1000Error: La sala con código {roomCode} no existe."

        await sala.broadcast_message(sender, content)
        return "Mensaje enviado a la sala."

    async def remove_room(self, codigo_sala):
        # Eliminar la sala y su referencia de IP
        if codigo_sala in self.rooms:
            del self.rooms[codigo_sala]
            self.ip_to_room = {ip: room for ip, room in self.ip_to_room.items() if room != codigo_sala}

    async def handle_disconnect(self, websocket):
        # Obtener la IP del cliente desconectado
        client_ip = websocket.client.host

        # Buscar la sala a la que pertenece el usuario
        codigo_sala = self.ip_to_room.get(client_ip)
        if not codigo_sala:
            return  # El usuario no está asociado a ninguna sala

        sala = self.rooms.get(codigo_sala)
        if not sala:
            return  # La sala no existe (inconsistencia inesperada)

        # Encontrar al usuario en la sala
        user = sala.get_user_by_websocket(websocket)
        if not user:
            return  # El usuario no está en la sala (inconsistencia inesperada)

        # Eliminar al usuario de la sala
        was_leader = user.is_leader
        sala.remove_user(user)

        # Si la sala está vacía, eliminarla
        if sala.is_empty():
            await sala.notify_room_closed()  # Notificar cierre de sala
            await self.remove_room(codigo_sala)
        else:
            # Si el usuario era líder, reasignar liderazgo
            if was_leader:
                new_leader = sala.users[0]  # Asignar al primer usuario restante
                new_leader.is_leader = True
                await sala.broadcast_json({
                    "id": 0,
                    "message": f"NEW_LEADER.{new_leader.username}",
                    "timestamp": int(time.time() * 1000)
                })

        # Eliminar la asociación de la IP del cliente
        if client_ip in self.ip_to_room:
            del self.ip_to_room[client_ip]
