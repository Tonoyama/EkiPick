"""
駅・路線情報API
CSVファイルから駅と家賃相場情報を提供
"""

import os
import csv
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])

# CSVファイルパス
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'lineinfo.csv')

class StationInfo(BaseModel):
    """駅情報モデル"""
    station_name: str  # 駅名
    prefecture: str  # 都道府県
    station_number: str  # 駅番号
    layout: str  # 間取り
    rent: float  # 家賃(万円)
    average_rent: float  # 家賃相場(万円)
    line_name: str  # 路線名
    time: int  # 時間
    transit_count: int  # 乗換回数
    coord_lat: float  # 緯度
    coord_lon: float  # 経度
    min_time_to_kioicho: float  # 紀尾井町への最短時間
    is_terminal: bool  # 始発
    line_index: int  # 路線内インデックス


def load_station_data() -> List[Dict[str, Any]]:
    """CSVファイルから駅情報を読み込む"""
    stations = []

    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                stations.append({
                    "station_name": row['駅名'],
                    "prefecture": row['都道府県'],
                    "station_number": row['駅番号'],
                    "layout": row['間取り'],
                    "rent": float(row['家賃(万円)']) if row['家賃(万円)'] else 0,
                    "average_rent": float(row['家賃相場(万円)']) if row['家賃相場(万円)'] else 0,
                    "line_name": row['路線名'],
                    "time": int(row['time']) if row['time'] else 0,
                    "transit_count": int(row['transit_count']) if row['transit_count'] else 0,
                    "coord_lat": float(row['coord_lat']) if row['coord_lat'] else 0,
                    "coord_lon": float(row['coord_lon']) if row['coord_lon'] else 0,
                    "min_time_to_kioicho": float(row['min_time_to_kioicho']) if row['min_time_to_kioicho'] else 0,
                    "is_terminal": row['始発'].lower() == 'true' if row['始発'] else False,
                    "line_index": int(row['路線内インデックス']) if row['路線内インデックス'] else 0,
                })
    except FileNotFoundError:
        logger.error(f"CSV file not found: {CSV_FILE_PATH}")
        return []
    except Exception as e:
        logger.error(f"Error loading CSV file: {e}")
        return []

    return stations


@router.get("/", response_model=List[StationInfo])
async def get_all_stations(
    station_name: Optional[str] = Query(None, description="駅名でフィルタ"),
    line_name: Optional[str] = Query(None, description="路線名でフィルタ"),
    layout: Optional[str] = Query(None, description="間取りでフィルタ"),
    max_rent: Optional[float] = Query(None, description="最大家賃（万円）"),
    min_rent: Optional[float] = Query(None, description="最小家賃（万円）"),
    max_time: Optional[int] = Query(None, description="最大時間"),
    limit: int = Query(100, description="取得件数制限"),
    skip: int = Query(0, description="スキップ件数")
):
    """
    駅情報一覧を取得

    クエリパラメータでフィルタリング可能：
    - station_name: 駅名（部分一致）
    - line_name: 路線名（部分一致）
    - layout: 間取り（完全一致）
    - max_rent: 最大家賃
    - min_rent: 最小家賃
    - max_time: 最大時間
    """
    stations = load_station_data()

    # フィルタリング
    if station_name:
        stations = [s for s in stations if station_name in s['station_name']]
    if line_name:
        stations = [s for s in stations if line_name in s['line_name']]
    if layout:
        stations = [s for s in stations if s['layout'] == layout]
    if max_rent is not None:
        stations = [s for s in stations if s['rent'] <= max_rent]
    if min_rent is not None:
        stations = [s for s in stations if s['rent'] >= min_rent]
    if max_time is not None:
        stations = [s for s in stations if s['time'] <= max_time]

    # ページネーション
    total = len(stations)
    stations = stations[skip:skip + limit]

    return stations


@router.get("/stations", response_model=List[Dict[str, Any]])
async def get_unique_stations():
    """
    駅名の一覧を重複なしで取得（座標付き）
    """
    stations = load_station_data()

    # 駅名でグループ化して、座標と路線情報を集約
    station_map = {}
    for station in stations:
        name = station['station_name']
        if name not in station_map:
            station_map[name] = {
                "station_name": name,
                "coord_lat": station['coord_lat'],
                "coord_lon": station['coord_lon'],
                "lines": set(),
                "min_time_to_kioicho": station['min_time_to_kioicho'],
                "is_terminal": station['is_terminal'],
                "average_rent": []
            }
        station_map[name]['lines'].add(station['line_name'])
        station_map[name]['average_rent'].append(station['average_rent'])

    # 結果を整形
    result = []
    for name, data in station_map.items():
        result.append({
            "station_name": name,
            "coord_lat": data['coord_lat'],
            "coord_lon": data['coord_lon'],
            "lines": list(data['lines']),
            "min_time_to_kioicho": data['min_time_to_kioicho'],
            "is_terminal": data['is_terminal'],
            "average_rent": sum(data['average_rent']) / len(data['average_rent']) if data['average_rent'] else 0
        })

    return sorted(result, key=lambda x: x['station_name'])


@router.get("/lines", response_model=List[str])
async def get_lines():
    """
    路線名の一覧を重複なしで取得
    """
    stations = load_station_data()
    lines = set(station['line_name'] for station in stations)
    return sorted(list(lines))


@router.get("/layouts", response_model=List[str])
async def get_layouts():
    """
    間取りの一覧を重複なしで取得
    """
    stations = load_station_data()
    layouts = set(station['layout'] for station in stations)
    return sorted(list(layouts))


@router.get("/station/{station_name}", response_model=List[StationInfo])
async def get_station_by_name(station_name: str):
    """
    特定の駅の全間取り情報を取得
    """
    stations = load_station_data()
    station_data = [s for s in stations if s['station_name'] == station_name]

    if not station_data:
        raise HTTPException(status_code=404, detail=f"Station '{station_name}' not found")

    return station_data


@router.get("/line/{line_name}", response_model=List[StationInfo])
async def get_stations_by_line(
    line_name: str,
    layout: Optional[str] = Query(None, description="間取りでフィルタ")
):
    """
    特定の路線の駅情報を取得
    """
    stations = load_station_data()
    line_stations = [s for s in stations if s['line_name'] == line_name]

    if not line_stations:
        raise HTTPException(status_code=404, detail=f"Line '{line_name}' not found")

    if layout:
        line_stations = [s for s in line_stations if s['layout'] == layout]

    # 路線内インデックスでソート
    line_stations.sort(key=lambda x: x['line_index'])

    return line_stations


@router.get("/search/nearby", response_model=List[Dict[str, Any]])
async def search_nearby_stations(
    lat: float = Query(..., description="緯度"),
    lon: float = Query(..., description="経度"),
    radius_km: float = Query(2.0, description="検索半径（km）")
):
    """
    指定座標から近い駅を検索
    """
    import math

    def haversine_distance(lat1, lon1, lat2, lon2):
        """2点間の距離を計算（km）"""
        R = 6371  # 地球の半径（km）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    stations = load_station_data()

    # 駅ごとにグループ化
    station_map = {}
    for station in stations:
        name = station['station_name']
        if name not in station_map:
            distance = haversine_distance(lat, lon, station['coord_lat'], station['coord_lon'])
            if distance <= radius_km:
                station_map[name] = {
                    "station_name": name,
                    "coord_lat": station['coord_lat'],
                    "coord_lon": station['coord_lon'],
                    "distance_km": round(distance, 2),
                    "lines": set(),
                    "min_time_to_kioicho": station['min_time_to_kioicho']
                }
        if name in station_map:
            station_map[name]['lines'].add(station['line_name'])

    # リストに変換してソート
    result = []
    for data in station_map.values():
        data['lines'] = list(data['lines'])
        result.append(data)

    result.sort(key=lambda x: x['distance_km'])

    return result[:20]  # 最大20件返す