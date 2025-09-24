

from datetime import datetime
from typing import Dict

_REQUEST_COUNTS: Dict[str, Dict[str, int]] = {}

def check_rate_limit(client_ip: str, limit: int = 10, window: int = 60) -> bool:
    current_time = int(datetime.now().timestamp())
    window_start = current_time - window

    if client_ip not in _REQUEST_COUNTS:
        _REQUEST_COUNTS[client_ip] = {}

    # クリーンアップ
    _REQUEST_COUNTS[client_ip] = {
        timestamp: count
        for timestamp, count in _REQUEST_COUNTS[client_ip].items()
        if int(timestamp) > window_start
    }

    # リクエスト数をカウント
    total_requests = sum(_REQUEST_COUNTS[client_ip].values())

    if total_requests >= limit:
        return False

    # リクエストを記録
    current_minute = str(current_time // 60 * 60)
    _REQUEST_COUNTS[client_ip][current_minute] = (
        _REQUEST_COUNTS[client_ip].get(current_minute, 0) + 1
    )

    return True