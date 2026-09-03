"""L3 业务闭环测试：沟通记录(Note) → 候选需求 → 确认转正式需求（v3 语义）。

v3：Note 挂客户(customer_id)下、组私有、scenario=req_discussion、结构化存 ai_structured
(模型无 v2 的 summary/points/decisions/todos/scene/project_id)；需求溯源字段=source_note_id。
候选需求仅 extract 产候选(不落库——防幻觉)，人工确认后转正式需求(Requirement)并带
source_note_id 溯源。

【阻塞说明】录音→Note 的自动流水线(app/services/pipeline.py 仍用 v2 Note 字段 scene/
summary/points/decisions/todos/project_id/author_id 构造 v3 Note)与 notes.py 的
confirm-requirements 端点(P3.4)为主 agent 重写范围，故本文件直接经 db fixture 按 v3 权威模型
落一条 Note，验证其后「候选→确认→正式需求带 source_note_id」链路；不实测语音(保留 mock 手法)。
"""
import uuid

import pytest

pytestmark = pytest.mark.l3

from app.models import Customer, Note, User  # noqa: E402
from app.services import req_extract as req_extract_module  # noqa: E402

DEVELOPER = ("developer1", "developer123")  # 种子：开发，属 技术组


def _login(c, u=DEVELOPER[0], p=DEVELOPER[1]):
    r = c.post("/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _seed_note(db, transcript="客户说想要一个自动回复功能，能自动回消息"):
    """按 v3 Note 模型落一条挂客户下的 req_discussion Note，返回 (note_id, customer_id)。"""
    cid = db.query(Customer).first()  # 测试已先建客户+项目
    assert cid is not None, "需先在组内建客户"
    note_author = db.query(User).filter(User.username == "developer1").first()
    note = Note(
        customer_id=cid.id,
        group_id=cid.group_id,
        scenario="req_discussion",
        transcript=transcript,
        ai_structured={},
        quality_flags={},
        note_author_id=note_author.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note.id, cid.id


class _FakeLLM:
    def chat(self, messages):
        import json
        return json.dumps([{
            "title": "自动回复功能",
            "description": "客户想要自动回复",
            "source_ref": "客户说想要一个自动回复功能",
            "confidence": 0.9,
            "reason": "客户明确提及",
        }])


def _mock_req_llm(monkeypatch):
    monkeypatch.setattr(req_extract_module, "get_llm", lambda: _FakeLLM())


def _setup_customer_project(client, tok):
    """组内建客户+项目，供 Note 挂载与需求落库用。"""
    cid = client.post("/customers/", json={"name": f"录音客户_{uuid.uuid4().hex[:6]}"},
                      headers={"token": tok}).json()["id"]
    pid = client.post("/projects/", json={"name": "录音项目", "customer_id": cid},
                      headers={"token": tok}).json()["id"]
    return cid, pid


def test_note_extract_candidates_not_persist_until_confirm(client, db, monkeypatch):
    """防幻觉铁律：extract 只产候选，不 confirm/转正式 就不落正式需求。"""
    tok = _login(client)
    cid, pid = _setup_customer_project(client, tok)
    note_id, note_cid = _seed_note(db)

    # 不存在笔记 → 404
    assert client.post("/notes/999999/extract", headers={"token": tok}).status_code == 404

    # mock 提炼 LLM，extract 返回候选但不落库
    _mock_req_llm(monkeypatch)
    resp = client.post(f"/notes/{note_id}/extract", headers={"token": tok}).json()
    assert resp["quality"]["degraded"] is False
    assert len(resp["candidates"]) == 1
    assert resp["candidates"][0]["title"] == "自动回复功能"
    assert resp["candidates"][0]["source_ref"] == "客户说想要一个自动回复功能"

    # 仅 extract → 需求库仍为空
    assert client.get("/requirements/", headers={"token": tok}).json() == []
    assert pid is not None


def test_note_to_formal_requirement_with_source_trace(client, db, monkeypatch):
    """候选需求经人工确认转正式需求：Requirement.source_note_id 溯源到 Note，Note 挂客户。"""
    tok = _login(client)
    cid, pid = _setup_customer_project(client, tok)
    note_id, note_cid = _seed_note(db)
    assert note_cid == cid  # Note 挂客户下

    # 候选区
    _mock_req_llm(monkeypatch)
    cand = client.post(f"/notes/{note_id}/extract",
                       headers={"token": tok}).json()["candidates"][0]

    # 人工确认 → 以 ai_extract 来源转正式需求，并带 source_note_id 溯源(替代 v2 source_ref)
    created = client.post("/requirements/", json={
        "title": cand["title"],
        "description": cand["description"],
        "project_id": pid,
        "source": "ai_extract",
        "source_note_id": note_id,
        "ai_confidence": 0.9,
    }, headers={"token": tok})
    assert created.status_code == 200, created.text
    req = created.json()
    assert req["status"] == "draft"            # 转正式后默认草稿，待评审
    assert req["source"] == "ai_extract"
    assert req["source_note_id"] == note_id    # 溯源：非 v2 source_ref 字符串
    assert req["project_id"] == pid

    # 需求库出现该草稿，且可溯源到沟通记录
    reqs = client.get("/requirements/", headers={"token": tok}).json()
    match = [r for r in reqs if r["id"] == req["id"]]
    assert match and match[0]["title"] == "自动回复功能"
    assert match[0]["source_note_id"] == note_id
