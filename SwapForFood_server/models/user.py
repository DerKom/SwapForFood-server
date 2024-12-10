class User:
    def __init__(self, websocket):
        self.websocket = websocket
        self.username = None  # Se asignará al recibir el mensaje correspondiente
        self.location = None  # Ubicación del usuario si se requiere
        self.is_leader = False  # Indica si es el líder de la sala
