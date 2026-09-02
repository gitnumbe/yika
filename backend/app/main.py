from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  确保模型注册到 Base.metadata
from .config import settings
from .database import Base, engine
from .routers import auth, backup, customers, knowledge, notes, projects, qa, recordings, requirements, tts

app = FastAPI(title="Team Collab Agent")

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

Base.metadata.create_all(bind=engine)
