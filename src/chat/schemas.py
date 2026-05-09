from pydantic import BaseModel


class FilteringParams(BaseModel):
    compliance_152fz: bool | None = None
    provider_id: str | None = None
    region: str | None = None
    tech_stack: list[str] | None = None
    service_type_id: str | None = None


class RangingParams(BaseModel):
    budget_min: float | None = None
    budget_max: float | None = None
    vcpu_min: int | None = None
    vcpu_max: int | None = None
    ram_min: int | None = None
    ram_max: int | None = None
    disk_min: int | None = None
    disk_max: int | None = None


class SessionContext(BaseModel):
    filtering: FilteringParams = FilteringParams()
    ranging: RangingParams = RangingParams()


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
