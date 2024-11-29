import random
from models.user import User
from typing import Dict, List
from utils.restaurant_fetcher import fetch_restaurants

class Room:
    def __init__(self, code: str, leader: User):
        self.code = code
        self.leader = leader
        self.users: List[User] = [leader]
        self.game_started = False

    async def broadcast(self, message: dict):
        for user in self.users:
            await user.websocket.send_text(json.dumps(message))

    async def start_game(self):
        self.game_started = True
        # Obtener restaurantes basados en la ubicación del líder
        restaurants = fetch_restaurants(self.leader.location)
        # Lógica para enviar restaurantes y manejar votaciones
        for restaurant in restaurants:
            await self.broadcast({"type": "restaurant", "data": restaurant})
            # Aquí agregar lógica de votación y consenso

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

    async def connect_user(self, room_code: str, user: User):
        room = self.rooms.get(room_code)
        if room:
            room.users.append(user)
            await room.broadcast({"type": "user_joined", "username": user.username})

    async def disconnect_user(self, room_code: str, user: User):
        room = self.rooms.get(room_code)
        if room:
            room.users.remove(user)
            await room.broadcast({"type": "user_left", "username": user.username})

    async def broadcast(self, room_code: str, message: dict):
        room = self.rooms.get(room_code)
        if room:
            await room.broadcast(message)
