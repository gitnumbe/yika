import pytest

pytestmark = pytest.mark.l2


def _token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_ask_hits_knowledge(client):
    t = _token(client, "tech1", "developer")
    h = {"token": t}
    client.post("/knowledge/", json={"title": "什么是agent", "content": "agent是能自主执行任务的AI"}, headers=h)
    r = client.post("/qa/ask", json={"question": "什么是agent"}, headers=h)
    assert r.json()["needs_human"] is False
    assert "agent" in r.json()["answer"]


def test_ask_no_hit_marks_pending(client):
    i = _token(client, "inst1", "instructor")
    r = client.post("/qa/ask", json={"question": "完全不知道的问题xyz"}, headers={"token": i})
    assert r.json()["needs_human"] is True


def test_tech_answer_reflows_to_knowledge(client):
    t = _token(client, "tech1", "developer")
    h = {"token": t}
    qid = client.post("/qa/ask", json={"question": "如何部署agent"}, headers=h).json()["id"]
    client.post(f"/qa/{qid}/answer", json={"answer": "部署步骤是..."}, headers=h)
    r = client.get("/knowledge/", headers=h)
    assert any("如何部署" in k["title"] for k in r.json())
