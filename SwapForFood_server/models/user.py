class User:
    def __init__(self, websocket):
        self.websocket = websocket
        self.username = None
        self.is_leader = False
