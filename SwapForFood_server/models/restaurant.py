# restaurant.py
class Restaurant:
    def __init__(self, id: str, name: str, description: str = "No description available", photo_url: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.photo_url = photo_url

    def to_dict(self):
        """
        Convierte la instancia del restaurante a un diccionario.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "photo_url": self.photo_url
        }