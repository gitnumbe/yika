"""知识库 L2 测试（v3：全平台共通；开发/组长直接发布，讲师写进审核队列 draft）。"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _mk(c, role, pw="pw123456"):
    a = c.post("/auth/login", json={"username": "admin", "password": "admin123"}).json()["token"]
    suf = uuid.uuid4().hex[:6]
    g = c.post("/org/groups", json={"name": f"g_{role}_{suf}"}, headers={"token": a}).json()
    gid = g["id"]
    un = f"u_{role}_{suf}"
    c.post("/org/users", json={"username": un, "password": pw, "role": role,
                               "group_ids": [gid], "display_name": un}, headers={"token": a})
    return c.post("/auth/login", json={"username": un, "password": pw}).json()["token"]


def test_dev_write_instructor_read(client):
    """开发写知识(published)，讲师可读（全平台共通）。"""
    t = _mk(client, "developer")
    client.post("/knowledge/", json={"title": "agent 基础", "body": "..."}, headers={"token": t})
    i = _mk(client, "instructor")
    r = client.get("/knowledge/", headers={"token": i})
    assert r.status_code == 200
    assert any(k["title"] == "agent 基础" for k in r.json())


def test_instructor_write_is_draft_pending_review(client):
    """讲师写 → draft(待审核)，不是 403（v3 语义）。"""
    i = _mk(client, "instructor")
    r = client.post("/knowledge/", json={"title": "讲师答疑", "body": "y"}, headers={"token": i})
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
