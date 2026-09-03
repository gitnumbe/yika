"""P1.5 共享主数据 API（S3）测试：组隔离强制，子系统经平台层不直连库。

覆盖：
- /api/shared/customers 按组隔离（A 组看不到 B 组客户）
- /api/shared/knowledge 全平台共通（跨组可见）
- /api/shared/me 返回当前用户角色/组
- 未登录访问共享 API → 401
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client, username, password="admin123"):
    return client.post("/auth/login", json={"username": username, "password": password}).json()["token"]


def _mk_group_and_user(client, admin, prefix, role="instructor"):
    gid = client.post("/org/groups", json={"name": f"{prefix}_{uuid.uuid4().hex[:5]}"},
                      headers={"token": admin}).json()["id"]
    client.post("/org/users", json={"username": prefix, "password": "pw123456",
                                    "role": role, "group_ids": [gid]},
                headers={"token": admin})
    return gid


def _add_customer(client, tok, name):
    return client.post("/customers/", json={"name": name}, headers={"token": tok})


def test_shared_customers_group_isolation(client):
    admin = _login(client, "admin")
    _mk_group_and_user(client, admin, "共享A")
    _mk_group_and_user(client, admin, "共享B")
    ta = _login(client, "共享A", "pw123456")
    tb = _login(client, "共享B", "pw123456")
    _add_customer(client, ta, "A共享客户")
    # B 经共享 API 读不到 A 客户
    shared_b = client.get("/api/shared/customers", headers={"token": tb}).json()
    assert all(c["name"] != "A共享客户" for c in shared_b)
    # A 能读到
    shared_a = client.get("/api/shared/customers", headers={"token": ta}).json()
    assert any(c["name"] == "A共享客户" for c in shared_a)


def test_shared_knowledge_all_groups(client):
    admin = _login(client, "admin")
    _mk_group_and_user(client, admin, "知A", role="developer")  # A 组开发能直接发布知识
    _mk_group_and_user(client, admin, "知B")
    ta = _login(client, "知A", "pw123456")
    # A 组开发写一条知识（全平台共通；published 直接入）
    client.post("/knowledge/", json={"title": "共享知识条", "body": "内容"},
                headers={"token": ta})
    tb = _login(client, "知B", "pw123456")
    kb = client.get("/api/shared/knowledge", headers={"token": tb}).json()
    assert any(k["title"] == "共享知识条" for k in kb)  # 跨组可见


def test_shared_me(client):
    admin = _login(client, "admin")
    me = client.get("/api/shared/me", headers={"token": admin}).json()
    assert me["role"] == "admin"
    assert me["username"] == "admin"


def test_shared_requires_auth(client):
    r = client.get("/api/shared/knowledge")
    assert r.status_code == 401
