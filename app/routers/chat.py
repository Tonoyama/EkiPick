"""
AIチャットエンドポイント
Google Vertex AI Gemini 2.0を使用したマルチエージェントシステム
"""

import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from app.services.agents.estate_agent import build_estate_agent
from app.routers.middlewares.rate_limit import check_rate_limit
from app.services.global_state import DATA_STORES, SESSION_SERVICE, check_conversation_if_exist
from app.services.agents.station_agent import build_station_agent, build_multiple_pin_station_agent
from app.services.agents.suggestion_agent import build_suggest_agent
from app.services.agents.report_agent import build_report_agent
from app.services.agents.followup_agent import build_followup_agent
from textwrap import dedent


router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., min_length=1, max_length=100)

    @field_validator("message")
    def sanitize_message(cls, v):
        return v.strip()

    @field_validator("session_id")
    def validate_session_id(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "session_id must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v

async def _generate_first_conversation(user_message: str, user_id: str, session_id: str):
    # 指定された駅を示す
    station_agent = build_station_agent(SESSION_SERVICE)
    response = await station_agent.stream(user_message, user_id, session_id)
    pin_message = response[-1]

    for pin in DATA_STORES.extract_pins(user_id):
        yield pin

    yield f"data: {json.dumps({'type': 'agent_response', 'agent': 'real_estate_response', 'agent_name': '不動産エージェント', 'message': pin_message, 'round': 0})}\n\n"

    # 駅をオススメする
    suggestion_agent = build_suggest_agent(SESSION_SERVICE)
    response = await suggestion_agent.stream(user_message, user_id, session_id)
    suggestion_message = response[-1]

    yield f"data: {json.dumps({'type': 'agent_response', 'agent': 'real_estate_response', 'agent_name': '不動産エージェント', 'message': suggestion_message, 'round': 0})}\n\n"


    # 複数ピンを指す
    station_agent = build_multiple_pin_station_agent(SESSION_SERVICE)
    response = await station_agent.stream(suggestion_message, user_id, session_id)
    pins_message = response[-1]

    yield f"data: {json.dumps({'type': 'agent_response', 'agent': 'real_estate_response', 'agent_name': '不動産エージェント', 'message': pins_message, 'round': 0})}\n\n"

    for pin in DATA_STORES.extract_pins(user_id):
        yield pin

    # 駅周辺情報を解説する
    for i in range(3):
        report_agent = build_report_agent(SESSION_SERVICE, i + 1)
        response = await report_agent.stream(pins_message, user_id, session_id)
        message = response[-1]
        if "出力無" in message:
            break
        yield f"data: {json.dumps({'type': 'agent_response', 'agent': 'real_estate_response', 'agent_name': '不動産エージェント', 'message': message, 'round': 0})}\n\n"

    # フォローアップメッセージを送る
    followup_agent = build_followup_agent(SESSION_SERVICE)
    response = await followup_agent.stream(suggestion_message, user_id, session_id)
    followup = response[-1]
    yield f"data: {json.dumps({'type': 'agent_response', 'agent': 'real_estate_response', 'agent_name': '不動産エージェント', 'message': followup, 'round': 0})}\n\n"
    




async def _generate_after_second_conversations(message: str, user_id: str, session_id: str):
    try:
        estate_agent = build_estate_agent(SESSION_SERVICE)
        response = await estate_agent.stream(message, user_id, session_id)
        message = response[-1]

        for pin in DATA_STORES.extract_pins(user_id):
            yield pin

        yield f"data: {json.dumps({'type': 'agent_response', 'agent': 'real_estate_response', 'agent_name': '不動産エージェント', 'message': message, 'round': 0})}\n\n"

    except Exception as e:
        print(e)
        yield f"data: {json.dumps({'type': 'error', 'message': f'会話中にエラーが発生しました: {str(e)}'})}\n\n"


@router.post("")
async def chat(request: ChatRequest, req: Request):
    client_ip = req.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    session_id = request.session_id
    user_id = request.session_id
    message = request.message
    name = "MODEL"

    second_coversations = check_conversation_if_exist(SESSION_SERVICE, name, user_id, session_id)
    generate = _generate_after_second_conversations if second_coversations else _generate_first_conversation
    try:
        return StreamingResponse(
            generate(message, user_id, session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception:
        import traceback
        raise HTTPException(status_code=500, detail=f"Internal server error: {traceback.format_exc()}")