from google.genai.types import Part, Content
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from app.services.global_state import check_conversation_if_exist


class CustomAgent:
    def __init__(self, agent, session_service):
        self._agent = agent
        self._runner = Runner(
            app_name="MODEL",
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=session_service,
            memory_service=InMemoryMemoryService(),
        )

    async def stream(self, query: str, user_id: str, session_id: str):
        if check_conversation_if_exist(self._runner.session_service, "MODEL", user_id, session_id): # type: ignore
            _session = self._runner.session_service.sessions["MODEL"][user_id][session_id]
        else:
            _session = await self._runner.session_service.create_session(
                app_name="MODEL",
                user_id=user_id,
                session_id=session_id,
            )


        content = Content(role="user", parts=[Part.from_text(text=query)])
        try:
            async_events = self._runner.run_async(
                user_id=user_id,
                session_id=_session.id,
                new_message=content,
            )
            result = []
            async for event in async_events:
                if (
                    hasattr(event, "content")
                    and event.content
                    and event.content.parts
                ):
                    response = "\n".join(
                        [p.text for p in event.content.parts if p.text]
                    )
                    if response:
                        result.append(response)

            if not result:
                result.append("応答を生成できませんでした。")

            return result

        except Exception as e:
            import traceback

            return [f"エラーが発生しました: {traceback.format_exc()}"]
