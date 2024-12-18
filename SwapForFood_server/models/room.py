import json
import time
from typing import List
from .user import User

class Room:
    def __init__(self):
        self.users: List[User] = []
        self.game = None  # Agregamos este atributo para almacenar la instancia del juego.

    def add_user(self, user: User):
        self.users.append(user)

    def remove_user(self, user: User):
        if user in self.users:
            self.users.remove(user)
            # Si era líder y quedan usuarios, reasignar liderazgo
            if user.is_leader and self.users:
                self.users[0].is_leader = True
                return self.users[0]
        return None

    def get_user_by_websocket(self, websocket):
        for u in self.users:
            if u.websocket == websocket:
                return u
        return None

    def get_user_by_username(self, username: str):
        for u in self.users:
            if u.username == username:
                return u
        return None

    def is_empty(self):
        return len(self.users) == 0

    async def broadcast(self, message: str):
        # Envía mensaje de texto a todos en la sala
        for u in self.users:
            try:
                await u.websocket.send_text(message)
            except:
                pass

    async def broadcast_json(self, data: dict):
        msg = json.dumps(data)
        await self.broadcast(msg)

    async def notify_room_closed(self):
        message = "ROOM_CLOSED"
        response = json.dumps({
            "id": 0,
            "message": message,
            "timestamp": int(time.time() * 1000)
        })
        await self.broadcast(response)

    async def notify_user_left(self, username: str):
        message = f"USER_LEFT.{username}"
        response = json.dumps({
            "id": 0,
            "message": message,
            "timestamp": int(time.time() * 1000)
        })
        await self.broadcast(response)

    async def notify_new_user(self, username: str, exclude_websocket):
        message = f"USER_JOINED.{username}"
        response = json.dumps({
            "id": 0,
            "message": message,
            "timestamp": int(time.time() * 1000)
        })
        for u in self.users:
            if u.websocket != exclude_websocket:
                try:
                    await u.websocket.send_text(response)
                except:
                    pass

    async def notify_user_removed(self, user: User):
        message = "REMOVED"
        response = json.dumps({
            "id": 0,
            "message": message,
            "timestamp": int(time.time() * 1000)
        })
        try:
            await user.websocket.send_text(response)
            await user.websocket.close()
        except:
            pass

    async def broadcast_message(self, sender: str, content: str):
        msg = json.dumps({
            "id": 0,
            "message": f"NEW_MESSAGE.{sender}:{content}",
            "timestamp": int(time.time() * 1000)
        })
        await self.broadcast(msg)