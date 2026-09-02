"""P1.4b 权限查询接口测试（界面级权限提示依据）。

覆盖：leader/instructor/developer/admin 各角色的权限点正确。
- can_review 仅 leader
- can_manage_org 仅 admin
- can_write_knowledge admin/developer/leader
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _mk_and_login(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw123456", "role": role})
    r = client.post("/auth/login", json={"username": username, "password": "pw123456"})
    return r.json()["token"]


def _perms(client, tok):
    return client.get("/permissions/mine", headers={"token": tok}).json()


def test_leader_review_only(client):
    tok = _mk_and_login(client, "组长权", "leader")
    p = _perms(client, tok)
    assert p["can_review"] is True
    assert p["can_manage_org"] is False


def test_instructor_no_review_no_manage(client):
    tok = _mk_and_login(client, "讲师权", "instructor")
    p = _perms(client, tok)
    assert p["can_review"] is False
    assert p["can_deliver"] is False
    assert p["can_manage_org"] is False
    assert p["can_write_knowledge"] is False


def test_developer_deliver_knowledge_not_manage(client):
    tok = _mk_and_login(client, "开发权", "developer")
    p = _perms(client, tok)
    assert p["can_review"] is False
    assert p["can_deliver"] is True
    assert p["can_write_knowledge"] is True
    assert p["can_manage_org"] is False


def test_admin_all_manage(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    tok = r.json()["token"]
    p = _perms(client, tok)
    assert p["can_manage_org"] is True and p["can_manage_subsystem"] is True
