from fastapi import FastAPI

from . import models  # noqa: F401  确保模型注册到 Base.metadata
from .database import Base, engine
from .routers import auth

app = FastAPI(title="Team Collab Agent")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)

Base.metadata.create_all(bind=engine)
