import os
from models.restaurant import Restaurant  # Importar el modelo Restaurant

"""
import requests
# API Key de Google Maps cargada desde variables de entorno
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
"""

BASE_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

def fetch_restaurants(location, radius=1000, keyword="restaurant"):
    """
    Obtiene restaurantes cercanos a una ubicación utilizando la API de Google Places.

    :param location: String de la ubicación en formato "lat,lng"
    :param radius: Radio de búsqueda en metros (por defecto 1000m)
    :param keyword: Tipo de lugar a buscar (por defecto "restaurant")
    :return: Lista de objetos Restaurant
    """

    """
    params = {
        "location": location,
        "radius": radius,
        "keyword": keyword,
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])

        restaurants = []
        for r in results:
            restaurant = Restaurant(
                id=r.get("place_id"),
                name=r.get("name"),
                description=r.get("vicinity", "No description available"),
                photo_url=get_photo_url(r.get("photos", []))
            )
            restaurants.append(restaurant)
        """

    return [
        Restaurant(
            id="1",
            name="Restaurante Prueba 1113",
            description="Un restaurante de prueba.",
            photo_url="https://via.placeholder.com/400"
        ),
        Restaurant(
            id="2",
            name="Restaurante Prueba 2",
            description="Otro restaurante de prueba.",
            photo_url="https://via.placeholder.com/400"
        ),
        Restaurant(
            id="3",
            name="Restaurante Prueba 3",
            description="Más datos de prueba.",
            photo_url="https://via.placeholder.com/400"
        ),
    ]

    """
    except requests.exceptions.RequestException as e:
        print(f"Error fetching restaurants: {e}")
        return []
    """


"""
def get_photo_url(photos):

    ""
    Genera la URL de una foto usando la API de Google Places.

    :param photos: Lista de fotos obtenida de un lugar
    :return: URL de la primera foto si existe, o cadena vacía si no hay fotos
    ""
    
    if photos:
        photo_reference = photos[0].get("photo_reference")
        if photo_reference:
            return (
                f"https://maps.googleapis.com/maps/api/place/photo?"
                f"maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
            )
    return ""
"""