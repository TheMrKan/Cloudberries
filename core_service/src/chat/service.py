from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.schemas import StructuredSearch
from src.db.models import ChatSession


class ChatService:
    @staticmethod
    async def create_session(db: AsyncSession, session_id: str | None = None) -> str:
        session_id = session_id or str(uuid4())
        exists = await db.get(ChatSession, session_id)
        if not exists:
            db.add(ChatSession(session_id=session_id, context={}))
            await db.commit()
        return session_id

    @staticmethod
    async def get_session(db: AsyncSession, session_id: str) -> ChatSession | None:
        return await db.get(ChatSession, session_id)

    @staticmethod
    async def append_message(
        db: AsyncSession,
        session_id: str,
        role: str,
        text: str,
        events: list[dict] | None = None,
    ) -> None:
        session = await db.get(ChatSession, session_id)
        if session is None:
            return

        msg = {
            "role": role,
            "text": text,
            "events": events,
            "created_at": datetime.utcnow().isoformat(),
        }
        session.messages = [*session.messages, msg]
        await db.commit()
