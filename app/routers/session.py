from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as DBSession
from typing import Optional, Dict, Any, List
import uuid
import json
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import Session, SearchHistory, CommuteHistory, SavedProperty, Property
from ..schemas import SessionCreate, SessionResponse, SearchHistoryResponse, CommuteHistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: Optional[SessionCreate] = None,
    db: DBSession = Depends(get_db)
):
    """
    新しいセッションを作成
    認証は不要、クライアントでセッションIDを保持
    """
    try:
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=30)  # 30日間有効

        db_session = Session(
            id=session_id,
            data=json.dumps(session_data.dict() if session_data else {}),
            expires_at=expires_at
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)

        return SessionResponse(
            id=db_session.id,
            data=json.loads(db_session.data) if db_session.data else {},
            created_at=db_session.created_at,
            expires_at=db_session.expires_at
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="セッション作成に失敗しました")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """セッション情報を取得"""
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    # 有効期限チェック
    if db_session.expires_at and db_session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="セッションの有効期限が切れています")

    return SessionResponse(
        id=db_session.id,
        data=json.loads(db_session.data) if db_session.data else {},
        created_at=db_session.created_at,
        expires_at=db_session.expires_at
    )


@router.put("/{session_id}")
async def update_session(
    session_id: str,
    session_data: Dict[str, Any],
    db: DBSession = Depends(get_db)
):
    """セッションデータを更新"""
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    try:
        db_session.data = json.dumps(session_data)
        db_session.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "セッションを更新しました"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(status_code=500, detail="セッション更新に失敗しました")


@router.post("/{session_id}/search-history")
async def add_search_history(
    session_id: str,
    search_type: str,
    search_params: Dict[str, Any],
    results_count: int,
    db: DBSession = Depends(get_db)
):
    """検索履歴を追加"""
    # セッション存在確認
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    try:
        history = SearchHistory(
            session_id=session_id,
            search_type=search_type,
            search_params=json.dumps(search_params),
            results_count=results_count
        )
        db.add(history)
        db.commit()

        return {"message": "検索履歴を保存しました"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add search history: {e}")
        raise HTTPException(status_code=500, detail="検索履歴の保存に失敗しました")


@router.get("/{session_id}/search-history", response_model=List[SearchHistoryResponse])
async def get_search_history(
    session_id: str,
    limit: int = 10,
    db: DBSession = Depends(get_db)
):
    """検索履歴を取得"""
    histories = db.query(SearchHistory).filter(
        SearchHistory.session_id == session_id
    ).order_by(SearchHistory.created_at.desc()).limit(limit).all()

    return [
        SearchHistoryResponse(
            id=h.id,
            search_type=h.search_type,
            search_params=json.loads(h.search_params) if h.search_params else {},
            results_count=h.results_count,
            created_at=h.created_at
        )
        for h in histories
    ]


@router.post("/{session_id}/commute-history")
async def add_commute_history(
    session_id: str,
    from_address: str,
    to_address: str,
    from_coords: Dict[str, float],
    to_coords: Dict[str, float],
    commute_time: int,
    fare: float,
    route_data: Dict[str, Any],
    db: DBSession = Depends(get_db)
):
    """通勤時間計算履歴を追加"""
    # セッション存在確認
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    try:
        history = CommuteHistory(
            session_id=session_id,
            from_address=from_address,
            to_address=to_address,
            from_lat=from_coords.get("lat"),
            from_lon=from_coords.get("lon"),
            to_lat=to_coords.get("lat"),
            to_lon=to_coords.get("lon"),
            commute_time=commute_time,
            fare=fare,
            route_data=json.dumps(route_data)
        )
        db.add(history)
        db.commit()

        return {"message": "通勤時間履歴を保存しました"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add commute history: {e}")
        raise HTTPException(status_code=500, detail="通勤時間履歴の保存に失敗しました")


@router.get("/{session_id}/commute-history", response_model=List[CommuteHistoryResponse])
async def get_commute_history(
    session_id: str,
    limit: int = 10,
    db: DBSession = Depends(get_db)
):
    """通勤時間計算履歴を取得"""
    histories = db.query(CommuteHistory).filter(
        CommuteHistory.session_id == session_id
    ).order_by(CommuteHistory.created_at.desc()).limit(limit).all()

    return [
        CommuteHistoryResponse(
            id=h.id,
            from_address=h.from_address,
            to_address=h.to_address,
            from_coords={"lat": h.from_lat, "lon": h.from_lon},
            to_coords={"lat": h.to_lat, "lon": h.to_lon},
            commute_time=h.commute_time,
            fare=h.fare,
            route_data=json.loads(h.route_data) if h.route_data else {},
            created_at=h.created_at
        )
        for h in histories
    ]


@router.post("/{session_id}/saved-properties/{property_id}")
async def save_property(
    session_id: str,
    property_id: int,
    notes: Optional[str] = None,
    commute_data: Optional[Dict[str, Any]] = None,
    db: DBSession = Depends(get_db)
):
    """物件を保存"""
    # セッションと物件の存在確認
    db_session = db.query(Session).filter(Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="物件が見つかりません")

    # すでに保存済みか確認
    existing = db.query(SavedProperty).filter(
        SavedProperty.session_id == session_id,
        SavedProperty.property_id == property_id
    ).first()

    if existing:
        # 更新
        existing.notes = notes
        if commute_data:
            existing.commute_data = json.dumps(commute_data)
        db.commit()
        return {"message": "保存済み物件を更新しました"}

    try:
        saved = SavedProperty(
            session_id=session_id,
            property_id=property_id,
            notes=notes,
            commute_data=json.dumps(commute_data) if commute_data else None
        )
        db.add(saved)
        db.commit()

        return {"message": "物件を保存しました"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save property: {e}")
        raise HTTPException(status_code=500, detail="物件の保存に失敗しました")


@router.get("/{session_id}/saved-properties")
async def get_saved_properties(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """保存した物件一覧を取得"""
    saved_properties = db.query(SavedProperty).filter(
        SavedProperty.session_id == session_id
    ).order_by(SavedProperty.created_at.desc()).all()

    result = []
    for saved in saved_properties:
        property_data = {
            "id": saved.property.id,
            "title": saved.property.title,
            "price": saved.property.price,
            "location": saved.property.location,
            "bedrooms": saved.property.bedrooms,
            "bathrooms": saved.property.bathrooms,
            "area_sqft": saved.property.area_sqft,
            "property_type": saved.property.property_type.value if saved.property.property_type else None,
            "notes": saved.notes,
            "commute_data": json.loads(saved.commute_data) if saved.commute_data else None,
            "saved_at": saved.created_at
        }
        result.append(property_data)

    return result


@router.delete("/{session_id}/saved-properties/{property_id}")
async def remove_saved_property(
    session_id: str,
    property_id: int,
    db: DBSession = Depends(get_db)
):
    """保存した物件を削除"""
    saved = db.query(SavedProperty).filter(
        SavedProperty.session_id == session_id,
        SavedProperty.property_id == property_id
    ).first()

    if not saved:
        raise HTTPException(status_code=404, detail="保存された物件が見つかりません")

    try:
        db.delete(saved)
        db.commit()
        return {"message": "保存した物件を削除しました"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove saved property: {e}")
        raise HTTPException(status_code=500, detail="物件の削除に失敗しました")