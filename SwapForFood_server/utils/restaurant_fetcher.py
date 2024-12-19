import os
import requests
import math
from models.restaurant import Restaurant

# Cargar la API Key desde variable de entorno
API_KEY = "AIzaSyAXxCIuMUbUcGSy6pstHOE1YEKPt6dLpqY"
PLACE_TYPE = "restaurant"
MAX_RESULTS = 2

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radio de la Tierra en km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def get_place_photo_url(photo_reference, max_width=400):
    base_url = "https://maps.googleapis.com/maps/api/place/photo"
    photo_url = (f"{base_url}?maxwidth={max_width}"
                 f"&photoreference={photo_reference}"
                 f"&key={API_KEY}")
    return photo_url

def nearby_search(api_key, latitude, longitude, place_type, rankby="distance"):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{latitude},{longitude}",
        "type": place_type,
        "rankby": rankby,
        "key": api_key
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error en la solicitud Nearby Search: {response.status_code}")

    data = response.json()

    if data.get("status") not in ["OK", "ZERO_RESULTS"]:
        raise Exception(f"Error en la respuesta Nearby Search: {data.get('status')}")

    return data.get("results", [])

def fetch_restaurants(location, offline=False):
    """
    Obtiene restaurantes cercanos a una ubicación. Si offline=True, devuelve datos de prueba.
    Si offline=False, utiliza la API de Google Places.
    :param location: String "lat,lng"
    :param offline: Bool que indica si usar datos offline o la API real.
    :return: Lista de objetos Restaurant
    """
    if offline:
        # Datos de prueba offline
        return [
            Restaurant(
                id="1",
                name="Restaurante Prueba 1113",
                rating="4.0",
                distance="0.50",
                photo_url="https://via.placeholder.com/400"
            ),
            Restaurant(
                id="27",
                name="Restaurante Prueba 2",
                rating="3.2",
                distance="1.20",
                photo_url="https://via.placeholder.com/400"
            ),
            Restaurant(
                id="3",
                name="Restaurante Prueba 3",
                rating="4.8",
                distance="2.10",
                photo_url="https://via.placeholder.com/400"
            ),
            Restaurant(
                id="4",
                name="Restaurante Prueba 4444",
                rating="2.5",
                distance="0.75",
                photo_url="https://via.placeholder.com/400"
            ),
        ]
    else:
        # Modo online utilizando la API de Google Places
        lat_str, lng_str = location.split(",")
        lat = float(lat_str.strip())
        lng = float(lng_str.strip())

        resultados = nearby_search(API_KEY, lat, lng, PLACE_TYPE)
        if not resultados:
            return []

        # Tomar los primeros MAX_RESULTS
        restaurantes = resultados[:MAX_RESULTS]

        lista_restaurantes = []
        for r in restaurantes:
            nombre = r.get("name", "Sin nombre disponible")
            place_id = r.get("place_id", "")
            rating = r.get("rating")
            if rating is None:
                rating_str = "N/A"
            else:
                rating_str = f"{rating}"

            photos = r.get("photos")
            if photos and photos[0].get("photo_reference"):
                photo_url = get_place_photo_url(photos[0].get("photo_reference"))
            else:
                photo_url = ""

            loc = r.get("geometry", {}).get("location", {})
            lat_rest = loc.get("lat")
            lng_rest = loc.get("lng")
            distance_str = ""
            if lat_rest is not None and lng_rest is not None:
                distancia = haversine_distance(lat, lng, lat_rest, lng_rest)
                distance_str = f"{distancia:.2f}"

            lista_restaurantes.append(
                Restaurant(
                    id=place_id,
                    name=nombre,
                    rating=rating_str,
                    distance=distance_str,
                    photo_url=photo_url
                )
            )

        return lista_restaurantes