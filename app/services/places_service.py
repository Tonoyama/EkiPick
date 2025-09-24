"""
Google Maps/Search API サービス
駅周辺の施設情報を取得
"""

import os
from typing import List, Dict, Any, Optional
import httpx
import logging
import json

logger = logging.getLogger(__name__)

# Google Maps API設定
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_PLACES_API_URL = "https://maps.googleapis.com/maps/api/place"


class PlacesService:
    """Google Maps Places APIを使用した周辺施設検索サービス"""

    def __init__(self):
        self.api_key = GOOGLE_MAPS_API_KEY
        self.base_url = GOOGLE_PLACES_API_URL

    async def search_nearby_places(
        self,
        lat: float,
        lon: float,
        radius: int = 1000,
        place_types: Optional[List[str]] = None,
        keyword: Optional[str] = None,
        language: str = "ja"
    ) -> Dict[str, Any]:
        """
        指定座標の周辺施設を検索

        Args:
            lat: 緯度
            lon: 経度
            radius: 検索半径（メートル）最大50000
            place_types: 施設タイプ（restaurant, school, hospital等）
            keyword: キーワード検索
            language: 言語設定

        Returns:
            周辺施設のリスト
        """
        if not self.api_key:
            logger.warning("Google Maps API key is not configured, using mock data")
            return self._get_mock_places_data(lat, lon, radius, place_types)

        params = {
            "location": f"{lat},{lon}",
            "radius": min(radius, 50000),
            "language": language,
            "key": self.api_key
        }

        if place_types:
            params["type"] = "|".join(place_types)

        if keyword:
            params["keyword"] = keyword

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/nearbysearch/json",
                    params=params
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_places_response(data, lat, lon)
                else:
                    logger.error(f"Places API request failed: {response.status_code}")
                    return self._get_mock_places_data(lat, lon, radius, place_types)

        except Exception as e:
            logger.error(f"Places API error: {str(e)}")
            return self._get_mock_places_data(lat, lon, radius, place_types)

    def _parse_places_response(self, data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        """
        Places APIレスポンスを解析
        """
        places = []

        for result in data.get("results", []):
            place = {
                "name": result.get("name"),
                "place_id": result.get("place_id"),
                "types": result.get("types", []),
                "rating": result.get("rating"),
                "user_ratings_total": result.get("user_ratings_total"),
                "vicinity": result.get("vicinity"),
                "location": {
                    "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": result.get("geometry", {}).get("location", {}).get("lng")
                },
                "distance": self._calculate_distance(
                    lat, lon,
                    result.get("geometry", {}).get("location", {}).get("lat", lat),
                    result.get("geometry", {}).get("location", {}).get("lng", lon)
                )
            }
            places.append(place)

        # 距離でソート
        places.sort(key=lambda x: x["distance"])

        return {
            "center": {"lat": lat, "lon": lon},
            "total_results": len(places),
            "places": places,
            "categories": self._categorize_places(places)
        }

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        2点間の距離を計算（メートル）
        """
        import math

        R = 6371000  # 地球の半径（メートル）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return round(R * c, 2)

    def _categorize_places(self, places: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        施設をカテゴリ別に分類
        """
        categories = {
            "食事": [],
            "買い物": [],
            "医療": [],
            "教育": [],
            "公共施設": [],
            "レジャー": [],
            "金融": [],
            "その他": []
        }

        category_mapping = {
            "restaurant": "食事",
            "food": "食事",
            "cafe": "食事",
            "meal_takeaway": "食事",
            "supermarket": "買い物",
            "store": "買い物",
            "shopping_mall": "買い物",
            "convenience_store": "買い物",
            "hospital": "医療",
            "doctor": "医療",
            "pharmacy": "医療",
            "dentist": "医療",
            "school": "教育",
            "university": "教育",
            "library": "教育",
            "post_office": "公共施設",
            "police": "公共施設",
            "fire_station": "公共施設",
            "park": "レジャー",
            "gym": "レジャー",
            "movie_theater": "レジャー",
            "bank": "金融",
            "atm": "金融"
        }

        for place in places:
            categorized = False
            for place_type in place.get("types", []):
                if place_type in category_mapping:
                    categories[category_mapping[place_type]].append(place)
                    categorized = True
                    break

            if not categorized:
                categories["その他"].append(place)

        # 空のカテゴリを削除
        return {k: v for k, v in categories.items() if v}

    def _get_mock_places_data(
        self,
        lat: float,
        lon: float,
        radius: int,
        place_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        APIキーがない場合のモックデータを生成
        """
        import random

        mock_places = []
        base_places = [
            {"name": "セブンイレブン", "types": ["convenience_store"], "rating": 4.0},
            {"name": "ファミリーマート", "types": ["convenience_store"], "rating": 3.9},
            {"name": "ローソン", "types": ["convenience_store"], "rating": 4.1},
            {"name": "西友", "types": ["supermarket"], "rating": 3.8},
            {"name": "イトーヨーカドー", "types": ["supermarket"], "rating": 4.2},
            {"name": "マクドナルド", "types": ["restaurant", "food"], "rating": 3.7},
            {"name": "スターバックス", "types": ["cafe"], "rating": 4.3},
            {"name": "ドトールコーヒー", "types": ["cafe"], "rating": 3.9},
            {"name": "公立小学校", "types": ["school"], "rating": 4.0},
            {"name": "総合病院", "types": ["hospital"], "rating": 3.5},
            {"name": "郵便局", "types": ["post_office"], "rating": 3.8},
            {"name": "交番", "types": ["police"], "rating": 4.1},
            {"name": "公園", "types": ["park"], "rating": 4.4},
            {"name": "みずほ銀行ATM", "types": ["atm", "bank"], "rating": 3.6},
            {"name": "三菱UFJ銀行", "types": ["bank"], "rating": 3.7}
        ]

        # 指定されたタイプでフィルタリング
        if place_types:
            filtered_places = []
            for place in base_places:
                for ptype in place["types"]:
                    if ptype in place_types:
                        filtered_places.append(place)
                        break
            base_places = filtered_places if filtered_places else base_places[:5]

        # ランダムに5-10個選択
        selected_places = random.sample(
            base_places,
            min(random.randint(5, 10), len(base_places))
        )

        for i, place_template in enumerate(selected_places):
            # ランダムな位置を生成（指定半径内）
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(100, radius)

            dlat = (distance / 111000) * math.cos(angle)
            dlon = (distance / (111000 * math.cos(math.radians(lat)))) * math.sin(angle)

            place = {
                "name": f"{place_template['name']} 駅前店",
                "place_id": f"mock_place_{i}",
                "types": place_template["types"],
                "rating": place_template["rating"] + random.uniform(-0.3, 0.3),
                "user_ratings_total": random.randint(50, 500),
                "vicinity": f"東京都某区某町{random.randint(1, 5)}-{random.randint(1, 20)}-{random.randint(1, 10)}",
                "location": {
                    "lat": lat + dlat,
                    "lng": lon + dlon
                },
                "distance": distance
            }
            mock_places.append(place)

        # 距離でソート
        mock_places.sort(key=lambda x: x["distance"])

        return {
            "center": {"lat": lat, "lon": lon},
            "total_results": len(mock_places),
            "places": mock_places,
            "categories": self._categorize_places(mock_places),
            "is_mock_data": True
        }

    async def analyze_area_characteristics(
        self,
        lat: float,
        lon: float,
        radius: int = 1500
    ) -> Dict[str, Any]:
        """
        エリアの特性を分析

        Args:
            lat: 緯度
            lon: 経度
            radius: 分析半径（メートル）

        Returns:
            エリア特性の分析結果
        """
        # 複数カテゴリの施設を検索
        categories_to_search = [
            ["convenience_store", "supermarket"],
            ["school", "university"],
            ["hospital", "doctor", "pharmacy"],
            ["restaurant", "cafe"],
            ["park"],
            ["bank", "atm"]
        ]

        all_results = {}
        for category_types in categories_to_search:
            result = await self.search_nearby_places(
                lat, lon, radius,
                place_types=category_types
            )
            for place_type in category_types:
                all_results[place_type] = [
                    p for p in result.get("places", [])
                    if place_type in p.get("types", [])
                ]

        # エリア特性を分析
        characteristics = {
            "convenience": self._calculate_convenience_score(all_results),
            "family_friendly": self._calculate_family_score(all_results),
            "shopping": self._calculate_shopping_score(all_results),
            "medical": self._calculate_medical_score(all_results),
            "tags": self._generate_area_tags(all_results)
        }

        return {
            "location": {"lat": lat, "lon": lon},
            "radius": radius,
            "characteristics": characteristics,
            "facility_counts": {k: len(v) for k, v in all_results.items()},
            "recommendations": self._generate_recommendations(characteristics)
        }

    def _calculate_convenience_score(self, results: Dict) -> float:
        """利便性スコアを計算（0-100）"""
        score = 0
        score += min(len(results.get("convenience_store", [])) * 10, 30)
        score += min(len(results.get("supermarket", [])) * 15, 30)
        score += min(len(results.get("bank", [])) * 10, 20)
        score += min(len(results.get("atm", [])) * 5, 10)
        score += min(len(results.get("restaurant", [])) * 5, 10)
        return min(score, 100)

    def _calculate_family_score(self, results: Dict) -> float:
        """ファミリー向けスコアを計算（0-100）"""
        score = 0
        score += min(len(results.get("school", [])) * 20, 40)
        score += min(len(results.get("park", [])) * 15, 30)
        score += min(len(results.get("hospital", [])) * 15, 20)
        score += min(len(results.get("supermarket", [])) * 5, 10)
        return min(score, 100)

    def _calculate_shopping_score(self, results: Dict) -> float:
        """買い物便利度スコアを計算（0-100）"""
        score = 0
        score += min(len(results.get("supermarket", [])) * 20, 40)
        score += min(len(results.get("convenience_store", [])) * 15, 30)
        score += min(len(results.get("shopping_mall", [])) * 20, 20)
        score += min(len(results.get("store", [])) * 5, 10)
        return min(score, 100)

    def _calculate_medical_score(self, results: Dict) -> float:
        """医療充実度スコアを計算（0-100）"""
        score = 0
        score += min(len(results.get("hospital", [])) * 25, 50)
        score += min(len(results.get("doctor", [])) * 15, 30)
        score += min(len(results.get("pharmacy", [])) * 10, 20)
        return min(score, 100)

    def _generate_area_tags(self, results: Dict) -> List[str]:
        """エリアの特徴タグを生成"""
        tags = []

        if len(results.get("convenience_store", [])) >= 3:
            tags.append("コンビニ充実")
        if len(results.get("supermarket", [])) >= 2:
            tags.append("買い物便利")
        if len(results.get("school", [])) >= 1:
            tags.append("学校近い")
        if len(results.get("park", [])) >= 2:
            tags.append("緑豊か")
        if len(results.get("hospital", [])) >= 1:
            tags.append("医療施設あり")
        if len(results.get("restaurant", [])) >= 5:
            tags.append("飲食店豊富")

        return tags

    def _generate_recommendations(self, characteristics: Dict) -> List[str]:
        """エリアの推奨ポイントを生成"""
        recommendations = []

        if characteristics["convenience"] >= 70:
            recommendations.append("日常生活に便利なエリアです")
        if characteristics["family_friendly"] >= 70:
            recommendations.append("子育て世帯におすすめのエリアです")
        if characteristics["shopping"] >= 70:
            recommendations.append("買い物に困らない立地です")
        if characteristics["medical"] >= 60:
            recommendations.append("医療施設が充実しています")

        if not recommendations:
            recommendations.append("静かで落ち着いた住環境です")

        return recommendations