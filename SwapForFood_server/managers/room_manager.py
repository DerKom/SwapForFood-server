import json
import time
from models.user import User
from models.room import Room

class RoomManager:
    def __init__(self):
        self.room = Room()

    async def join_room_with_prefix_0(self, websocket, content: str):
        # content: "0username"
        username = content[1:]
        user_in_room = self.room.get_user_by_websocket(websocket)
        if user_in_room:
            # Ya está en la sala
            return "Error: Ya estás en la sala."
        elif self.room.is_empty():
            # Sala vacía, este user es líder
            user = User(websocket)
            user.username = username
            user.is_leader = True
            self.room.add_user(user)
            return f"0000{username}"  # Indica creación y unión
        else:
            # Sala ya existe, este no es líder
            user = User(websocket)
            user.username = username
            user.is_leader = False
            self.room.add_user(user)
            await self.room.notify_new_user(username, websocket)
            # Lista de usuarios
            user_list = [u.username for u in self.room.users]
            return f"0001{len(user_list)}{'.'.join(user_list)}"

    async def join_room_with_prefix_1(self, websocket, content: str):
        # content: "1-username"
        username = content[2:]
        user = self.room.get_user_by_websocket(websocket)
        if not user:
            # Si no está en la sala, lo agregamos
            new_user = User(websocket)
            new_user.username = username
            new_user.is_leader = (self.room.is_empty())
            self.room.add_user(new_user)
            await self.room.notify_new_user(username, websocket)
        # Lista de usuarios
        user_list = [u.username for u in self.room.users]
        return f"0001{len(self.room.users)}{'.'.join(user_list)}"

    async def remove_user_by_username(self, username: str):
        user_to_remove = self.room.get_user_by_username(username)
        if user_to_remove:
            was_leader = user_to_remove.is_leader
            await self.room.notify_user_removed(user_to_remove)
            new_leader = self.room.remove_user(user_to_remove)
            await self.room.notify_user_left(username)
            # Si era líder, notificar nuevo líder
            if was_leader and new_leader:
                nl_msg = {
                    "id": 0,
                    "message": f"NEW_LEADER.{new_leader.username}",
                    "timestamp": int(time.time() * 1000)
                }
                await self.room.broadcast_json(nl_msg)

        return "Usuario eliminado."

    async def broadcast_chat_message(self, sender: str, content: str):
        await self.room.broadcast_message(sender, content)
        return "Mensaje enviado a la sala."

    async def handle_disconnect(self, websocket):
        user = self.room.get_user_by_websocket(websocket)
        if user:
            username = user.username
            was_leader = user.is_leader
            new_leader = self.room.remove_user(user)
            if was_leader:
                # Cerrar sala
                await self.room.notify_room_closed()
                # Limpiar sala
                self.room = Room()
            else:
                await self.room.notify_user_left(username)
