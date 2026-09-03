"""QA 答疑（v3）：RAG 命中 / 未命中标记待答 / 答后回流知识库。

v2→v3 迁移要点：
- 建用户不再用 /auth/register（只建无组用户），改用 make_org_user（admin 经 /org/groups+/org/users 建进组用户）。
- 知识库用 body（非 content），source_enum（非 source）；POST /knowledge/ 需 developer/leader/admin。
"""
import pytest

pytestmark = pytest.mark.l2


def test_ask_hits_knowledge(client, make_org_user):
    u = make_org_user("developer")
    h = {"token": u["token"]}
    client.post("/knowledge/", json={
        "title": "什么是agent",
        "body": "agent是能自主执行任务的AI",
        "tags": ["ai"],
        "source_enum": "manual",
    }, headers=h)
    r = client.post("/qa/ask", json={"question": "什么是agent"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["needs_human"] is False
    assert "agent" in body["answer"]
    assert body["source"] == "什么是agent"


def test_ask_no_hit_marks_pending(client, make_org_user):
    u = make_org_user("instructor")
    r = client.post("/qa/ask", json={"question": "完全不知道的问题xyz"},
                    headers={"token": u["token"]})
    assert r.status_code == 200, r.text
    assert r.json()["needs_human"] is True


def test_tech_answer_reflows_to_knowledge(client, make_org_user):
    u = make_org_user("developer")
    h = {"token": u["token"]}
    qid = client.post("/qa/ask", json={"question": "如何部署agent"}, headers=h).json()["id"]
    client.post(f"/qa/{qid}/answer", json={"answer": "部署步骤是..."}, headers=h)
    r = client.get("/knowledge/", headers=h)
    assert any("如何部署" in k["title"] for k in r.json())
