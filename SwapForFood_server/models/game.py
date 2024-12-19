import time
from models.restaurant import Restaurant
from utils.restaurant_fetcher import fetch_restaurants
import asyncio

class Game:
    def __init__(self, leader_location, room, offline=False):
        self.leader_location = leader_location
        self.room = room
        self.restaurants = []
        self.votes = {}
        self.total_votes_needed = 0
        self.timer_task = None
        self.game_ended = False
        self.offline = offline

    async def start(self):
        # Obtener restaurantes (offline o usando la API real)
        raw_restaurants = fetch_restaurants(self.leader_location, offline=self.offline)
        self.restaurants = [Restaurant(**r.to_dict()) for r in raw_restaurants]

        for r in self.restaurants:
            self.votes[r.id] = {}

        num_users = len(self.room.users)
        num_restaurants = len(self.restaurants)
        self.total_votes_needed = num_users * num_restaurants

        await self.room.broadcast_json({
            "id": 0,
            "message": "GAME_START.",
            "timestamp": int(time.time() * 1000)
        })

        restaurants_data = [r.to_dict() for r in self.restaurants]
        await self.room.broadcast_json({
            "id": num_restaurants,
            "message": f"NEW_RESTAURANT.{restaurants_data}",
            "timestamp": int(time.time() * 1000)
        })

        self.timer_task = asyncio.create_task(self.end_game_in_x_seconds(num_restaurants))

    async def end_game_in_x_seconds(self, num_restaurants):
        await asyncio.sleep(num_restaurants * 10)
        if not self.game_ended:
            await self.end_game()

    async def register_vote(self, username, vote, restaurant_id):
        if restaurant_id not in self.votes:
            return

        if username not in self.votes[restaurant_id]:
            self.votes[restaurant_id][username] = vote

            total_cast_votes = sum(len(user_votes) for user_votes in self.votes.values())

            if total_cast_votes >= self.total_votes_needed:
                if self.timer_task:
                    self.timer_task.cancel()
                await self.end_game()

    async def end_game(self):
        if self.game_ended:
            return
        self.game_ended = True

        results = {}
        for r in self.restaurants:
            likes = [user for user, v in self.votes[r.id].items() if v == '0']
            results[r.name] = likes

        await self.room.broadcast_json({
            "id": 0,
            "message": f"GAME_RESULTS.{results}",
            "timestamp": int(time.time() * 1000)
        })

        self.room.game = None
