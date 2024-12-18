# models/game.py

import time
from models.restaurant import Restaurant
from utils.restaurant_fetcher import fetch_restaurants
import asyncio  # <-- LÍNEA AÑADIDA: Importar asyncio para poder usar sleep y tareas


class Game:
    def __init__(self, leader_location, room):
        self.leader_location = leader_location
        self.room = room
        self.restaurants = []
        # self.current_index = 0  # <-- LÍNEA ELIMINADA: Ya no usamos current_index porque se envían todos a la vez
        self.votes = {}  # {restaurant_id: {username: vote}}
        # Eliminamos max_time y lógica de temporizador.
        # self.start_time = None  # <-- LÍNEA ELIMINADA: No lo necesitaremos así
        self.total_votes_needed = 0  # <-- LÍNEA AÑADIDA: Cantidad total de votos requeridos (usuarios * restaurantes)
        self.timer_task = None  # <-- LÍNEA AÑADIDA: Guardar referencia a la tarea del temporizador
        self.game_ended = False  # <-- LÍNEA AÑADIDA: Para evitar terminar el juego más de una vez

    async def start(self):
        # Ahora en lugar de ir restaurante por restaurante, obtenemos todos a la vez
        raw_restaurants = fetch_restaurants(self.leader_location)
        self.restaurants = [Restaurant(**r.to_dict()) for r in raw_restaurants]

        # Inicializar el diccionario de votos
        for r in self.restaurants:
            self.votes[r.id] = {}

        # Calcular la cantidad total de votos esperada
        # Todos los usuarios deben votar cada restaurante, así que total_votes = num_usuarios * num_restaurantes
        num_users = len(self.room.users)
        num_restaurants = len(self.restaurants)
        self.total_votes_needed = num_users * num_restaurants

        # Enviar mensaje de inicio del juego
        await self.room.broadcast_json({
            "id": 0,
            "message": "GAME_START.",
            "timestamp": int(time.time() * 1000)
        })

        # Enviar en un solo mensaje todos los restaurantes disponibles
        restaurants_data = [r.to_dict() for r in self.restaurants]
        await self.room.broadcast_json({
            "id": num_restaurants,
            "message": f"NEW_RESTAURANT.{restaurants_data}",
            "timestamp": int(time.time() * 1000)
        })

        # Iniciar temporizador, 10 segundos por cada restaurante
        self.timer_task = asyncio.create_task(self.end_game_in_x_seconds(num_restaurants))

    async def end_game_in_x_seconds(self, numRestaurants):
        # Esperar 10 segundos
        await asyncio.sleep(numRestaurants * 10)
        # Si aún no se ha terminado el juego, terminarlo
        if not self.game_ended:
            await self.end_game()

    async def register_vote(self, username, vote, restaurant_id):
        # Registrar el voto sólo si el usuario no ha votado antes a ese restaurante.
        if username not in self.votes[restaurant_id]:
            self.votes[restaurant_id][username] = vote
        # Comprobar si ya tenemos todos los votos necesarios
        # Contar total de votos realizados hasta ahora
        total_cast_votes = sum(len(user_votes) for user_votes in self.votes.values())
        if total_cast_votes == self.total_votes_needed:
            # Todos han votado todos los restaurantes
            if self.timer_task:
                self.timer_task.cancel()  # Cancelar el temporizador si todavía está en curso
            await self.end_game()

    async def end_game(self):
        if self.game_ended:
            return  # Si ya se ha terminado, no hacer nada.
        self.game_ended = True

        # Calcular resultados: cuántos likes tiene cada restaurante
        results = {}
        for r in self.restaurants:
            # Lista de usuarios que han dado like
            likes = [user for user, v in self.votes[r.id].items() if v == '0']  # '0' significa like
            results[r.name] = likes

        await self.room.broadcast_json({
            "id": 0,
            "message": f"GAME_RESULTS.{results}",
            "timestamp": int(time.time() * 1000)
        })

        # Limpiar la referencia al juego en la sala.
        self.room.game = None
