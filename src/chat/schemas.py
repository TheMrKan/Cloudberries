from pydantic import BaseModel


class StructuredSearch(BaseModel):
    fz_filter: bool | None = None
    regions_filter: list[str] | None = None
    search_queries: list[str] = []


class ChatInitResponse(BaseModel):
    session_id: str


class ChatSendRequest(BaseModel):
    session_id: str
    message: str


class MessageOut(BaseModel):
    role: str
    text: str
    events: list[dict] | None = None
    created_at: str | None = None
