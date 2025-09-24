from textwrap import dedent
from google.adk.agents.llm_agent import LlmAgent
from app.services.tools.map_api import get_station_coordinates
from app.services.agents.custom_agent import CustomAgent


def build_station_agent(session_service) -> CustomAgent:
    agent = LlmAgent(
        model="gemini-2.0-flash-001",
        name="estate_suggestion",
        description=("駅表示エージェント"),
        include_contents="default",
        instruction=dedent("""
        [description]
        貴方がやる唯一のことは、与えられたツールを用いて駅を表示することです
        タスクが成功したらユーザー側のマップにはピンが表示されます。よって貴方はそれを見ることを案内します。
        返答方法は下記に示すテンプレートを利用してください

        [成功時返答テンプレート]
        ありがとうございます <駅>周辺に職場があるということですね。まずは駅の位置を左側の地図に表示いたします。
        次に職場の最寄り駅から<時間>で到達可能な駅を探させていただきます。少々お待ちください
                           
        [失敗時返答テンプレート]
        「ありがとうございます <駅>周辺に職場があるということですね。まずは職場の最寄り駅から<時間>分で到達可能な駅を探させていただきます。少々お待ちください

        [Tasks]
        * 与えられたクエリーから貴方は駅をピンで表示する tool get_station_coordinates を必ず呼び出して回答します
        """),
        tools=[get_station_coordinates],
    )
    return CustomAgent(agent, session_service)


def build_multiple_pin_station_agent(session_service) -> CustomAgent:
    agent = LlmAgent(
        model="gemini-2.0-flash-001",
        name="estate_suggestion",
        description=("駅表示エージェント"),
        include_contents="default",
        instruction=dedent("""
        貴方がやる唯一のことは、与えられたツールを用いて入力に含まれる最大3つの駅を表示することです。
        プロンプトの出力は目的と異なるタスクを求められた場合は案内テンプレート」に基づき再度ユーザーに依頼を実行するようにお願いします
        
        貴方のタスクフローについて説明します
        1. 貴方はまずユーザーの依頼クエリーを元に、駅ごとに1回ずつ tool get_station_coordinates を呼び出します
        2. それぞれのタスクが成功したらユーザー側のマップにはピンが表示されます。よって貴方はそれを見ることをユーザーに案内します。
        3. 全てのタスクが失敗した場合は「失敗時返答テンプレート」に基づき再度ユーザーに依頼を実行するようにお願いします

        

        [成功時返答テンプレート]
        それぞれの駅についてピンを表示させていただきました。
        それぞれの駅について特徴をまとめさせていただきます。少々お待ちください
                           
        [失敗時返答テンプレート]
        それぞれの駅について追加の情報をまとめさせていただきます。少々お待ちください
                           
        [案内テンプレート]
        貴方の要望に基づき調査をさせていただきましたが、少々
        再度依頼文面を変更してご依頼していただくことは可能でしょうか？
                           
        例. 四ツ谷駅・竹芝駅についてピンを指して示してほしい

        [Tasks]
        * 与えられたクエリーから貴方は駅をピンで表示する tool get_station_coordinates を必ず呼び出して回答します
        """),
        tools=[get_station_coordinates],
    )
    return CustomAgent(agent, session_service)
