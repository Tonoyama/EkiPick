from typing import Dict, Any
import pandas as pd
import random
import os
from app.services.reachable_service import ReachableService


async def reachable_station(station_name: str, time_limit: int = 30) -> Dict[str, Any]:
    service = ReachableService()

    try:
        result = await service.search_reachable_stations(
            station_name=station_name,
            time_limit=time_limit
        )

        # 0件の場合のエラーメッセージ
        if not result.get("reachable_stations") or len(result["reachable_stations"]) == 0:
            return {
                "error": f"No reachable stations found for '{station_name}' within {time_limit} minutes",
                "origin_station": station_name,
                "time_limit": time_limit,
                "reachable_stations": []
            }

        # 4件以上の場合、lineinfo.csvとの結合処理
        if len(result["reachable_stations"]) >= 4:
            filtered_result = _filter_with_rent_data(result)
            return filtered_result

        return result

    except Exception as e:
        return {
            "error": f"Failed to get reachable stations: {str(e)}",
            "origin_station": station_name,
            "time_limit": time_limit,
            "reachable_stations": []
        }


def _filter_with_rent_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    lineinfo.csvのデータと結合してワンルーム(1R)の値段でフィルタリング
    """
    try:
        # CSVファイルのパスを取得
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "..", "..", "..", "data", "lineinfo.csv")

        # CSVデータを読み込み
        df = pd.read_csv(csv_path)

        # ワンルーム(1R)のデータのみフィルタリング
        oneroom_df = df[df['間取り'] == 'ワンルーム(1R)'].copy()

        # 到達可能駅リストから駅名を抽出
        reachable_stations = result["reachable_stations"]
        station_names = [station["station_name"] for station in reachable_stations]

        # 完全一致する駅名でフィルタリング
        matched_df = oneroom_df[oneroom_df['駅名'].isin(station_names)]

        if len(matched_df) == 0:
            # マッチしない場合はランダムに3つ選択
            random_stations = random.sample(reachable_stations, min(3, len(reachable_stations)))
            result["reachable_stations"] = random_stations
            result["total_stations"] = len(random_stations)
            result["filtering_method"] = "random_selection"
        else:
            # 家賃(万円)でソートして上位3件を選択
            sorted_df = matched_df.sort_values('家賃(万円)')
            top_3_stations = sorted_df.head(3)

            # 結合したデータを作成
            filtered_stations = []
            for _, row in top_3_stations.iterrows():
                # 元の駅情報を検索
                original_station = next(
                    (s for s in reachable_stations if s["station_name"] == row['駅名']),
                    None
                )

                if original_station:
                    # 家賃情報を追加
                    enhanced_station = original_station.copy()
                    enhanced_station["rent_1r"] = float(row['家賃(万円)'])
                    enhanced_station["line_name_csv"] = row['路線名']
                    enhanced_station["coord_lat_csv"] = row['coord_lat']
                    enhanced_station["coord_lon_csv"] = row['coord_lon']
                    filtered_stations.append(enhanced_station)

            result["reachable_stations"] = filtered_stations
            result["total_stations"] = len(filtered_stations)
            result["filtering_method"] = "rent_filtered"

        return result

    except Exception as e:
        # エラー時は元のデータをそのまま返す
        result["filtering_error"] = f"Failed to filter with rent data: {str(e)}"
        return result


