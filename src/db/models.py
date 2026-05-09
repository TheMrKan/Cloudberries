from datetime import datetime

from sqlalchemy import String, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
from pydantic import BaseModel as PDBaseModel


class BaseModel(DeclarativeBase):
    pass


class Provider(BaseModel):
    __tablename__ = "provider"

    provider_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(32))

    def __repr__(self) -> str:
        return f"Provider({self.provider_id=}, {self.name=})"


class ServiceParameter(PDBaseModel):
    id: str
    name: str
    uom: str


class ServiceType(BaseModel):
    __tablename__ = "service_type"

    type_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(512))
    parameters: Mapped[dict[str, ServiceParameter]] = mapped_column(JSON())

    def __repr__(self) -> str:
        return f"ServiceType({self.type_id=}, {self.name=}, {self.description[:20]=})"


class Service(BaseModel):
    __tablename__ = "service"

    service_id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("provider.provider_id", ondelete="CASCADE")
    )
    type_id: Mapped[str] = mapped_column(
        ForeignKey("service_type.type_id", ondelete="CASCADE")
    )
    uom: Mapped[str] = mapped_column(String(32))
    price: Mapped[float] = mapped_column()


class ServiceParameterValue(BaseModel):
    __tablename__ = "service_parameter_value"

    service_id: Mapped[int] = mapped_column(
        ForeignKey("service.service_id", ondelete="CASCADE"), primary_key=True
    )
    parameter_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[float] = mapped_column()

    def __repr__(self) -> str:
        return f"ServiceParameterValue({self.service_id=}, {self.parameter_id=}, {self.value=})"


class ChatSession(BaseModel):
    __tablename__ = "chat_session"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    context: Mapped[dict] = mapped_column(JSON, default=lambda: {})
    messages: Mapped[list[dict]] = mapped_column(JSON, default=lambda: [])
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
