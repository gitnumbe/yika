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
    client.post("/auth/register", json={"username": "bob", "password": "pw", "role": "tech"})
    r = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert r.status_code == 401
