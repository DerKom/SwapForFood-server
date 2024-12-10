import random
import json
from models.user import User
from typing import Dict, List
from utils.restaurant_fetcher import fetch_restaurants

class Room:
    def __init__(self, code: str, leader: User):
        self.code = code
        self.leader = leader
        self.leader.is_leader = True
        self.users: List[User] = [leader]
        self.game_started = False

    async def broadcast(self, message: dict):
        # Envía un mensaje a todos los usuarios en la sala
        for user in self.users:
            try:
                await user.websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error al enviar mensaje a {user.username}: {e}")

    async def start_game(self):
        self.game_started = True
        # Obtener restaurantes basados en la ubicación del líder
        restaurants = fetch_restaurants(self.leader.location)
        # Lógica para enviar restaurantes y manejar votaciones
        for restaurant in restaurants:
            await self.broadcast({"type": "restaurant", "data": restaurant})
            # Aquí agregar lógica de votación y consenso

    def get_user_by_username(self, username: str):
        for u in self.users:
            if u.username == username:
                return u
        return None

    def remove_user(self, user: User):
        if user in self.users:
            self.users.remove(user)
            # Si se elimina el líder, reasignar líder al primer usuario si existe
            if user.is_leader and len(self.users) > 0:
                self.users[0].is_leader = True
                return self.users[0]
        return None

    def is_empty(self):
        return len(self.users) == 0

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def generate_room_code(self) -> str:
        while True:
            code = str(random.randint(10000, 99999))
            if code not in self.rooms:
                return code

    async def create_room(self, leader: User) -> str:
        code = self.generate_room_code()
        room = Room(code, leader)
        self.rooms[code] = room
        return code

    def get_room(self, room_code: str):
        return self.rooms.get(room_code)

    async def connect_user(self, room_code: str, user: User):
        room = self.get_room(room_code)
        if room:
            # Si la sala no está vacía, el líder ya existe
            # Si está vacía, este será el líder (ya manejado en Room)
            room.users.append(user)
            await room.broadcast({"type": "user_joined", "username": user.username})

    async def disconnect_user(self, room_code: str, user: User):
        room = self.get_room(room_code)
        if room:
            was_leader = user.is_leader
            new_leader = room.remove_user(user)
            await room.broadcast({"type": "user_left", "username": user.username})
            if was_leader and new_leader:
                # Notificar nuevo líder
                await room.broadcast({"type": "new_leader", "username": new_leader.username})
            # Si la sala queda vacía, se puede eliminar
            if room.is_empty():
                del self.rooms[room_code]

    async def broadcast(self, room_code: str, message: dict):
        room = self.get_room(room_code)
        if room:
            await room.broadcast(message)
