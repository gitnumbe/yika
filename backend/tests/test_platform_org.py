"""P1.2 组织模型 API L2 权限测试。

覆盖：
- admin 建组 / 列组 / 指派组长 / 建用户
- 非 admin（leader/instructor/developer）访问组织管理 → 403（越权）
- 指派组长时被指派人必须为 leader 角色；组/用户不存在 → 404
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _admin_token(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    return r.json()["token"]


def _mk_user_token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw123456", "role": role})
    r = client.post("/auth/login", json={"username": username, "password": "pw123456"})
    return r.json()["token"]


def _h(tok):
    return {"token": tok}


def test_admin_create_and_list_groups(client):
    t = _admin_token(client)
    r = client.post("/org/groups", json={"name": "测试组A"}, headers=_h(t))
    assert r.status_code == 201
    gid = r.json()["id"]
    r2 = client.get("/org/groups", headers=_h(t))
    assert r2.status_code == 200
    names = [g["name"] for g in r2.json()]
    assert "测试组A" in names


def test_admin_create_user_and_assign_leader(client):
    t = _admin_token(client)
    # 建组
    gid = client.post("/org/groups", json={"name": "组B"}, headers=_h(t)).json()["id"]
    # 建组长
    uid = client.post("/org/users", json={
        "username": "组长甲", "password": "pw123456", "role": "leader",
        "display_name": "组长甲", "group_ids": [gid]}, headers=_h(t)).json()["id"]
    r = client.post(f"/org/groups/{gid}/leader", json={"leader_user_id": uid}, headers=_h(t))
    assert r.status_code == 200
    assert r.json()["leader_user_id"] == uid


def test_non_admin_forbidden(client):
    for role in ["leader", "instructor", "developer"]:
        tok = _mk_user_token(client, f"u_{role}_{__import__('uuid').uuid4().hex[:4]}", role)
        r = client.post("/org/groups", json={"name": "越权组"}, headers=_h(tok))
        assert r.status_code == 403, f"{role} 应 403"
        r2 = client.get("/org/users", headers=_h(tok))
        assert r2.status_code == 403


def test_assign_wrong_role_400(client):
    t = _admin_token(client)
    gid = client.post("/org/groups", json={"name": "组C"}, headers=_h(t)).json()["id"]
    # 建一个 developer，不能当组长
    uid = client.post("/org/users", json={
        "username": "开发乙", "password": "pw123456", "role": "developer"}, headers=_h(t)).json()["id"]
    r = client.post(f"/org/groups/{gid}/leader", json={"leader_user_id": uid}, headers=_h(t))
    assert r.status_code == 400


def test_group_not_found_404(client):
    t = _admin_token(client)
    r = client.post("/org/groups/99999/leader", json={"leader_user_id": 1}, headers=_h(t))
    assert r.status_code == 404
