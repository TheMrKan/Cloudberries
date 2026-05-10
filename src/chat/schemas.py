from pydantic import BaseModel


class StructuredSearch(BaseModel):
    keyword_search_query: str | None = None
    vector_search_query: str | None = None
    compliance_filter: list[str] | None = None
    regions_filter: list[str] | None = None


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
