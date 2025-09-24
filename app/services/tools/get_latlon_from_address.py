import urllib
import requests
import logging
from google.adk.tools import ToolContext
from app.services.global_state import DATA_STORES

logger = logging.getLogger(__name__)

DATA_STORES = {}

def get_latlon_from_address(address: str, tool_context: ToolContext | None = None) -> str:
    """
    住所から緯度・経度を取得してピンを打つためのツール
    国土地理院のAPIを使用

    Args:
        address: 住所文字列・駅名などを入力する

    Returns:
        dict
            lat: value
            lon: value
        if raised Exception, return empty dict
    """

    if tool_context:
        user_id = tool_context._invocation_context.user_id
    
    try:
        base_url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
        quoted = urllib.parse.quote(address)
        response = requests.get(base_url + quoted, timeout=10)
        response.raise_for_status()
        data = response.json()

        
        if data and len(data) > 0 and "geometry" in data[0]:
            for candidate in data:
                lon, lat = candidate["geometry"]["coordinates"]
                name = candidate["properties"]["title"]
                if name == address:
                    break

            if user_id not in DATA_STORES:
                DATA_STORES[user_id] = []
            DATA_STORES[user_id].append(
                {"type": "pin", "lat": lat, "lon": lon, "name": address}
            )
            return f"ご指定された場所名について地図で表示いたします。ユーザーに画面のピンを見るように指示をしてください"
    except Exception as e:
        logger.error(f"住所変換エラー（{address}）: {e}")

    return "エラーが発生しました。ユーザーに検索クエリが失敗したことを伝えてください"
