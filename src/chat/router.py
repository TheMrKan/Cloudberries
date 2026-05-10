import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.chat.schemas import ChatInitResponse, ChatSendRequest, MessageOut
from src.chat.service import ChatService
from src.chat_engine import chat_pipeline
from src.db.engine import get_session

router = APIRouter(prefix="/chat")


@router.post("/init", response_model=ChatInitResponse)
async def init_session(db: AsyncSession = Depends(get_session)):
    session_id = await ChatService.create_session(db)
    return ChatInitResponse(session_id=session_id)


@router.post("/send")
async def send_message(body: ChatSendRequest, db: AsyncSession = Depends(get_session)):
    session = await ChatService.get_session(db, body.session_id)
    if session is None:
        raise HTTPException(404, "Session not found")

    print(f"[ROUTER] session={body.session_id} message={body.message}")
    await ChatService.append_message(db, body.session_id, "user", body.message)

    async def event_stream():
        async for event in chat_pipeline(db, body.session_id, body.message):
            yield f"data: {event}\n\n"
        yield "event: done\ndata: null\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{session_id}", response_model=list[MessageOut])
async def get_history(session_id: str, db: AsyncSession = Depends(get_session)):
    session = await ChatService.get_session(db, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    return [MessageOut(**m) for m in session.messages]


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_session)):
    session = await ChatService.get_session(db, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    await db.delete(session)
    await db.commit()
