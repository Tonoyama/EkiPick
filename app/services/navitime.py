import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

RAPID_HOST = "navitime-route-totalnavi.p.rapidapi.com"

# 運賃区分のマッピング
FARE_UNITS: Dict[str, str] = {
    "0": "普通運賃（乗車券）",
    "1": "自由席特急料金",
    "2": "指定席特急料金",
    "3": "グリーン特急料金",
    "48": "IC運賃",
    "128": "通勤定期1ヶ月",
    "130": "通勤定期3ヶ月",
    "133": "通勤定期6ヶ月",
}


class NavitimeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("RAPIDAPI_KEY", "")
        if not self.api_key:
            logger.warning("NAVITIME API key not set - please configure RAPIDAPI_KEY environment variable")

    def _headers(self) -> Dict[str, str]:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": RAPID_HOST,
        }

    def _http_get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """HTTPリクエストを実行"""
        url = f"https://{RAPID_HOST}{path}"
        try:
            logger.info(f"NAVITIME API Request: {url}")
            logger.debug(f"Headers: {self._headers()}")
            logger.debug(f"Params: {params}")

            r = requests.get(url, headers=self._headers(), params=params, timeout=30)
            r.raise_for_status()

            # レスポンスをログに記録
            response_text = r.text
            logger.info(f"NAVITIME API Status Code: {r.status_code}")
            logger.info(f"NAVITIME API Response Headers: {dict(r.headers)}")
            logger.info(f"NAVITIME API Response (first 1000 chars): {response_text[:1000]}")

            # JSON パースを試みる
            try:
                json_response = r.json()
                logger.info(f"NAVITIME API JSON parsed successfully. Type: {type(json_response)}")
                return json_response
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response text: {response_text[:1000]}")
                return {}

        except requests.HTTPError as e:
            logger.error(f"NAVITIME API Error: {e}")
            logger.error(f"Response: {r.text[:500] if 'r' in locals() else 'N/A'}")
            raise
        except Exception as e:
            logger.error(f"NAVITIME API Request Failed: {e}")
            raise

    def get_route_transit(
        self,
        start: str,
        goal: str,
        start_time: str,
        order: str = "time",
        limit: int = 3,
        shape: bool = False,
    ) -> Dict[str, Any]:
        """
        経路検索（電車・バス）

        Args:
            start: 出発地点 "lat,lon" または場所ID
            goal: 到着地点 "lat,lon" または場所ID
            start_time: 出発時刻 (例: 2025-09-22T08:30:00)
            order: ソート順 (time/fare/transit/walk_distance等)
            limit: 取得する経路数
            shape: 経路形状を含めるか

        Returns:
            経路検索結果
        """
        params = {
            "start": start,
            "goal": goal,
            "start_time": start_time,
            "order": order,
            "limit": str(limit),
            "shape": str(shape).lower(),
        }
        return self._http_get("/route_transit", params)

    def parse_route_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        経路検索結果をパース

        Args:
            data: NAVITIME APIのレスポンス

        Returns:
            パースされた経路情報のリスト
        """
        results = []

        try:
            # データが文字列の場合はエラー
            if isinstance(data, str):
                logger.error(f"Unexpected string response: {data[:500]}")
                return []

            # データが辞書でない場合もエラー
            if not isinstance(data, dict):
                logger.error(f"Unexpected response type: {type(data)}. Data: {str(data)[:500]}")
                return []

            items = data.get("items", [])
            for item in items:
                logger.debug(f"Processing item type: {type(item)}, item: {item if not isinstance(item, str) else item[:100]}")

                if isinstance(item, str):
                    logger.error(f"Item is a string, not a dict: {item[:200]}")
                    continue

                summary = item.get("summary", {})
                move = summary.get("move", {})

                # 運賃情報をラベル化
                fare_raw = move.get("fare", {})
                fare_labeled = self._labelize_fare(fare_raw)

                # 通勤定期を除外した運賃
                fare_without_commuter = {
                    k: v for k, v in fare_labeled.items()
                    if "定期" not in k
                }

                result = {
                    "time_minutes": move.get("time"),
                    "from_time": move.get("from_time"),
                    "to_time": move.get("to_time"),
                    "transfer_count": move.get("transit_count", 0),
                    "walk_distance": move.get("walk_distance"),
                    "total_distance": move.get("distance"),
                    "fare": fare_labeled,
                    "fare_without_commuter": fare_without_commuter,
                    "total_fare": sum(fare_without_commuter.values()) if fare_without_commuter else None,
                    "sections": self._parse_sections(item.get("sections", [])),
                }
                results.append(result)
        except Exception as e:
            import traceback
            logger.error(f"Failed to parse route results: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

        return results

    def _labelize_fare(self, fare: Optional[Dict[str, float]]) -> Dict[str, float]:
        """運賃IDを日本語ラベルに変換"""
        if not fare:
            return {}

        labeled = {}
        for key, value in fare.items():
            if not key.startswith("unit_"):
                labeled[key] = value
                continue

            # unit_ID_... 形式を解析
            unit_id = key[len("unit_"):].split("_")[0]
            name = FARE_UNITS.get(unit_id, f"運賃種別{unit_id}")
            labeled[name] = value

        return labeled

    def _parse_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """区間情報をパース"""
        parsed = []
        for section in sections:
            # セクションが辞書でない場合はスキップ
            if not isinstance(section, dict):
                continue

            # typeがmoveの場合のみ処理
            if section.get("type") == "move":
                parsed.append({
                    "from_name": section.get("from_name"),
                    "to_name": section.get("to_name"),
                    "move_type": section.get("move"),
                    "line_name": section.get("line_name"),
                    "from_time": section.get("from_time"),
                    "to_time": section.get("to_time"),
                    "time": section.get("time"),
                    "distance": section.get("distance"),
                })
            elif section.get("type") == "point":
                # ポイント情報も保持
                parsed.append({
                    "type": "point",
                    "name": section.get("name"),
                    "coord": section.get("coord"),
                })
        return parsed


def calculate_commute_time(
    start_location: str,
    goal_location: str,
    start_time: str = "2025-09-22T08:30:00",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    通勤時間と運賃を計算

    Args:
        start_location: 出発地点 (住所または "lat,lon")
        goal_location: 到着地点 (住所または "lat,lon")
        start_time: 出発時刻
        api_key: NAVITIME API キー

    Returns:
        通勤時間と運賃の情報
    """
    client = NavitimeClient(api_key)

    try:
        # 経路検索
        data = client.get_route_transit(
            start=start_location,
            goal=goal_location,
            start_time=start_time,
            limit=3
        )

        # 結果をパース
        logger.info(f"Calling parse_route_results with data type: {type(data)}")
        routes = client.parse_route_results(data)

        if routes:
            # 最速ルートを取得
            best_route = routes[0]

            return {
                "success": True,
                "best_route": best_route,
                "alternative_routes": routes[1:] if len(routes) > 1 else [],
                "summary": {
                    "min_time": best_route["time_minutes"],
                    "min_fare": best_route["total_fare"],
                    "average_time": sum(r["time_minutes"] for r in routes if r["time_minutes"]) / len(routes),
                    "route_count": len(routes)
                }
            }
        else:
            return {
                "success": False,
                "error": "経路が見つかりませんでした"
            }

    except Exception as e:
        logger.error(f"Failed to calculate commute time: {e}")
        return {
            "success": False,
            "error": str(e)
        }