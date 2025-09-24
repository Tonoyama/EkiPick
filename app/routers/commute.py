from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from ..services.geocode import get_latlon_from_address, get_address_info
from ..services.navitime import calculate_commute_time, NavitimeClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/commute", tags=["commute"])


@router.get("/geocode")
async def geocode_address(address: str = Query(..., description="住所文字列")):
    """
    住所から緯度・経度を取得

    Example:
        GET /api/v1/commute/geocode?address=東京駅
    """
    result = get_address_info(address)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/time")
async def get_commute_time(
    from_address: str = Query(..., description="出発地の住所"),
    to_address: str = Query(..., description="到着地の住所"),
    start_time: str = Query("2025-09-22T08:30:00", description="出発時刻 (例: 2025-09-22T08:30:00)"),
    use_coordinates: bool = Query(False, description="住所を座標として扱うか (lat,lon形式)"),
):
    """
    2地点間の通勤時間と運賃を取得

    Example:
        GET /api/v1/commute/time?from_address=東京駅&to_address=新宿駅
        GET /api/v1/commute/time?from_address=35.681236,139.767125&to_address=35.658584,139.701742&use_coordinates=true
    """
    try:
        # 座標変換が必要な場合
        if not use_coordinates:
            # 住所から座標を取得
            from_lat, from_lon = get_latlon_from_address(from_address)
            to_lat, to_lon = get_latlon_from_address(to_address)

            if not from_lat or not from_lon:
                raise HTTPException(status_code=400, detail=f"出発地の住所が見つかりません: {from_address}")
            if not to_lat or not to_lon:
                raise HTTPException(status_code=400, detail=f"到着地の住所が見つかりません: {to_address}")

            start_location = f"{from_lat},{from_lon}"
            goal_location = f"{to_lat},{to_lon}"
        else:
            # すでに座標形式の場合
            start_location = from_address
            goal_location = to_address

        # 通勤時間を計算
        logger.info(f"Calculating commute time from {start_location} to {goal_location}")
        result = calculate_commute_time(
            start_location=start_location,
            goal_location=goal_location,
            start_time=start_time
        )

        logger.info(f"Commute calculation result: success={result.get('success')}, has_best_route={result.get('best_route') is not None}")
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "経路検索に失敗しました"))

        return {
            "from_address": from_address,
            "to_address": to_address,
            "from_coordinates": start_location if use_coordinates else f"{from_lat},{from_lon}",
            "to_coordinates": goal_location if use_coordinates else f"{to_lat},{to_lon}",
            "routes": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Commute time calculation failed: {e}")
        raise HTTPException(status_code=500, detail="通勤時間の計算に失敗しました")


@router.get("/batch")
async def get_batch_commute_times(
    from_address: str = Query(..., description="出発地の住所"),
    to_addresses: str = Query(..., description="到着地の住所（カンマ区切り）"),
    start_time: str = Query("2025-09-22T08:30:00", description="出発時刻"),
):
    """
    複数の目的地への通勤時間を一括取得

    Example:
        GET /api/v1/commute/batch?from_address=東京駅&to_addresses=新宿駅,渋谷駅,品川駅
    """
    to_list = [addr.strip() for addr in to_addresses.split(",")]

    # 出発地の座標を取得
    from_lat, from_lon = get_latlon_from_address(from_address)
    if not from_lat or not from_lon:
        raise HTTPException(status_code=400, detail=f"出発地の住所が見つかりません: {from_address}")

    start_location = f"{from_lat},{from_lon}"
    results = []

    for to_addr in to_list:
        try:
            # 到着地の座標を取得
            to_lat, to_lon = get_latlon_from_address(to_addr)
            if not to_lat or not to_lon:
                results.append({
                    "to_address": to_addr,
                    "error": "住所が見つかりません"
                })
                continue

            goal_location = f"{to_lat},{to_lon}"

            # 通勤時間を計算
            result = calculate_commute_time(
                start_location=start_location,
                goal_location=goal_location,
                start_time=start_time
            )

            if result["success"] and result.get("best_route"):
                best = result["best_route"]
                results.append({
                    "to_address": to_addr,
                    "coordinates": goal_location,
                    "time_minutes": best["time_minutes"],
                    "total_fare": best["total_fare"],
                    "transfer_count": best["transfer_count"],
                })
            else:
                results.append({
                    "to_address": to_addr,
                    "error": "経路が見つかりません"
                })

        except Exception as e:
            logger.error(f"Failed to calculate for {to_addr}: {e}")
            results.append({
                "to_address": to_addr,
                "error": str(e)
            })

    return {
        "from_address": from_address,
        "from_coordinates": start_location,
        "results": results,
        "summary": {
            "total_destinations": len(to_list),
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
        }
    }


@router.get("/ranking")
async def get_commute_ranking(
    from_address: str = Query(..., description="出発地の住所"),
    to_addresses: str = Query(..., description="到着地の住所（カンマ区切り）"),
    start_time: str = Query("2025-09-22T08:30:00", description="出発時刻"),
    sort_by: str = Query("time", description="ソート基準 (time/fare)"),
):
    """
    複数の目的地を通勤時間または運賃でランキング

    Example:
        GET /api/v1/commute/ranking?from_address=東京駅&to_addresses=新宿駅,渋谷駅,品川駅&sort_by=time
    """
    batch_result = await get_batch_commute_times(from_address, to_addresses, start_time)

    # 成功した結果のみを抽出
    valid_results = [r for r in batch_result["results"] if "error" not in r]

    # ソート
    if sort_by == "fare":
        valid_results.sort(key=lambda x: x.get("total_fare") or float('inf'))
    else:  # time
        valid_results.sort(key=lambda x: x.get("time_minutes") or float('inf'))

    return {
        "from_address": batch_result["from_address"],
        "from_coordinates": batch_result["from_coordinates"],
        "sort_by": sort_by,
        "ranking": [
            {
                "rank": i + 1,
                **result
            }
            for i, result in enumerate(valid_results)
        ],
        "failed": [r for r in batch_result["results"] if "error" in r]
    }