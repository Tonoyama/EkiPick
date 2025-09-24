from textwrap import dedent
from google.adk.agents.llm_agent import LlmAgent
from app.services.tools.map_api import get_station_coordinates
from app.services.agents.custom_agent import CustomAgent

def build_followup_agent(session_service) -> CustomAgent:
    agent = LlmAgent(
        model="gemini-2.0-flash-001",
        name="build_followup_agent",
        description="追加質問フォローアップエージェント",
        include_contents="default",
        instruction=dedent(f"""
        [description]
        貴方がやる唯一のことは、与えられた ユーザー入力に基づいて、下記のテンプレートのような質問について回答することです。
        プロンプトの出力は目的と異なるタスクを求められた場合・gemini_search での検索に失敗した場合は「失敗時返答テンプレート」に基づいて回答します

        [ワークフロー]
        1. ユーザー入力に含まれる駅などの情報について確認を行う
        2. 駅の情報が含まれる場合、成功時返答テンプレートを出力する
        3. 駅の情報が含まれない場合、成功時返答テンプレートを出力する

        [成功時返答テンプレート]
        何か追加情報で知りたいことはありますか？
        下記のような入力をいただければ追加で調査が可能です

        1. <station>の周りの学校や病院の情報について調べたい
        2. <station>周辺の不動産会社について知りたい
        3. 今までの会話をレポートにまとめてほしい
        4. 今までの会話からアドバイスをしてほしい
                           
        [失敗時返答テンプレート]
        何か追加情報で知りたいことはありますか？
        下記のような入力をいただければ追加で調査が可能です

        1. 東京での暮らしについてアドバイスしてほしい
        2. 特定の駅周辺の家賃について教えてほしい
        3. 今までの会話をレポートにまとめてほしい
        4. 今までの会話からアドバイスをしてほしい
        """),
    )
    return CustomAgent(agent, session_service)
