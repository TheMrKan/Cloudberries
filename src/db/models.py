from sqlalchemy import String, ForeignKey, JSON
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
