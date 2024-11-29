class User:
    def __init__(self, websocket):
        self.websocket = websocket
        self.username = None  # Puedes asignar un nombre de usuario único
        self.location = None  # Ubicación del usuario
