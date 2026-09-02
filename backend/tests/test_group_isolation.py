"""P1.4a 组隔离（group_id 数据归属）L3 越权测试。

核心：跨组水平越权必须被拦截。
- A 组用户建的客户，B 组用户经 /customers 读不到
- 无组用户不能创建客户（403）
- admin 可跨组看到所有组客户
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

G_SUF = uuid.uuid4().hex[:6]


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _token(client, username, password="admin123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    return r.json()["token"]


def _create_user(client, admin_tok, username, role, group_ids):
    return client.post("/org/users", json={
        "username": username, "password": "pw123456", "role": role, "group_ids": group_ids},
        headers={"token": admin_tok})


def test_cross_group_cannot_read(client):
    admin = _token(client, "admin")
    gid_a = client.post("/org/groups", json={"name": "组A_"+G_SUF+""}, headers={"token": admin}).json()["id"]
    gid_b = client.post("/org/groups", json={"name": "组B_"+G_SUF+""}, headers={"token": admin}).json()["id"]
    _create_user(client, admin, "讲师A", "instructor", [gid_a])
    _create_user(client, admin, "讲师B", "instructor", [gid_b])
    tok_a = _token(client, "讲师A", "pw123456")
    tok_b = _token(client, "讲师B", "pw123456")
    # A 组建客户
    c = client.post("/customers/", json={"name": "A的客户"}, headers={"token": tok_a}).json()
    # B 组读不到
    list_b = client.get("/customers/", headers={"token": tok_b}).json()
    assert all(x["name"] != "A的客户" for x in list_b)
    # A 组能看到
    list_a = client.get("/customers/", headers={"token": tok_a}).json()
    assert any(x["name"] == "A的客户" for x in list_a)


def test_user_without_group_cannot_create(client):
    admin = _token(client, "admin")
    # 建一个无组 instructor
    client.post("/org/users", json={"username": "无组员", "password": "pw123456", "role": "instructor"},
                headers={"token": admin})
    tok = _token(client, "无组员", "pw123456")
    r = client.post("/customers/", json={"name": "x"}, headers={"token": tok})
    assert r.status_code == 403


def test_admin_sees_all_groups(client):
    admin = _token(client, "admin")
    gid_a = client.post("/org/groups", json={"name": "组X_"+G_SUF+""}, headers={"token": admin}).json()["id"]
    gid_b = client.post("/org/groups", json={"name": "组Y_"+G_SUF+""}, headers={"token": admin}).json()["id"]
    _create_user(client, admin, "讲师X", "instructor", [gid_a])
    _create_user(client, admin, "讲师Y", "instructor", [gid_b])
    tx = _token(client, "讲师X", "pw123456")
    ty = _token(client, "讲师Y", "pw123456")
    client.post("/customers/", json={"name": "X客户"}, headers={"token": tx})
    client.post("/customers/", json={"name": "Y客户"}, headers={"token": ty})
    # admin 跨组全见
    all_list = client.get("/customers/", headers={"token": admin}).json()
    names = {x["name"] for x in all_list}
    assert "X客户" in names and "Y客户" in names
