import asyncio
import time
from models.restaurant import Restaurant
from utils.restaurant_fetcher import fetch_restaurants

class Game:
    def __init__(self, leader_location, room, max_time_per_restaurant=10):
        self.leader_location = leader_location
        self.room = room
        self.restaurants = []
        self.current_index = 0
        self.votes = {}  # {restaurant_id: {username: vote}}
        self.max_time = max_time_per_restaurant  # En segundos
        self.start_time = None

    async def start(self):
        # Enviar mensaje de inicio del juego
        await self.room.broadcast_json({
            "id": 0,
            "message": "GAME_START.",
            "timestamp": int(time.time() * 1000)
        })

        raw_restaurants = await fetch_restaurants(self.leader_location)
        self.restaurants = [Restaurant(**r.to_dict()) for r in raw_restaurants]
        self.votes = {r.id: {} for r in self.restaurants}
        await self.send_next_restaurant()

    async def send_next_restaurant(self):
        if self.current_index >= len(self.restaurants):
            await self.end_game()
            return

        restaurant = self.restaurants[self.current_index]
        self.start_time = time.time()
        await self.room.broadcast_json({
            "id": 0,
            "data": f"NEW_RESTAURANT.{restaurant.to_dict()}",
            "timestamp": int(time.time() * 1000)
        })
        asyncio.create_task(self.monitor_time())

    async def monitor_time(self):
        await asyncio.sleep(self.max_time)
        if time.time() - self.start_time >= self.max_time:
            await self.advance_to_next()

    async def register_vote(self, username, vote):
        restaurant_id = self.restaurants[self.current_index].id
        self.votes[restaurant_id][username] = vote
        if len(self.votes[restaurant_id]) >= len(self.room.users):
            await self.advance_to_next()

    async def advance_to_next(self):
        self.current_index += 1
        await self.send_next_restaurant()

    async def end_game(self):
        results = {
            r.name: [user for user, vote in self.votes[r.id].items() if vote == 'like']
            for r in self.restaurants
        }
        await self.room.broadcast_json({
            "event": "GAME_RESULTS",
            "data": results
        })
