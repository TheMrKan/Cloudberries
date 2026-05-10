from datetime import datetime

from sqlalchemy import String, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
from pydantic import BaseModel as PDBaseModel


class BaseModel(DeclarativeBase):
    pass


class Provider(BaseModel):
    __tablename__ = "provider"

    provider_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))

    def __repr__(self) -> str:
        return f"Provider({self.provider_id=}, {self.name=})"


class PricingElement(PDBaseModel):
    description: str
    uom: str
    price: float


class Service(BaseModel):
    __tablename__ = "service"

    service_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider.provider_id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    compliance_tags: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    regions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    pricing_elements: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True, default=list
    )
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)


class ChatSession(BaseModel):
    __tablename__ = "chat_session"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    context: Mapped[dict] = mapped_column(JSON, default=lambda: {})
    messages: Mapped[list[dict]] = mapped_column(JSON, default=lambda: [])
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
