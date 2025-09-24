import os
import json
import requests
import logging
from app.services.global_state import DATA_STORES
from google.adk.tools import ToolContext
from app.services.send_pin import SendPin

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
MAP_BASE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

logger = logging.getLogger(__name__)

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set. Map functions will be limited.")

def get_station_coordinates(station_name: str, tool_context: ToolContext | None = None) -> str:

    if tool_context:
        user_id = tool_context._invocation_context.user_id


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
            pin = SendPin(lat=location["lat"], lon=location["lng"], name=station_name)
            if user_id:
                DATA_STORES.insert_pins(user_id, pin)
            result = {
                "status": "success",
                "message": f"{station_name}を左側の地図に表示いたします",
            }
        else:
            result = {
                "status": "error",
                "message": f"{station_name}の座標が見つかりませんでした",
            }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"駅座標取得エラー ({station_name}): {e}")
        error_result = {
            "status": "error",
            "message": f"座標取得に失敗しました",
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)