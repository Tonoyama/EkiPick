from google.adk.sessions import InMemorySessionService
from app.services.send_pin import SendPinStore

SESSION_SERVICE = InMemorySessionService()
DATA_STORES = SendPinStore()



def check_conversation_if_exist(session_service: InMemorySessionService, name: str, user_id: str, session_id: str) -> bool:
    sessions = session_service.sessions
    return name in sessions and user_id in sessions[name] and session_id in sessions[name][user_id]  # type: ignore
