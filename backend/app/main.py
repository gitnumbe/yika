from fastapi import FastAPI

from . import models  # noqa: F401  确保模型注册到 Base.metadata
from .database import Base, engine
from .routers import auth, customers, knowledge, projects, requirements

app = FastAPI(title="Team Collab Agent")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(projects.router)
app.include_router(requirements.router)
app.include_router(knowledge.router)

Base.metadata.create_all(bind=engine)
