class Restaurant:
    def __init__(self, id: str, name: str, rating: str = "N/A", distance: str = "", photo_url: str = ""):
        self.id = id
        self.name = name
        self.rating = rating  # rating en string (ej. "4.5")
        self.distance = distance  # distancia en km en string (ej. "0.07")
        self.photo_url = photo_url

    def to_dict(self):
        """
        Convierte la instancia del restaurante a un diccionario.
        """
        return {
            "id": self.id,
            "name": self.name,
            "rating": self.rating,
            "distance": self.distance,
            "photo_url": self.photo_url
        }
