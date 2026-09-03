"""P7a.1 A1 客户建档端点测试（mock AI，不依赖真实 LLM）。

验证 POST /customers/{cid}/analyze：
- 调 A1 后写回 ai_status=done + ai_flags 存档案
- 不覆盖人工已填字段（防幻觉：AI 结果存 ai_flags 而非覆写 industry/scale）
- 组隔离：跨组 analyze 404
"""
import uuid

import pytest

pytestmark = pytest.mark.l1


def test_analyze_writes_ai_flags(client, make_org_user, monkeypatch):
    u = make_org_user(role="developer")
    tok = u["token"]

    # 建客户
    c = client.post("/customers/", json={"name": "A1测试客户", "industry": "制造"},
                    headers={"token": tok}).json()

    # mock profile.analyze 返回结构化档案
    import app.core.ai.profile as profile_mod
    def fake_analyze(company, sources_text=None, true_profile=None):
        return {
            "company": company,
            "profile": {"industry": "工业软件", "scale": "大型", "main_business": "自研MES",
                        "background": "成立2005", "website": ""},
            "validation": {"company": {"need_human": False}},
        }
    monkeypatch.setattr(profile_mod, "analyze", fake_analyze)

    r = client.post(f"/customers/{c['id']}/analyze", headers={"token": tok})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ai_status"] == "done"
    # ai_flags 存了档案
    assert data["ai_flags"][0]["industry"] == "工业软件"
    assert data["ai_flags"][0]["scale"] == "大型"

    # 人工填的 industry（"制造"）未被覆盖（防幻觉）
    detail = client.get(f"/customers/{c['id']}", headers={"token": tok}).json()
    assert detail["industry"] == "制造"


def test_analyze_cross_group_404(client, make_org_user):
    uA = make_org_user(role="developer")
    tokA = uA["token"]
    uB = make_org_user(role="developer")
    tokB = uB["token"]

    cid = client.post("/customers/", json={"name": "A组客户"}, headers={"token": tokA}).json()["id"]
    r = client.post(f"/customers/{cid}/analyze", headers={"token": tokB})
    assert r.status_code == 404
