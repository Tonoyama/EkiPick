"""
災害リスクデータ取得サービス
国土地理院ハザードマップポータルサイトのAPIを利用
"""

import requests
from PIL import Image
from io import BytesIO
import mercantile
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 各災害データのタイルURL
HAZARD_TILE_URLS = {
    "flood_l1": "https://disaportaldata.gsi.go.jp/raster/01_flood_l1_shinsuishin_newlegend_data/{z}/{x}/{y}.png",
    "flood_l2": "https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png",
    "inland_flood": "https://disaportaldata.gsi.go.jp/raster/02_naisui_data/{z}/{x}/{y}.png",
    "storm_surge": "https://disaportaldata.gsi.go.jp/raster/03_hightide_l2_shinsuishin_data/{z}/{x}/{y}.png",
    "tsunami": "https://disaportaldata.gsi.go.jp/raster/04_tsunami_newlegend_data/{z}/{x}/{y}.png",
    "landslide_debris": "https://disaportaldata.gsi.go.jp/raster/05_dosekiryukeikaikuiki/{z}/{x}/{y}.png",
    "landslide_slope": "https://disaportaldata.gsi.go.jp/raster/05_kyukeishakeikaikuiki/{z}/{x}/{y}.png",
    "landslide_slide": "https://disaportaldata.gsi.go.jp/raster/05_jisuberikeikaikuiki/{z}/{x}/{y}.png",
    "avalanche": "https://disaportaldata.gsi.go.jp/raster/05_nadarekikenkasyo/{z}/{x}/{y}.png"
}

# 洪水・内水氾濫用の色深度マップ
FLOOD_COLOR_DEPTH_MAP = {
    (247, 245, 169): "0.5m未満",
    (255, 216, 192): "0.5-1.0m",
    (255, 183, 183): "1.0-2.0m",
    (255, 145, 145): "2.0-3.0m",
    (242, 133, 201): "3.0-5.0m",
    (220, 122, 220): "5.0m以上"
}

# 津波・高潮用の色深度マップ
TSUNAMI_COLOR_DEPTH_MAP = {
    (247, 245, 169): "0.5m未満",
    (255, 216, 192): "0.5-3.0m",
    (255, 183, 183): "3.0-5.0m",
    (255, 145, 145): "5.0-10.0m",
    (242, 133, 201): "10.0-20.0m",
    (220, 122, 220): "20.0m以上"
}

# 土砂災害警戒区域用の色判定
LANDSLIDE_COLOR_MAP = {
    (255, 0, 0): "特別警戒区域",     # 赤
    (255, 255, 0): "警戒区域",       # 黄
    (255, 204, 0): "警戒区域",       # 黄色系
    (255, 153, 0): "特別警戒区域",   # 赤系
}

# 雪崩危険箇所の色
AVALANCHE_COLORS = [
    (255, 255, 0),  # 黄色
    (255, 204, 0),  # 黄色系
]


class HazardService:
    """災害リスクデータ取得サービス"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'A2A-Estate-HazardService/1.0'
        })

    def get_tile_image(self, url: str) -> Optional[Image.Image]:
        """タイル画像を取得"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content)).convert("RGB")
            return None
        except Exception as e:
            logger.error(f"タイル画像取得エラー: {url} - {e}")
            return None

    def get_pixel_from_coords(
        self,
        lat: float,
        lon: float,
        image: Image.Image,
        tile: mercantile.Tile
    ) -> Tuple[int, int, int]:
        """緯度経度から該当ピクセルの色を取得"""
        bounds = mercantile.bounds(tile)
        x_ratio = (lon - bounds.west) / (bounds.east - bounds.west)
        y_ratio = (bounds.north - lat) / (bounds.north - bounds.south)
        px = min(max(int(x_ratio * 256), 0), 255)
        py = min(max(int(y_ratio * 256), 0), 255)
        return image.getpixel((px, py))

    def estimate_flood_risk(self, lat: float, lon: float, level: str = "l1") -> str:
        """洪水リスクを判定（L1:計画規模、L2:想定最大規模）"""
        try:
            tile = mercantile.tile(lon, lat, 14)
            url_key = f"flood_{level}"
            if url_key not in HAZARD_TILE_URLS:
                return "データなし"

            url = HAZARD_TILE_URLS[url_key].format(z=tile.z, x=tile.x, y=tile.y)
            image = self.get_tile_image(url)
            if not image:
                return "データ取得失敗"

            color = self.get_pixel_from_coords(lat, lon, image, tile)
            return FLOOD_COLOR_DEPTH_MAP.get(color, "対象外")

        except Exception as e:
            logger.error(f"洪水リスク判定エラー: {e}")
            return "判定エラー"

    def estimate_inland_flood_risk(self, lat: float, lon: float) -> str:
        """内水氾濫リスクを判定"""
        try:
            tile = mercantile.tile(lon, lat, 14)
            url = HAZARD_TILE_URLS["inland_flood"].format(z=tile.z, x=tile.x, y=tile.y)
            image = self.get_tile_image(url)
            if not image:
                return "データ取得失敗"

            color = self.get_pixel_from_coords(lat, lon, image, tile)
            return FLOOD_COLOR_DEPTH_MAP.get(color, "対象外")

        except Exception as e:
            logger.error(f"内水氾濫リスク判定エラー: {e}")
            return "判定エラー"

    def estimate_storm_surge_risk(self, lat: float, lon: float) -> str:
        """高潮リスクを判定"""
        try:
            tile = mercantile.tile(lon, lat, 14)
            url = HAZARD_TILE_URLS["storm_surge"].format(z=tile.z, x=tile.x, y=tile.y)
            image = self.get_tile_image(url)
            if not image:
                return "データ取得失敗"

            color = self.get_pixel_from_coords(lat, lon, image, tile)
            return TSUNAMI_COLOR_DEPTH_MAP.get(color, "対象外")

        except Exception as e:
            logger.error(f"高潮リスク判定エラー: {e}")
            return "判定エラー"

    def estimate_tsunami_risk(self, lat: float, lon: float) -> str:
        """津波リスクを判定"""
        try:
            tile = mercantile.tile(lon, lat, 14)
            url = HAZARD_TILE_URLS["tsunami"].format(z=tile.z, x=tile.x, y=tile.y)
            image = self.get_tile_image(url)
            if not image:
                return "データ取得失敗"

            color = self.get_pixel_from_coords(lat, lon, image, tile)
            return TSUNAMI_COLOR_DEPTH_MAP.get(color, "対象外")

        except Exception as e:
            logger.error(f"津波リスク判定エラー: {e}")
            return "判定エラー"

    def check_landslide_zones(self, lat: float, lon: float) -> List[str]:
        """土砂災害警戒区域を判定"""
        zones = []
        zone_types = {
            "landslide_debris": "土石流",
            "landslide_slope": "急傾斜地崩壊",
            "landslide_slide": "地すべり"
        }

        try:
            tile = mercantile.tile(lon, lat, 14)

            for zone_key, zone_name in zone_types.items():
                url = HAZARD_TILE_URLS[zone_key].format(z=tile.z, x=tile.x, y=tile.y)
                image = self.get_tile_image(url)
                if not image:
                    continue

                color = self.get_pixel_from_coords(lat, lon, image, tile)

                # 赤または黄色の判定（RGB値の範囲で判定）
                r, g, b = color
                if r > 200 and g < 100 and b < 100:  # 赤系
                    zones.append(f"{zone_name}：特別警戒区域")
                elif r > 200 and g > 200 and b < 100:  # 黄系
                    zones.append(f"{zone_name}：警戒区域")

            return zones if zones else ["対象外"]

        except Exception as e:
            logger.error(f"土砂災害警戒区域判定エラー: {e}")
            return ["判定エラー"]

    def check_avalanche_risk(self, lat: float, lon: float) -> bool:
        """雪崩危険箇所を判定"""
        try:
            tile = mercantile.tile(lon, lat, 14)
            url = HAZARD_TILE_URLS["avalanche"].format(z=tile.z, x=tile.x, y=tile.y)
            image = self.get_tile_image(url)
            if not image:
                return False

            color = self.get_pixel_from_coords(lat, lon, image, tile)

            # 黄色系の色かチェック
            r, g, b = color
            if r > 200 and g > 200 and b < 100:  # 黄色系
                return True

            return False

        except Exception as e:
            logger.error(f"雪崩危険箇所判定エラー: {e}")
            return False

    def get_all_risks(self, lat: float, lon: float) -> Dict[str, Any]:
        """指定地点の全災害リスクを取得"""
        return {
            "location": {
                "lat": lat,
                "lon": lon
            },
            "flood": {
                "L1_depth": self.estimate_flood_risk(lat, lon, "l1"),
                "L2_depth": self.estimate_flood_risk(lat, lon, "l2")
            },
            "inland_flood": {
                "depth": self.estimate_inland_flood_risk(lat, lon)
            },
            "storm_surge": {
                "depth": self.estimate_storm_surge_risk(lat, lon)
            },
            "tsunami": {
                "depth": self.estimate_tsunami_risk(lat, lon)
            },
            "landslide": self.check_landslide_zones(lat, lon),
            "avalanche": self.check_avalanche_risk(lat, lon)
        }


# シングルトンインスタンス
hazard_service = HazardService()