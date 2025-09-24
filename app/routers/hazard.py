"""
災害リスク情報API
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from ..services.hazard_service import hazard_service
from ..routers.auth import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hazard", tags=["hazard"])


class HazardRiskRequest(BaseModel):
    """災害リスク判定リクエスト"""
    lat: float
    lon: float


class HazardRiskResponse(BaseModel):
    """災害リスク判定レスポンス"""
    location: Dict[str, float]
    flood: Dict[str, str]
    inland_flood: Dict[str, str]
    storm_surge: Dict[str, str]
    tsunami: Dict[str, str]
    landslide: List[str]
    avalanche: bool


class MultiplePointsRequest(BaseModel):
    """複数地点の災害リスク判定リクエスト"""
    points: List[Dict[str, float]]  # [{"lat": 35.6762, "lon": 139.6503}, ...]


@router.get("/risks", response_model=HazardRiskResponse)
async def get_hazard_risks(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度")
):
    """
    指定地点の全災害リスクを取得

    Parameters:
    - lat: 緯度（-90～90）
    - lon: 経度（-180～180）

    Returns:
    - 全災害種別のリスク判定結果
    """
    try:
        logger.info(f"災害リスク取得: lat={lat}, lon={lon}")
        risks = hazard_service.get_all_risks(lat, lon)
        return HazardRiskResponse(**risks)
    except Exception as e:
        logger.error(f"災害リスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flood")
async def get_flood_risk(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度"),
    level: str = Query("l1", regex="^(l1|l2)$", description="想定規模（l1:計画規模、l2:想定最大規模）")
):
    """
    洪水浸水リスクを取得

    Parameters:
    - lat: 緯度
    - lon: 経度
    - level: 想定規模（l1:計画規模＝約100年に1度、l2:想定最大規模＝約1000年に1度）
    """
    try:
        depth = hazard_service.estimate_flood_risk(lat, lon, level)
        return {
            "location": {"lat": lat, "lon": lon},
            "level": level,
            "depth": depth
        }
    except Exception as e:
        logger.error(f"洪水リスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inland-flood")
async def get_inland_flood_risk(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度")
):
    """内水氾濫（雨水出水）リスクを取得"""
    try:
        depth = hazard_service.estimate_inland_flood_risk(lat, lon)
        return {
            "location": {"lat": lat, "lon": lon},
            "depth": depth
        }
    except Exception as e:
        logger.error(f"内水氾濫リスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storm-surge")
async def get_storm_surge_risk(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度")
):
    """高潮浸水リスクを取得"""
    try:
        depth = hazard_service.estimate_storm_surge_risk(lat, lon)
        return {
            "location": {"lat": lat, "lon": lon},
            "depth": depth
        }
    except Exception as e:
        logger.error(f"高潮リスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tsunami")
async def get_tsunami_risk(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度")
):
    """津波浸水リスクを取得"""
    try:
        depth = hazard_service.estimate_tsunami_risk(lat, lon)
        return {
            "location": {"lat": lat, "lon": lon},
            "depth": depth
        }
    except Exception as e:
        logger.error(f"津波リスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/landslide")
async def get_landslide_zones(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度")
):
    """土砂災害警戒区域を判定"""
    try:
        zones = hazard_service.check_landslide_zones(lat, lon)
        return {
            "location": {"lat": lat, "lon": lon},
            "zones": zones,
            "is_in_zone": zones != ["対象外"]
        }
    except Exception as e:
        logger.error(f"土砂災害警戒区域判定エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/avalanche")
async def get_avalanche_risk(
    lat: float = Query(..., ge=-90, le=90, description="緯度"),
    lon: float = Query(..., ge=-180, le=180, description="経度")
):
    """雪崩危険箇所を判定"""
    try:
        is_risk = hazard_service.check_avalanche_risk(lat, lon)
        return {
            "location": {"lat": lat, "lon": lon},
            "is_avalanche_risk": is_risk
        }
    except Exception as e:
        logger.error(f"雪崩危険箇所判定エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multiple",
    response_model=List[HazardRiskResponse],
    summary="複数地点の災害リスクを一括取得"
)
async def get_multiple_hazard_risks(
    request: MultiplePointsRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    複数地点の災害リスクを一括取得（認証ユーザーのみ）

    最大10地点まで同時取得可能
    """
    if len(request.points) > 10:
        raise HTTPException(
            status_code=400,
            detail="一度に取得できるのは最大10地点までです"
        )

    results = []
    for point in request.points:
        try:
            risks = hazard_service.get_all_risks(
                point.get("lat"),
                point.get("lon")
            )
            results.append(HazardRiskResponse(**risks))
        except Exception as e:
            logger.error(f"地点({point})のリスク取得エラー: {e}")
            # エラーの場合はデフォルト値を返す
            results.append(HazardRiskResponse(
                location=point,
                flood={"L1_depth": "エラー", "L2_depth": "エラー"},
                inland_flood={"depth": "エラー"},
                storm_surge={"depth": "エラー"},
                tsunami={"depth": "エラー"},
                landslide=["エラー"],
                avalanche=False
            ))

    return results


@router.get("/property/{property_id}")
async def get_property_hazard_risks(
    property_id: int
):
    """
    物件IDから災害リスクを取得

    物件データから緯度経度を取得して災害リスクを判定
    """
    # ここでは簡易実装（実際は物件データベースから取得）
    # 仮の東京駅の座標を使用
    lat, lon = 35.6812, 139.7671

    try:
        risks = hazard_service.get_all_risks(lat, lon)
        return {
            "property_id": property_id,
            "risks": risks
        }
    except Exception as e:
        logger.error(f"物件災害リスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiles")
async def get_hazard_tile_urls():
    """
    地図表示用のタイルURLを取得

    フロントエンドで地図レイヤーとして使用
    """
    from ..services.hazard_service import HAZARD_TILE_URLS

    return {
        "tiles": {
            "flood_l1": {
                "url": HAZARD_TILE_URLS["flood_l1"],
                "name": "洪水浸水想定（計画規模）",
                "attribution": "ハザードマップポータル"
            },
            "flood_l2": {
                "url": HAZARD_TILE_URLS["flood_l2"],
                "name": "洪水浸水想定（想定最大規模）",
                "attribution": "ハザードマップポータル"
            },
            "inland_flood": {
                "url": HAZARD_TILE_URLS["inland_flood"],
                "name": "内水氾濫",
                "attribution": "ハザードマップポータル"
            },
            "storm_surge": {
                "url": HAZARD_TILE_URLS["storm_surge"],
                "name": "高潮浸水想定",
                "attribution": "ハザードマップポータル"
            },
            "tsunami": {
                "url": HAZARD_TILE_URLS["tsunami"],
                "name": "津波浸水想定",
                "attribution": "ハザードマップポータル"
            },
            "landslide_debris": {
                "url": HAZARD_TILE_URLS["landslide_debris"],
                "name": "土石流警戒区域",
                "attribution": "ハザードマップポータル"
            },
            "landslide_slope": {
                "url": HAZARD_TILE_URLS["landslide_slope"],
                "name": "急傾斜地崩壊警戒区域",
                "attribution": "ハザードマップポータル"
            },
            "landslide_slide": {
                "url": HAZARD_TILE_URLS["landslide_slide"],
                "name": "地すべり警戒区域",
                "attribution": "ハザードマップポータル"
            },
            "avalanche": {
                "url": HAZARD_TILE_URLS["avalanche"],
                "name": "雪崩危険箇所",
                "attribution": "ハザードマップポータル"
            }
        },
        "legend": {
            "flood": {
                "colors": {
                    "#F7F5A9": "0.5m未満",
                    "#FFD8C0": "0.5-1.0m",
                    "#FFB7B7": "1.0-2.0m",
                    "#FF9191": "2.0-3.0m",
                    "#F285C9": "3.0-5.0m",
                    "#DC7ADC": "5.0m以上"
                }
            },
            "tsunami": {
                "colors": {
                    "#F7F5A9": "0.5m未満",
                    "#FFD8C0": "0.5-3.0m",
                    "#FFB7B7": "3.0-5.0m",
                    "#FF9191": "5.0-10.0m",
                    "#F285C9": "10.0-20.0m",
                    "#DC7ADC": "20.0m以上"
                }
            },
            "landslide": {
                "colors": {
                    "#FF0000": "特別警戒区域",
                    "#FFFF00": "警戒区域"
                }
            }
        }
    }