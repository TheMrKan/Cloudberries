from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqladmin import Admin

from src.admin import AdminAuth, ProviderAdmin, ServiceAdmin
from src.chat.router import router as chat_router
from src.db.engine import async_session_factory, engine
from src.db.models import BaseModel
from src.search.keyword_search import init_keyword_search
from src.search.qdrant_client import get_qdrant_client, ensure_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        qc = get_qdrant_client()
        ensure_collection(qc)
    except Exception:
        pass
    async with async_session_factory() as session:
        await init_keyword_search(session)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="dev-secret-key-change-in-prod")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(chat_router, prefix="/api")


@app.get("/")
async def index():
    from fastapi.responses import FileResponse

    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


auth_backend = AdminAuth(secret_key="dev-secret-key-change-in-prod")

admin = Admin(app, engine, authentication_backend=auth_backend)
admin.add_view(ProviderAdmin)
admin.add_view(ServiceAdmin)
