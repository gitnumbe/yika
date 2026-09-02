from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  确保模型注册到 Base.metadata
from .config import settings
from .core.errors import register_error_handlers
from .core.logging import setup_logging
from .database import Base, SessionLocal, engine
from .seed import seed_if_empty
from .routers import auth, backup, customers, knowledge, notes, projects, qa, recordings, requirements, tts
from .platform.routers import org as platform_org
from .platform.routers import subsystems as platform_subsystems
from .platform.routers import permissions as platform_permissions
from .platform.routers import shared_data as platform_shared


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：建表（缺表）+ 幂等种子（仅库为空时） + 日志骨架。"""
    setup_logging()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="yika 企业业务集成平台", lifespan=lifespan)
register_error_handlers(app)

# CORS 白名单（生产级 §10.3）：内网域名/IP；开发允许 5173/4173
# 生产环境通过 CORS_ORIGINS（逗号分隔）注入，未配置时允许本机 Vite 端口
_cors_origins = [o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()]
if not _cors_origins:
    _cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(projects.router)
app.include_router(requirements.router)
app.include_router(knowledge.router)
app.include_router(backup.router)
app.include_router(qa.router)
app.include_router(recordings.router)
app.include_router(notes.router)
app.include_router(tts.router)
app.include_router(platform_org.router)
app.include_router(platform_subsystems.router)
app.include_router(platform_permissions.router)
app.include_router(platform_shared.router)
