def _token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_tech_create_instructor_read(client):
    t = _token(client, "tech1", "tech")
    client.post("/knowledge/", json={"title": "agent 基础", "content": "..."}, headers={"token": t})
    i = _token(client, "inst1", "instructor")
    r = client.get("/knowledge/", headers={"token": i})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_instructor_cannot_create(client):
    i = _token(client, "inst2", "instructor")
    r = client.post("/knowledge/", json={"title": "x", "content": "y"}, headers={"token": i})
    assert r.status_code == 403
