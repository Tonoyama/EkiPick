import requests
import urllib.parse
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def get_latlon_from_address(address: str) -> Tuple[Optional[float], Optional[float]]:
    """
    住所から緯度・経度を取得
    国土地理院のAPIを使用

    Args:
        address: 住所文字列

    Returns:
        (緯度, 経度) のタプル。取得失敗時は (None, None)
    """
    try:
        base_url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
        quoted = urllib.parse.quote(address)
        response = requests.get(base_url + quoted, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0 and "geometry" in data[0]:
            lon, lat = data[0]["geometry"]["coordinates"]
            return lat, lon
    except Exception as e:
        logger.error(f"住所変換エラー（{address}）: {e}")

    return None, None


def get_address_info(address: str) -> dict:
    """
    住所から詳細情報を取得

    Args:
        address: 住所文字列

    Returns:
        住所情報の辞書
    """
    try:
        base_url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
        quoted = urllib.parse.quote(address)
        response = requests.get(base_url + quoted, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            result = data[0]
            lon, lat = result["geometry"]["coordinates"]

            return {
                "address": address,
                "latitude": lat,
                "longitude": lon,
                "title": result.get("properties", {}).get("title", ""),
                "full_address": result.get("properties", {}).get("title", address)
            }
    except Exception as e:
        logger.error(f"住所情報取得エラー（{address}）: {e}")

    return {
        "address": address,
        "latitude": None,
        "longitude": None,
        "error": "住所情報を取得できませんでした"
    }