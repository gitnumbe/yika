def _token(client, username="tech1", role="tech"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_full_review_flow(client):
    t = _token(client)
    h = {"token": t}
    r = client.post("/requirements/", json={"title": "自动回复客户咨询"}, headers=h).json()
    rid = r["id"]
    # draft -> pending_review
    client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h)
    # pending_review -> info_needed
    client.post(f"/requirements/{rid}/transition", json={"to": "info_needed", "reason": "需向客户确认并发量"}, headers=h)
    # info_needed -> pending_review
    r2 = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h)
    assert r2.json()["status"] == "pending_review"


def test_illegal_transition_rejected(client):
    t = _token(client)
    h = {"token": t}
    rid = client.post("/requirements/", json={"title": "x"}, headers=h).json()["id"]
    # draft 直接跳到 delivered 应被拒
    r = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"}, headers=h)
    assert r.status_code == 400


def test_instructor_cannot_transition(client):
    t = _token(client, username="inst1", role="instructor")
    h = {"token": t}
    rid = client.post("/requirements/", json={"title": "x"}, headers=h).json()["id"]
    r = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h)
    assert r.status_code == 403
