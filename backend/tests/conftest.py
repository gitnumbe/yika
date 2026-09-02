import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"

from app.database import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_if_empty  # noqa: E402


@pytest.fixture()
def db():
    """每个测试重建 test.db（drop_all→create_all→seed），隔离且保证 app 全局 engine 可用。"""
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    seed_if_empty(session)
    yield session
    session.close()


@pytest.fixture()
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
