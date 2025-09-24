import os
import json
import requests
import logging
from google.adk.tools import ToolContext
from app.services.global_state import DATA_STORES
from app.services.send_pin import SendPin

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
logger = logging.getLogger(__name__)

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set. Map functions will be limited.")



def get_nearby_buildings(lat: float, lon: float, radius: int = 1000, place_type: str = "None", tool_context: ToolContext | None = None) -> str:
    """
    Google Places APIを使用して周辺建物情報を取得

    Args:
        lat: 緯度
        lon: 経度
        radius: 検索半径（メートル、デフォルト: 1000m）
        place_type: 建物タイプ (restaurant, hospital, school, bank, etc.)
        None の場合は指定しない

    Returns:
        JSON文字列形式の周辺建物情報
    """

    if tool_context:
        user_id = tool_context._invocation_context.user_id

    if place_type == "None":
        place_type = None
    
    try:
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

        params = {
            "location": f"{lat},{lon}",
            "radius": radius,
            "language": "ja",
            "maxResultCount": 6,
            "key": GOOGLE_MAPS_API_KEY
        }


        # 建物タイプが指定されている場合は追加
        if place_type:
            params["type"] = place_type

        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        buildings = []
        if data.get("status") == "OK" and "results" in data:
            for place in data["results"]:  # 最大20件
                location = place.get("geometry", {}).get("location", {})
                building_info = {
                    "name": place.get("name", ""),
                    "vicinity": place.get("vicinity", ""),
                    "opening_hours": {
                        "open_now": place.get("opening_hours", {}).get("open_now", None)
                    } if place.get("opening_hours") else None,
                }

                if user_id:
                    DATA_STORES.insert_pins(user_id, SendPin(location.get("lat"), location.get("lng"), place.get("name", "")))

                buildings.append(building_info)

        result = {
            "status": "success",
            "message": f"周辺建物情報を{len(buildings)}件取得しました",
            "search_params": {
                "center": {"lat": lat, "lng": lon},
                "radius": radius,
                "type": place_type
            },
            "buildings": buildings
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"周辺建物取得エラー (lat: {lat}, lon: {lon}): {e}")
        error_result = {
            "status": "error",
            "message": f"周辺建物情報の取得に失敗しました: {str(e)}",
            "buildings": []
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

