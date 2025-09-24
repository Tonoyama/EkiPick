import os
import requests
import logging
from app.services.hazard_service import hazard_service

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
MAP_BASE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

logger = logging.getLogger(__name__)

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set. Map functions will be limited.")

def get_station_position(station_name: str) -> tuple[float, float]:
    params = {
        "address": f"{station_name}",
        "language": "ja",
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(MAP_BASE_API_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])
        else:
            return (-1, -1)
    except Exception as e:
        logger.error(f"駅座標取得エラー ({station_name}): {e}")
        return (-1, -1)

def check_hazard_info(station_name: str) -> dict:
    lat, lon = get_station_position(station_name)
    if lat == -1:
        return {
            "result": "error"
        }
    
    return hazard_service.get_all_risks(lat, lon)