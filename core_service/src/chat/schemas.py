from pydantic import BaseModel


class StructuredSearch(BaseModel):
    keyword_search_query: str | None = None
    vector_search_query: str | None = None
    compliance_filter: list[str] | None = None
    regions_filter: list[str] | None = None


class ServiceItem(BaseModel):
    id: int
    name: str
    provider: str
    description: str | None = None
    compliance_tags: list[str] = []
    regions: list[str] = []
    pricing_elements: list[dict] = []


class ServiceResult(BaseModel):
    id: int
    name: str
    provider: str
    description: str | None = None
    compliance_tags: list[str] = []
    regions: list[str] = []
    pricing_elements: list[dict] = []
    rationale: str = ""
    scores: dict[str, str]
    matched_keywords: list[str] = []


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]
    results: list[dict] | None = None


class ChatInitResponse(BaseModel):
    session_id: str
