# models/game.py

import time
from models.restaurant import Restaurant
from utils.restaurant_fetcher import fetch_restaurants
import asyncio  # Importar asyncio para manejar tareas asíncronas

class Game:
    def __init__(self, leader_location, room):
        self.leader_location = leader_location
        self.room = room
        self.restaurants = []
        self.votes = {}  # {restaurant_id: {username: vote}}
        self.total_votes_needed = 0  # Cantidad total de votos requeridos (usuarios * restaurantes)
        self.timer_task = None  # Referencia a la tarea del temporizador
        self.game_ended = False  # Para evitar terminar el juego más de una vez

    async def start(self):
        """
        Inicia el juego obteniendo todos los restaurantes, enviando mensajes de inicio y
        restaurantes, y comenzando el temporizador.
        """
        # Obtener todos los restaurantes de forma síncrona
        raw_restaurants = fetch_restaurants(self.leader_location)
        self.restaurants = [Restaurant(**r.to_dict()) for r in raw_restaurants]

        # Inicializar el diccionario de votos para cada restaurante
        for r in self.restaurants:
            self.votes[r.id] = {}

        # Calcular la cantidad total de votos esperada
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

        # Iniciar temporizador: 10 segundos por cada restaurante
        self.timer_task = asyncio.create_task(self.end_game_in_x_seconds(num_restaurants))

    async def end_game_in_x_seconds(self, num_restaurants):
        """
        Espera un tiempo determinado (10 segundos por restaurante) y termina el juego
        si aún no se ha finalizado.
        """
        await asyncio.sleep(num_restaurants * 10)
        if not self.game_ended:
            await self.end_game()

    async def register_vote(self, username, vote, restaurant_id):
        """
        Registra el voto de un usuario para un restaurante específico.
        Solo se registra el primer voto de cada usuario por restaurante.
        Si se han recibido todos los votos necesarios, termina el juego anticipadamente.
        """

        # Validar que el restaurante exista
        if restaurant_id not in self.votes:
            # Opcional: Puedes manejar este caso según tus necesidades
            return

        # Registrar el voto sólo si el usuario no ha votado antes a ese restaurante
        if username not in self.votes[restaurant_id]:
            self.votes[restaurant_id][username] = vote

            # Contar total de votos realizados hasta ahora
            total_cast_votes = sum(len(user_votes) for user_votes in self.votes.values())

            # Verificar si se han recibido todos los votos necesarios
            if total_cast_votes >= self.total_votes_needed:
                if self.timer_task:
                    self.timer_task.cancel()  # Cancelar el temporizador si todavía está en curso
                await self.end_game()
        else:
            # Opcional: Puedes notificar al usuario que ya ha votado para este restaurante
            pass

    async def end_game(self):
        """
        Termina el juego calculando los resultados y enviando el mensaje correspondiente.
        Asegura que el juego solo termine una vez.
        """
        if self.game_ended:
            return  # Si ya se ha terminado, no hacer nada.
        self.game_ended = True

        # Calcular resultados: cuántos 'likes' tiene cada restaurante
        results = {}
        for r in self.restaurants:
            # Lista de usuarios que han dado like ('0' significa like)
            likes = [user for user, v in self.votes[r.id].items() if v == '0']
            results[r.name] = likes

        # Enviar mensaje con los resultados del juego
        await self.room.broadcast_json({
            "id": 0,
            "message": f"GAME_RESULTS.{results}",
            "timestamp": int(time.time() * 1000)
        })

        # Limpiar la referencia al juego en la sala
        self.room.game = None