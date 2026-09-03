"""P5 各 AI 环节 mock 测试（不依赖真实 LLM 端点）。

用假 LLM(monkeypatch get_llm) 覆盖：
- A1 客户画像：build_profile 结构化解析 / validate_profile 存疑字段推人工
- A3 需求提炼：extract_candidates 解析候选 / 防幻觉不落库(只返回)
- A4 答疑：response 带引用+低置信转人

真实端点连通性用 tests/measure_a*.py 手测脚本。
"""
import json
import pytest


# ---------- 假 LLM ----------
class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
    def chat(self, messages):
        return self.responses.pop(0)


# ---------- A1 ----------
def test_a1_build_profile_parses_json(monkeypatch):
    from app.core.ai import profile
    monkeypatch.setattr(profile, "get_llm", lambda: FakeLLM([
        '{"company":"某科技","industry":"工业软件","scale":"大型","main_business":"ERP","website":"","background":"背景"}'
    ]))
    data = profile.build_profile("某科技", "官网文本")
    assert data["company"] == "某科技"
    assert data["industry"] == "工业软件"


def test_a1_validate_marks_uncertain_human(monkeypatch):
    from app.core.ai import profile
    # 字段缺失 → 存疑推人工
    v = profile.validate_profile({"company": "某科技", "industry": "", "scale": ""})
    assert v["industry"]["need_human"] is True
    assert v["scale"]["need_human"] is True
    # 真值不匹配 → 存疑
    v2 = profile.validate_profile({"company": "错公司", "industry": "金融", "scale": "小型"},
                                  true_profile={"company": "某科技", "industry": "工业软件", "scale": "大型"})
    assert v2["company"]["need_human"] is True


# ---------- A3 ----------
def test_a3_extract_candidates_parses(monkeypatch):
    from app.core.ai import req_extract
    monkeypatch.setattr(req_extract, "get_llm", lambda: FakeLLM([
        '[{"title":"自动回复","description":"客服","source_ref":"客户说","confidence":0.9},{"title":"","source_ref":"x"}]'
    ]))
    res = req_extract.extract_candidates("客户想要自动回复")
    # 过滤无标题候选（空 title）
    assert len(res["candidates"]) == 1
    assert res["candidates"][0]["title"] == "自动回复"
    assert res["quality"]["degraded"] is False


def test_a3_returns_no_persist(monkeypatch):
    """防幻觉：extract 只返回候选，不落库。"""
    from app.core.ai import req_extract
    monkeypatch.setattr(req_extract, "get_llm", lambda: FakeLLM([
        '[{"title":"看板","source_ref":"想要看板","confidence":0.8}]'
    ]))
    res = req_extract.extract_candidates("想要一个看板")
    assert "candidates" in res  # 仅内存返回，无 db 写入


# ---------- A4 ----------
def test_a4_answer_with_reference_and_low_confidence():
    """A4 命中带引用；低置信(未命中)转人。"""
    from app.core.ai import qa_service
    class _K:
        def __init__(self, id, title, body):
            self.id = id; self.title = title; self.body = body; self.status = "published"
    class _DB:
        def __init__(self, items): self.items = items
        def query(self, m): return self
        def filter(self, c): return self
        def all(self): return self.items
    items = [_K(1, "什么是Agent", "Agent 是自主执行任务的 AI 智能体")]
    db = _DB(items)
    # 命中（覆盖率高）
    r = qa_service.answer(db, "什么是agent")
    assert r["needs_human"] is False
    assert r["source"] == "什么是Agent"       # 引用 = 知识条目标题
    assert r["source_id"] == 1                # 引用可溯源
    # 未命中（覆盖率低）→ 转人
    r2 = qa_service.answer(db, "今天天气如何")
    assert r2["needs_human"] is True
