"""P1.3 子系统注册清单 L2 测试（S1/S8 粒度2）。

覆盖：
- admin 注册子系统 / 停 / 下线 / 激活（数据保留无物理删除）
- /mine 按当前用户角色过滤（active 且角色匹配才出现）
- 停止/下线后 /mine 不再返回（隐藏入口但数据保留）
- 非 admin 不能管理子系统（403）
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _token(client, username="admin", password="admin123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    return r.json()["token"]


def _mk(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw123456", "role": role})
    return _token(client, username, "pw123456")


def _create(client, tok, key, name, roles):
    return client.post("/subsystems", json={
        "key": key, "name": name, "icon": "el-icon", "url": f"/{key}", "roles": roles},
        headers={"token": tok})


def test_admin_lifecycle_register_stop_archive_activate(client):
    t = _token(client)
    r = _create(client, t, "collab", "组内协作", ["leader", "instructor", "developer"])
    assert r.status_code == 201
    assert r.json()["status"] == "active"
    key = r.json()["key"]
    # 停
    r2 = client.post(f"/subsystems/{key}/stop", headers={"token": t})
    assert r2.json()["status"] == "stopped"
    # 下线
    r3 = client.post(f"/subsystems/{key}/archive", headers={"token": t})
    assert r3.json()["status"] == "archived"
    # 激活
    r4 = client.post(f"/subsystems/{key}/activate", headers={"token": t})
    assert r4.json()["status"] == "active"


def test_mine_filters_by_role_and_status(client):
    t = _token(client)
    _create(client, t, "collab", "组内协作", ["leader", "instructor", "developer"])
    _create(client, t, "kb", "知识库", ["admin"])
    # 讲师：应看到 collab（匹配角色），看不到 kb（仅 admin）
    inst = _mk(client, "讲师子", "instructor")
    mine = client.get("/subsystems/mine", headers={"token": inst}).json()
    keys = [s["key"] for s in mine]
    assert "collab" in keys
    assert "kb" not in keys


def test_stopped_hidden_from_mine(client):
    t = _token(client)
    _create(client, t, "collab", "组内协作", ["instructor"])
    inst = _mk(client, "讲师停", "instructor")
    # 停止后讲师不可见
    client.post("/subsystems/collab/stop", headers={"token": t})
    mine = client.get("/subsystems/mine", headers={"token": inst}).json()
    assert all(s["key"] != "collab" for s in mine)


def test_non_admin_cannot_manage(client):
    dev = _mk(client, "开发管理", "developer")
    r = client.post("/subsystems", json={"key": "x", "name": "x"}, headers={"token": dev})
    assert r.status_code == 403
