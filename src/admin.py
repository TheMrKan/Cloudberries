from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.db.models import Provider, Service


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


class ServiceAdmin(ModelView, model=Service):
    column_list = [
        Service.service_id,
        Service.provider_id,
        Service.name,
        Service.compliance_tags,
        Service.regions,
        Service.pricing_elements,
    ]
    column_searchable_list = [Service.name]
    form_columns = [
        Service.provider_id,
        Service.name,
        Service.description,
        Service.compliance_tags,
        Service.regions,
        Service.pricing_elements,
    ]
