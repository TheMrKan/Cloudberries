from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from sqladmin import Admin

from src.admin import (
    AdminAuth,
    ProviderAdmin,
    ServiceAdmin,
    ServiceTypeAdmin,
    ServiceParameterValueAdmin,
)
from src.db.engine import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="dev-secret-key-change-in-prod")


@app.get("/health")
async def health():
    return {"status": "ok"}


auth_backend = AdminAuth(secret_key="dev-secret-key-change-in-prod")

admin = Admin(app, engine, authentication_backend=auth_backend)
admin.add_view(ProviderAdmin)
admin.add_view(ServiceTypeAdmin)
admin.add_view(ServiceAdmin)
admin.add_view(ServiceParameterValueAdmin)
