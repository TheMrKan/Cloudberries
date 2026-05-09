from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.db.models import Provider, ServiceType, Service, ServiceParameterValue


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form["username"] == "admin" and form["password"] == "admin":
            request.session.update({"token": "admin"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("token") == "admin"


class ProviderAdmin(ModelView, model=Provider):
    column_list = [Provider.provider_id, Provider.name]
    column_searchable_list = [Provider.name]
    form_columns = [Provider.provider_id, Provider.name]


class ServiceTypeAdmin(ModelView, model=ServiceType):
    column_list = [ServiceType.type_id, ServiceType.name, ServiceType.description]
    column_searchable_list = [ServiceType.name]
    form_columns = [
        ServiceType.type_id,
        ServiceType.name,
        ServiceType.description,
        ServiceType.parameters,
    ]


class ServiceAdmin(ModelView, model=Service):
    column_list = [
        Service.service_id,
        Service.provider_id,
        Service.type_id,
        Service.uom,
        Service.price,
    ]
    column_searchable_list = [Service.uom]
    form_columns = [Service.provider_id, Service.type_id, Service.uom, Service.price]


class ServiceParameterValueAdmin(ModelView, model=ServiceParameterValue):
    column_list = [
        ServiceParameterValue.service_id,
        ServiceParameterValue.parameter_id,
        ServiceParameterValue.value,
    ]
    form_columns = [
        ServiceParameterValue.service_id,
        ServiceParameterValue.parameter_id,
        ServiceParameterValue.value,
    ]
