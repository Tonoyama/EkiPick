"""
Gemini APIを用いた検索AIを提供するTool
"""

import os
from google import genai
from google.genai import types


# APIキーベースの認証を使用
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    # フォールバック: Vertex AIの設定を試みる
    GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
    if GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION:
        __search_model = genai.Client(
            vertexai=True, project=GOOGLE_CLOUD_PROJECT, location=GOOGLE_CLOUD_LOCATION
        )
    else:
        raise ValueError("GOOGLE_API_KEY or (GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION) must be set")
else:
    # APIキーベースのクライアントを使用
    __search_model = genai.Client(api_key=GOOGLE_API_KEY)

__search_tool = types.Tool(google_search=types.GoogleSearch())


def gemini_search(query: str) -> str:
    """
    クエリ情報から検索した結果を返却する関数

    Args:
        query: str
            「新宿駅周辺はどのような街ですか？」
            「赤坂見附は一般人が住むのに適している街でしょうか？」
    Returns:
        str: 回答結果

    """
    resp = __search_model.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=query,
        config=types.GenerateContentConfig(tools=[__search_tool], temperature=0.3),
    )
    return resp.text if resp.text is not None else "検索エラー"
