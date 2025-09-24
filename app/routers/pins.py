"""
保存ピン（駅）データ管理API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from ..database import get_db
from ..models import SavedPin, User
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pins", tags=["pins"])


class PinCreate(BaseModel):
    """ピン作成リクエスト"""
    station_name: str
    line_name: Optional[str] = None
    coord_lat: float
    coord_lon: float
    nearby_places: Optional[Dict[str, Any]] = None
    reachable_stations: Optional[List[Dict[str, Any]]] = None
    average_rent: Optional[float] = None
    conversation_context: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class PinUpdate(BaseModel):
    """ピン更新リクエスト"""
    nearby_places: Optional[Dict[str, Any]] = None
    reachable_stations: Optional[List[Dict[str, Any]]] = None
    average_rent: Optional[float] = None
    conversation_context: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class PinResponse(BaseModel):
    """ピンレスポンス"""
    id: int
    user_id: int
    station_name: str
    line_name: Optional[str]
    coord_lat: float
    coord_lon: float
    nearby_places: Optional[Dict[str, Any]]
    reachable_stations: Optional[List[Dict[str, Any]]]
    average_rent: Optional[float]
    conversation_context: Optional[str]
    notes: Optional[str]
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=PinResponse)
async def create_pin(
    pin_data: PinCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """新しいピンを作成"""
    # 既存のピンをチェック
    existing_pin = db.query(SavedPin).filter(
        SavedPin.user_id == current_user.id,
        SavedPin.station_name == pin_data.station_name,
        SavedPin.line_name == pin_data.line_name
    ).first()

    if existing_pin:
        raise HTTPException(
            status_code=400,
            detail=f"駅 {pin_data.station_name} ({pin_data.line_name or '全線'}) は既に保存されています"
        )

    # 新しいピンを作成
    new_pin = SavedPin(
        user_id=current_user.id,
        station_name=pin_data.station_name,
        line_name=pin_data.line_name,
        coord_lat=pin_data.coord_lat,
        coord_lon=pin_data.coord_lon,
        nearby_places=pin_data.nearby_places,
        reachable_stations=pin_data.reachable_stations,
        average_rent=pin_data.average_rent,
        conversation_context=pin_data.conversation_context,
        notes=pin_data.notes,
        tags=pin_data.tags
    )

    db.add(new_pin)
    db.commit()
    db.refresh(new_pin)

    return PinResponse.from_orm(new_pin)


@router.get("/", response_model=List[PinResponse])
async def get_pins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    station_name: Optional[str] = Query(None, description="駅名でフィルタ"),
    line_name: Optional[str] = Query(None, description="路線名でフィルタ"),
    tags: Optional[List[str]] = Query(None, description="タグでフィルタ"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """保存されたピンの一覧を取得"""
    query = db.query(SavedPin).filter(SavedPin.user_id == current_user.id)

    # フィルタリング
    if station_name:
        query = query.filter(SavedPin.station_name.contains(station_name))
    if line_name:
        query = query.filter(SavedPin.line_name.contains(line_name))
    if tags:
        # タグのいずれかを含むピンを取得
        for tag in tags:
            query = query.filter(SavedPin.tags.contains([tag]))

    # ページネーション
    pins = query.order_by(SavedPin.created_at.desc()).offset(skip).limit(limit).all()

    return [PinResponse.from_orm(pin) for pin in pins]


@router.get("/{pin_id}", response_model=PinResponse)
async def get_pin(
    pin_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """特定のピンを取得"""
    pin = db.query(SavedPin).filter(
        SavedPin.id == pin_id,
        SavedPin.user_id == current_user.id
    ).first()

    if not pin:
        raise HTTPException(status_code=404, detail="ピンが見つかりません")

    return PinResponse.from_orm(pin)


@router.put("/{pin_id}", response_model=PinResponse)
async def update_pin(
    pin_id: int,
    pin_update: PinUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ピンを更新"""
    pin = db.query(SavedPin).filter(
        SavedPin.id == pin_id,
        SavedPin.user_id == current_user.id
    ).first()

    if not pin:
        raise HTTPException(status_code=404, detail="ピンが見つかりません")

    # 更新
    if pin_update.nearby_places is not None:
        pin.nearby_places = pin_update.nearby_places
    if pin_update.reachable_stations is not None:
        pin.reachable_stations = pin_update.reachable_stations
    if pin_update.average_rent is not None:
        pin.average_rent = pin_update.average_rent
    if pin_update.conversation_context is not None:
        pin.conversation_context = pin_update.conversation_context
    if pin_update.notes is not None:
        pin.notes = pin_update.notes
    if pin_update.tags is not None:
        pin.tags = pin_update.tags

    pin.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(pin)

    return PinResponse.from_orm(pin)


@router.delete("/{pin_id}")
async def delete_pin(
    pin_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ピンを削除"""
    pin = db.query(SavedPin).filter(
        SavedPin.id == pin_id,
        SavedPin.user_id == current_user.id
    ).first()

    if not pin:
        raise HTTPException(status_code=404, detail="ピンが見つかりません")

    db.delete(pin)
    db.commit()

    return {"message": "ピンを削除しました"}


@router.post("/batch", response_model=List[PinResponse])
async def create_pins_batch(
    pins_data: List[PinCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """複数のピンを一括作成"""
    created_pins = []

    for pin_data in pins_data:
        # 既存のピンをチェック
        existing_pin = db.query(SavedPin).filter(
            SavedPin.user_id == current_user.id,
            SavedPin.station_name == pin_data.station_name,
            SavedPin.line_name == pin_data.line_name
        ).first()

        if not existing_pin:
            # 新しいピンを作成
            new_pin = SavedPin(
                user_id=current_user.id,
                station_name=pin_data.station_name,
                line_name=pin_data.line_name,
                coord_lat=pin_data.coord_lat,
                coord_lon=pin_data.coord_lon,
                nearby_places=pin_data.nearby_places,
                reachable_stations=pin_data.reachable_stations,
                average_rent=pin_data.average_rent,
                conversation_context=pin_data.conversation_context,
                notes=pin_data.notes,
                tags=pin_data.tags
            )
            db.add(new_pin)
            created_pins.append(new_pin)
        else:
            # 既存のピンを更新
            if pin_data.nearby_places is not None:
                existing_pin.nearby_places = pin_data.nearby_places
            if pin_data.reachable_stations is not None:
                existing_pin.reachable_stations = pin_data.reachable_stations
            if pin_data.average_rent is not None:
                existing_pin.average_rent = pin_data.average_rent
            if pin_data.conversation_context is not None:
                existing_pin.conversation_context = pin_data.conversation_context
            if pin_data.notes is not None:
                existing_pin.notes = pin_data.notes
            if pin_data.tags is not None:
                existing_pin.tags = pin_data.tags
            existing_pin.updated_at = datetime.utcnow()
            created_pins.append(existing_pin)

    db.commit()

    # すべてのピンをリフレッシュ
    for pin in created_pins:
        db.refresh(pin)

    return [PinResponse.from_orm(pin) for pin in created_pins]


@router.get("/search/nearby", response_model=List[PinResponse])
async def search_nearby_pins(
    lat: float = Query(..., description="緯度"),
    lon: float = Query(..., description="経度"),
    radius_km: float = Query(5.0, description="検索半径（km）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """近くのピンを検索"""
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

    # ユーザーのすべてのピンを取得
    all_pins = db.query(SavedPin).filter(SavedPin.user_id == current_user.id).all()

    # 距離でフィルタリング
    nearby_pins = []
    for pin in all_pins:
        distance = haversine_distance(lat, lon, pin.coord_lat, pin.coord_lon)
        if distance <= radius_km:
            pin_response = PinResponse.from_orm(pin)
            pin_response.distance_km = round(distance, 2)  # 距離情報を追加
            nearby_pins.append(pin_response)

    # 距離順にソート
    nearby_pins.sort(key=lambda x: x.distance_km)

    return nearby_pins