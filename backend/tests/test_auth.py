import pytest

pytestmark = pytest.mark.l2


def test_register_login(client):
    r = client.post("/auth/register", json={"username": "alice", "password": "pw123", "role": "instructor"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert token

    r2 = client.post("/auth/login", json={"username": "alice", "password": "pw123"})
    assert r2.status_code == 200
    assert r2.json()["role"] == "instructor"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "bob", "password": "pw", "role": "developer"})
    r = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.l2
def test_authorization_header_authenticates(client):
    """文档 §12.1：请求走 Authorization: Bearer <token> 头应能认证（不靠 token 头/cookie）。"""
    client.post("/auth/register", json={"username": "alice", "password": "pw123", "role": "instructor"})
    token = client.post("/auth/login", json={"username": "alice", "password": "pw123"}).json()["token"]
    r = client.get("/permissions/mine", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "instructor"


@pytest.mark.l2
def test_authorization_header_priority_over_token_header(client):
    """Authorization 头优先于自定义 token 头。"""
    client.post("/auth/register", json={"username": "carol", "password": "pw1", "role": "instructor"})
    client.post("/auth/register", json={"username": "dave", "password": "pw2", "role": "leader"})
    t_instr = client.post("/auth/login", json={"username": "carol", "password": "pw1"}).json()["token"]
    t_leader = client.post("/auth/login", json={"username": "dave", "password": "pw2"}).json()["token"]
    # 同时带 Authorization(leader) 与 token(instructor) → 应认 Authorization
    r = client.get("/permissions/mine", headers={"Authorization": f"Bearer {t_leader}", "token": t_instr})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "leader"
