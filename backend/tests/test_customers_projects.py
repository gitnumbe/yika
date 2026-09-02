import pytest

pytestmark = pytest.mark.l2


def _token(client, username="tech1", role="developer"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_create_customer_and_project(client):
    token = _token(client)
    h = {"token": token}
    c = client.post("/customers/", json={"name": "A公司", "industry": "制造"}, headers=h)
    assert c.status_code == 200
    cid = c.json()["id"]
    p = client.post("/projects/", json={"name": "A公司智能客服", "customer_id": cid}, headers=h)
    assert p.status_code == 200
    assert p.json()["customer_id"] == cid


def test_unauthenticated_rejected(client):
    r = client.get("/customers/")
    assert r.status_code == 401
