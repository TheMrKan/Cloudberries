import json
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.schemas import SessionContext
from src.db.models import ChatSession


class ChatService:
    @staticmethod
    async def create_session(db: AsyncSession) -> str:
        session_id = str(uuid4())
        ctx = SessionContext().model_dump()
        db.add(ChatSession(session_id=session_id, context=ctx))
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

    @staticmethod
    async def process_message(
        db: AsyncSession, session_id: str, text: str
    ) -> AsyncGenerator[str, None]:
        _ = text

        yield json.dumps(
            {"event": "message", "data": {"text": "Ищу подходящие услуги..."}}
        )

        yield json.dumps(
            {
                "event": "question",
                "data": {
                    "question": "Какой бюджет?",
                    "options": ["до 10 000", "10 000 - 50 000", "более 50 000"],
                },
            }
        )

        yield json.dumps({"event": "services", "data": []})

        yield json.dumps({"event": "done", "data": None})
