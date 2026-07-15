"""Conversation orchestration: per-session history, optional retrieval, and
the actual call into the LangChain chat model.

Session history is kept in-process, in memory. That's intentional for a
"simple chat agent" - swap in Redis or a database-backed message history if
the service needs to survive restarts or run with multiple replicas.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.config import Settings, get_settings
from app.services.knowledge_base import get_retriever
from app.services.llm_factory import get_chat_model


@dataclass
class _Session:
    messages: list[BaseMessage] = field(default_factory=list)
    last_seen: float = field(default_factory=time.monotonic)


class ChatService:
    """Stateful façade over the chat model, history, and retriever."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._llm = get_chat_model()
        self._retriever = get_retriever()
        self._sessions: dict[str, _Session] = {}
        self._lock = asyncio.Lock()

    @property
    def rag_enabled(self) -> bool:
        return self._retriever is not None

    async def _get_session(self, session_id: str) -> _Session:
        async with self._lock:
            session = self._sessions.setdefault(session_id, _Session())
            session.last_seen = time.monotonic()
            return session

    async def reset_session(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def _retrieve_context(self, query: str) -> Optional[str]:
        if not self._retriever:
            return None
        docs = await self._retriever.ainvoke(query)
        if not docs:
            return None
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    def _build_system_message(self, context: Optional[str]) -> SystemMessage:
        prompt = self.settings.system_prompt
        if context:
            prompt = f"{prompt}\n\nKnowledge base context:\n{context}"
        return SystemMessage(content=prompt)

    async def _build_prompt(self, session: _Session, message: str) -> list[BaseMessage]:
        context = await self._retrieve_context(message)
        history_limit = self.settings.history_turns * 2
        trimmed_history = session.messages[-history_limit:] if history_limit else session.messages
        return [self._build_system_message(context), *trimmed_history, HumanMessage(content=message)]

    async def chat(self, session_id: str, message: str) -> str:
        session = await self._get_session(session_id)
        prompt = await self._build_prompt(session, message)

        response = await self._llm.ainvoke(prompt)
        reply = response.content if isinstance(response.content, str) else str(response.content)

        session.messages.append(HumanMessage(content=message))
        session.messages.append(AIMessage(content=reply))
        return reply

    async def stream(self, session_id: str, message: str) -> AsyncIterator[str]:
        session = await self._get_session(session_id)
        prompt = await self._build_prompt(session, message)

        chunks: list[str] = []
        async for chunk in self._llm.astream(prompt):
            token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            if not token:
                continue
            chunks.append(token)
            yield token

        session.messages.append(HumanMessage(content=message))
        session.messages.append(AIMessage(content="".join(chunks)))


_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _service
    if _service is None:
        _service = ChatService()
    return _service
