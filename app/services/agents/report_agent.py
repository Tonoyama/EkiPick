from textwrap import dedent
from google.adk.agents.llm_agent import LlmAgent
from app.services.tools.map_api import get_station_coordinates
from app.services.agents.custom_agent import CustomAgent

def build_report_agent(session_service, number: int) -> CustomAgent:
    agent = LlmAgent(
        model="gemini-2.0-flash-001",
        name="report_agent",
        description="駅周辺情報調査エージェント",
        include_contents="default",
        instruction=dedent(f"""
        [description]
        貴方がやる唯一のことは、与えられた tool gemini_searchを用いて、入力にある{number}番目の駅についてを詳細情報を解説することです。
        プロンプトの出力は目的と異なるタスクを求められた場合・gemini_search での検索に失敗した場合は「失敗時返答テンプレート」に基づき、
        再度ユーザーに依頼を実行するようにお願いします。

        また、{number}番目の駅が入力に存在しない場合には、「出力無」とだけ記載してください

        [ワークフロー]
        1. gemini_search で駅情報について検索を行う
        2. gemini_search が成功した場合、下記に示す成功時返答テンプレートに従ってそれぞれの項目を数行ずつ記載する
        3. gemini_search が失敗した場合、「失敗時返答テンプレート」に基づき、再度ユーザーに依頼を実行するようにお願いします。

        [成功時返答テンプレート]
        <station name> について調査しましたのでご報告します

        1. 周辺環境について
        2. 住宅環境について
        3. オススメポイント
                           
        [失敗時返答テンプレート]
         <station name> についての情報を取得できませんでした。
        再度時間をおいてからお試しください


        [Tasks]
        * 与えられたクエリーから貴方は駅をピンで表示する tool gemini_search を必ず呼び出して回答します
            クエリ例 「<station name>について、周辺環境・住宅環境・住む場合のおすすめポイントについて出来るだけ詳細に教えてください」
        """),
        tools=[get_station_coordinates],
    )
    return CustomAgent(agent, session_service)
