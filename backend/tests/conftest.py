import os
import uuid
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


@pytest.fixture()
def make_org_user(client):
    """用 admin 经 /org/groups + /org/users 建一个“进新组”的指定角色用户，返回其登录 token。

    v3 语义：客户/项目为组私有，用户须有组（group_ids）才能建客户/项目；/auth/register 只建无组用户。
    返回 dict: {token, id, group_id, username}。
    """
    def _make(role="developer", password="pw123456"):
        admin = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert admin.status_code == 200, admin.text
        atok = admin.json()["token"]
        suffix = uuid.uuid4().hex[:8]
        g = client.post("/org/groups", json={"name": f"grp_{role}_{suffix}"}, headers={"token": atok})
        assert g.status_code == 201, g.text
        gid = g.json()["id"]
        uname = f"u_{role}_{suffix}"
        u = client.post("/org/users",
                        json={"username": uname, "password": password, "role": role,
                              "group_ids": [gid], "display_name": uname},
                        headers={"token": atok})
        assert u.status_code == 201, u.text
        tok = client.post("/auth/login", json={"username": uname, "password": password}).json()["token"]
        return {"token": tok, "id": u.json()["id"], "group_id": gid, "username": uname}
    return _make
