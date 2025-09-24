"""
駅探索API
NAVITIME Reachable APIとGoogle Maps APIを組み合わせた総合的な駅探索機能
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from ..database import get_db
from ..models import User, SavedPin
from ..services.reachable_service import ReachableService
from ..services.places_service import PlacesService
from .auth import get_current_user
from .stations import load_station_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/explore", tags=["explore"])


class ExploreRequest(BaseModel):
    """駅探索リクエスト"""
    station_name: str
    time_limit: int = 30  # 分
    search_radius: int = 1500  # メートル
    analyze_places: bool = True
    save_pins: bool = False


class StationExploreResponse(BaseModel):
    """駅探索レスポンス"""
    origin_station: str
    reachable_stations: List[Dict[str, Any]]
    total_stations: int
    zones: Dict[str, List[Dict[str, Any]]]
    area_characteristics: Optional[Dict[str, Any]] = None


class OptimalStationsRequest(BaseModel):
    """最適駅検索リクエスト"""
    station_name: str
    max_travel_time: int = 30
    max_rent: Optional[float] = None
    min_rent: Optional[float] = None
    layouts: Optional[List[str]] = None
    analyze_places: bool = True


@router.post("/reachable", response_model=StationExploreResponse)
async def explore_reachable_stations(
    request: ExploreRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    指定駅から到達可能な駅を探索
    """
    reachable_service = ReachableService()

    # 到達可能駅を取得
    reachable_result = await reachable_service.search_reachable_stations(
        station_name=request.station_name,
        time_limit=request.time_limit
    )

    if "error" in reachable_result:
        # エラーの場合はCSVデータから近隣駅を取得
        stations = load_station_data()
        origin_stations = [s for s in stations if s["station_name"] == request.station_name]

        if not origin_stations:
            raise HTTPException(status_code=404, detail=f"駅 '{request.station_name}' が見つかりません")

        origin = origin_stations[0]
        reachable_stations = []

        # 簡易的に近隣駅を計算
        for station in stations:
            if station["station_name"] != request.station_name:
                # 距離を簡易計算
                distance = ((origin["coord_lat"] - station["coord_lat"]) ** 2 +
                           (origin["coord_lon"] - station["coord_lon"]) ** 2) ** 0.5

                # 距離から推定時間を計算（簡易的に）
                estimated_time = int(distance * 500)  # 適当な係数

                if estimated_time <= request.time_limit:
                    reachable_stations.append({
                        "station_name": station["station_name"],
                        "line_name": station["line_name"],
                        "travel_time": estimated_time,
                        "coord_lat": station["coord_lat"],
                        "coord_lon": station["coord_lon"],
                        "average_rent": station["average_rent"],
                        "is_terminal": station["is_terminal"]
                    })

        # 重複を削除
        seen = set()
        unique_stations = []
        for station in reachable_stations:
            key = station["station_name"]
            if key not in seen:
                seen.add(key)
                unique_stations.append(station)

        reachable_result = {
            "origin_station": request.station_name,
            "time_limit": request.time_limit,
            "total_stations": len(unique_stations),
            "reachable_stations": sorted(unique_stations, key=lambda x: x["travel_time"])[:30],
            "zones": categorize_by_time(unique_stations)
        }

    # 必要に応じて周辺施設情報を取得
    area_characteristics = None
    if request.analyze_places and origin_stations:
        places_service = PlacesService()
        area_characteristics = await places_service.analyze_area_characteristics(
            lat=origin["coord_lat"],
            lon=origin["coord_lon"],
            radius=request.search_radius
        )

    # ユーザーがログインしていて、ピン保存を希望する場合
    if current_user and request.save_pins and reachable_result.get("reachable_stations"):
        saved_count = 0
        for station in reachable_result["reachable_stations"][:10]:  # 上位10駅を保存
            existing_pin = db.query(SavedPin).filter(
                SavedPin.user_id == current_user.id,
                SavedPin.station_name == station["station_name"]
            ).first()

            if not existing_pin:
                new_pin = SavedPin(
                    user_id=current_user.id,
                    station_name=station["station_name"],
                    line_name=station.get("line_name"),
                    coord_lat=station.get("coord_lat", 0),
                    coord_lon=station.get("coord_lon", 0),
                    reachable_stations=[reachable_result["origin_station"]],
                    average_rent=station.get("average_rent"),
                    conversation_context=f"「{request.station_name}」から{request.time_limit}分以内で到達可能",
                    tags=["reachable", f"from_{request.station_name}"]
                )
                db.add(new_pin)
                saved_count += 1

        if saved_count > 0:
            db.commit()
            logger.info(f"Saved {saved_count} pins for user {current_user.id}")

    return StationExploreResponse(
        origin_station=reachable_result["origin_station"],
        reachable_stations=reachable_result["reachable_stations"],
        total_stations=reachable_result["total_stations"],
        zones=reachable_result["zones"],
        area_characteristics=area_characteristics
    )


@router.post("/optimal")
async def find_optimal_stations(
    request: OptimalStationsRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    条件に合う最適な駅を検索
    """
    # CSVデータから駅情報と家賃データを取得
    stations_data = load_station_data()

    # 駅別の平均家賃を計算
    rent_by_station = {}
    for station in stations_data:
        name = station["station_name"]
        if request.layouts and station["layout"] not in request.layouts:
            continue

        if name not in rent_by_station:
            rent_by_station[name] = []
        rent_by_station[name].append(station["average_rent"])

    # 平均を計算
    average_rents = {
        name: sum(rents) / len(rents)
        for name, rents in rent_by_station.items()
    }

    # ReachableServiceを使用して最適駅を検索
    reachable_service = ReachableService()
    optimal_stations = await reachable_service.find_optimal_stations(
        station_name=request.station_name,
        max_travel_time=request.max_travel_time,
        max_rent=request.max_rent,
        min_rent=request.min_rent,
        rent_data=average_rents
    )

    # CSVデータで補完（ReachableAPIが使えない場合）
    if not optimal_stations:
        origin_stations = [s for s in stations_data if s["station_name"] == request.station_name]
        if not origin_stations:
            raise HTTPException(status_code=404, detail=f"駅 '{request.station_name}' が見つかりません")

        origin = origin_stations[0]
        optimal_stations = []

        for name, avg_rent in average_rents.items():
            if request.max_rent and avg_rent > request.max_rent:
                continue
            if request.min_rent and avg_rent < request.min_rent:
                continue

            # 該当駅の情報を取得
            station_info = next((s for s in stations_data if s["station_name"] == name), None)
            if station_info:
                # 簡易的な距離計算
                distance = ((origin["coord_lat"] - station_info["coord_lat"]) ** 2 +
                           (origin["coord_lon"] - station_info["coord_lon"]) ** 2) ** 0.5
                estimated_time = int(distance * 500)

                if estimated_time <= request.max_travel_time:
                    optimal_stations.append({
                        "station_name": name,
                        "line_name": station_info["line_name"],
                        "travel_time": estimated_time,
                        "average_rent": avg_rent,
                        "coord_lat": station_info["coord_lat"],
                        "coord_lon": station_info["coord_lon"],
                        "optimization_score": 0.5  # 仮のスコア
                    })

        # スコアを再計算
        if optimal_stations:
            max_time = max(s["travel_time"] for s in optimal_stations)
            max_rent_val = max(s["average_rent"] for s in optimal_stations)

            for station in optimal_stations:
                time_score = 1 - (station["travel_time"] / max_time) if max_time > 0 else 0.5
                rent_score = 1 - (station["average_rent"] / max_rent_val) if max_rent_val > 0 else 0.5
                station["optimization_score"] = (time_score * 0.6 + rent_score * 0.4)

            optimal_stations.sort(key=lambda x: x["optimization_score"], reverse=True)
            optimal_stations = optimal_stations[:20]

    # 周辺施設情報を追加
    if request.analyze_places and optimal_stations:
        places_service = PlacesService()
        for station in optimal_stations[:5]:  # 上位5駅のみ
            if "coord_lat" in station and "coord_lon" in station:
                area_info = await places_service.analyze_area_characteristics(
                    lat=station["coord_lat"],
                    lon=station["coord_lon"],
                    radius=1000
                )
                station["area_characteristics"] = area_info["characteristics"]
                station["area_tags"] = area_info["characteristics"].get("tags", [])

    return {
        "origin_station": request.station_name,
        "search_criteria": {
            "max_travel_time": request.max_travel_time,
            "max_rent": request.max_rent,
            "min_rent": request.min_rent,
            "layouts": request.layouts
        },
        "total_results": len(optimal_stations),
        "optimal_stations": optimal_stations
    }


@router.get("/station/{station_name}/places")
async def get_station_places(
    station_name: str,
    radius: int = Query(1000, description="検索半径（メートル）"),
    place_types: Optional[List[str]] = Query(None, description="施設タイプ"),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    駅周辺の施設情報を取得
    """
    # CSVデータから駅の座標を取得
    stations = load_station_data()
    station_data = next((s for s in stations if s["station_name"] == station_name), None)

    if not station_data:
        raise HTTPException(status_code=404, detail=f"駅 '{station_name}' が見つかりません")

    # 周辺施設を検索
    places_service = PlacesService()
    places_result = await places_service.search_nearby_places(
        lat=station_data["coord_lat"],
        lon=station_data["coord_lon"],
        radius=radius,
        place_types=place_types
    )

    # エリア特性も分析
    area_analysis = await places_service.analyze_area_characteristics(
        lat=station_data["coord_lat"],
        lon=station_data["coord_lon"],
        radius=radius
    )

    return {
        "station": {
            "name": station_name,
            "line": station_data["line_name"],
            "coord_lat": station_data["coord_lat"],
            "coord_lon": station_data["coord_lon"],
            "average_rent": station_data["average_rent"]
        },
        "places": places_result,
        "area_analysis": area_analysis
    }


def categorize_by_time(stations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
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
        time = station.get("travel_time", 0)
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