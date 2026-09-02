import pytest

pytestmark = pytest.mark.l2


def _token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_export_requires_admin(client):
    t = _token(client, "tech1", "developer")
    r = client.get("/backup/export", headers={"token": t})
    assert r.status_code == 403
    a = _token(client, "admin1", "admin")
    r2 = client.get("/backup/export", headers={"token": a})
    assert r2.status_code == 200
    assert "requirements" in r2.json()
