"""
NAVITIME Reachable API サービス
指定駅から到達可能な駅を検索
"""

import os
from typing import List, Dict, Any, Optional
import httpx
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# RapidAPI設定
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "navitime-reachable.p.rapidapi.com"


class ReachableService:
    """NAVITIME Reachable APIを使用した到達可能駅検索サービス"""

    def __init__(self):
        self.base_url = "https://navitime-reachable.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }

    async def search_reachable_stations(
        self,
        station_name: str,
        time_limit: int = 30,
        transport_types: Optional[List[str]] = None,
        start_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        指定駅から到達可能な駅を検索

        Args:
            station_name: 起点となる駅名
            time_limit: 到達時間制限（分）デフォルト30分
            transport_types: 交通手段（train, walk, busなど）
            start_time: 出発時刻（ISO形式）

        Returns:
            到達可能な駅のリスト
        """
        if not RAPIDAPI_KEY:
            logger.error("RAPIDAPI_KEY is not set - please configure RAPIDAPI_KEY environment variable")
            return {
                "error": "API key is not configured - please set RAPIDAPI_KEY environment variable",
                "reachable_stations": []
            }

        # 駅コードを検索（実際のAPIエンドポイントに合わせて調整が必要）
        station_code = await self._get_station_code(station_name)
        if not station_code:
            return {
                "error": f"Station '{station_name}' not found",
                "reachable_stations": []
            }

        # パラメータの準備
        params = {
            "node": station_code,
            "limit": time_limit,
            "offset": 0,
            "datum": "wgs84",
            "term": "station",
            "coord_unit": "degree"
        }

        if start_time:
            params["start"] = start_time

        if transport_types:
            params["options"] = ",".join(transport_types)
        else:
            params["options"] = "train,walk"  # デフォルトは電車と徒歩

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/reachable_transit/station_list",
                    headers=self.headers,
                    params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_reachable_response(data, station_name, time_limit)
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    return {
                        "error": f"API request failed with status {response.status_code}",
                        "reachable_stations": []
                    }

        except httpx.TimeoutException:
            logger.error("API request timed out")
            return {
                "error": "Request timed out",
                "reachable_stations": []
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "reachable_stations": []
            }

    async def _get_station_code(self, station_name: str) -> Optional[str]:
        """
        駅名から駅コードを取得
        """
        # 駅検索APIを使用（実際のエンドポイントに合わせて調整が必要）
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/station_transit/search",
                    headers=self.headers,
                    params={
                        "word": station_name,
                        "limit": 1
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("items") and len(data["items"]) > 0:
                        return data["items"][0].get("code")

                    # 代替: 駅名から直接コードを生成（簡易実装）
                    return f"station:{station_name}"

        except Exception as e:
            logger.error(f"Failed to get station code: {str(e)}")

        # フォールバック: 駅名をそのまま使用
        return station_name

    def _parse_reachable_response(
        self,
        data: Dict[str, Any],
        origin_station: str,
        time_limit: int
    ) -> Dict[str, Any]:
        """
        APIレスポンスを解析して到達可能駅のリストを生成
        """
        reachable_stations = []

        # レスポンス形式に応じて解析（実際のAPIレスポンス形式に合わせて調整が必要）
        items = data.get("items", [])

        for item in items:
            station_info = {
                "station_name": item.get("name", ""),
                "line_name": item.get("line", ""),
                "travel_time": item.get("time", 0),  # 分
                "distance": item.get("distance", 0),  # メートル
                "coord_lat": item.get("coord", {}).get("lat"),
                "coord_lon": item.get("coord", {}).get("lon"),
                "transport_types": item.get("transport", []),
                "fare": item.get("fare", 0)
            }

            # 起点駅は除外
            if station_info["station_name"] != origin_station:
                reachable_stations.append(station_info)

        # 到達時間でソート
        reachable_stations.sort(key=lambda x: x["travel_time"])

        return {
            "origin_station": origin_station,
            "time_limit": time_limit,
            "total_stations": len(reachable_stations),
            "reachable_stations": reachable_stations,
            "zones": self._categorize_by_time(reachable_stations)
        }

    def _categorize_by_time(self, stations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        到達時間帯別にステーションを分類
        """
        zones = {
            "0-10min": [],
            "10-20min": [],
            "20-30min": [],
            "30-45min": [],
            "45-60min": [],
            "60min+": []
        }

        for station in stations:
            time = station["travel_time"]
            if time <= 10:
                zones["0-10min"].append(station)
            elif time <= 20:
                zones["10-20min"].append(station)
            elif time <= 30:
                zones["20-30min"].append(station)
            elif time <= 45:
                zones["30-45min"].append(station)
            elif time <= 60:
                zones["45-60min"].append(station)
            else:
                zones["60min+"].append(station)

        return zones

    async def get_reachable_with_rent_info(
        self,
        station_name: str,
        time_limit: int = 30,
        rent_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        到達可能駅に家賃情報を付加して返す

        Args:
            station_name: 起点駅名
            time_limit: 到達時間制限（分）
            rent_data: 駅名と家賃のマッピング辞書

        Returns:
            家賃情報付きの到達可能駅リスト
        """
        # 基本の到達可能駅を取得
        result = await self.search_reachable_stations(station_name, time_limit)

        if rent_data and result.get("reachable_stations"):
            # 各駅に家賃情報を付加
            for station in result["reachable_stations"]:
                station_name = station.get("station_name")
                if station_name in rent_data:
                    station["average_rent"] = rent_data[station_name]
                    station["has_rent_data"] = True
                else:
                    station["average_rent"] = None
                    station["has_rent_data"] = False

            # 家賃でもソートオプションを追加
            result["sorted_by_rent"] = sorted(
                [s for s in result["reachable_stations"] if s.get("has_rent_data")],
                key=lambda x: x["average_rent"]
            )

        return result

    async def find_optimal_stations(
        self,
        station_name: str,
        max_travel_time: int = 30,
        max_rent: Optional[float] = None,
        min_rent: Optional[float] = None,
        rent_data: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        条件に合う最適な駅を検索

        Args:
            station_name: 起点駅
            max_travel_time: 最大通勤時間（分）
            max_rent: 最大家賃
            min_rent: 最小家賃
            rent_data: 駅別家賃データ

        Returns:
            条件に合う駅のリスト
        """
        # 到達可能駅を取得
        result = await self.get_reachable_with_rent_info(
            station_name,
            max_travel_time,
            rent_data
        )

        if "error" in result:
            return []

        optimal_stations = []

        for station in result.get("reachable_stations", []):
            # 家賃条件でフィルタリング
            if station.get("has_rent_data"):
                rent = station.get("average_rent", 0)

                if max_rent and rent > max_rent:
                    continue
                if min_rent and rent < min_rent:
                    continue

                # スコアを計算（通勤時間と家賃のバランス）
                time_score = 1 - (station["travel_time"] / max_travel_time)

                if max_rent:
                    rent_score = 1 - (rent / max_rent)
                else:
                    rent_score = 0.5

                station["optimization_score"] = (time_score * 0.6 + rent_score * 0.4)
                optimal_stations.append(station)

        # スコアでソート
        optimal_stations.sort(key=lambda x: x["optimization_score"], reverse=True)

        return optimal_stations[:20]  # 上位20駅を返す