from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.chat.schemas import ChatRequest, ServiceItem, SessionResponse
from src.chat.service import ChatService
from src.chat_engine import chat_pipeline
from src.db.engine import get_session
from src.db.models import Provider, Service

router = APIRouter()


@router.get("/services")
async def list_services(db: AsyncSession = Depends(get_session)):
    rows = (
        (
            await db.execute(
                select(
                    Service.service_id,
                    Service.name,
                    Service.description,
                    Service.compliance_tags,
                    Service.regions,
                    Service.pricing_elements,
                    Provider.name.label("provider"),
                ).join(Provider, Provider.provider_id == Service.provider_id)
            )
        )
        .mappings()
        .all()
    )
    return [
        ServiceItem(
            id=r["service_id"],
            name=r["name"],
            provider=r["provider"],
            description=r["description"],
            compliance_tags=r["compliance_tags"]
            if isinstance(r["compliance_tags"], list)
            else [],
            regions=r["regions"] if isinstance(r["regions"], list) else [],
            pricing_elements=r["pricing_elements"]
            if isinstance(r["pricing_elements"], list)
            else [],
        ).model_dump()
        for r in rows
    ]


@router.post("/chat")
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_session)):
    session = await ChatService.get_session(db, body.session_id)
    if session is None:
        session = await ChatService.create_session(db, body.session_id)

    print(f"[ROUTER] session={body.session_id} message={body.message}")
    await ChatService.append_message(db, body.session_id, "user", body.message)

    async def event_stream():
        async for event in chat_pipeline(db, body.session_id, body.message):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/session")
async def get_session(session_id: str, db: AsyncSession = Depends(get_session)):
    session = await ChatService.get_session(db, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    return SessionResponse(
        session_id=session.session_id,
        messages=session.messages,
        results=session.results or None,
    ).model_dump(exclude_none=True)


@router.delete("/chat/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_session)):
    session = await ChatService.get_session(db, session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    await db.delete(session)
    await db.commit()
