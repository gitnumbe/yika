"""L3 业务闭环测试：录音 → 笔记 → 需求 完整链路。

验证录音流水线端到端：上传录音 → 转写 → 去噪 → 笔记 → 提炼需求 → 确认落库。
这是系统"把沟通变成需求"的核心闭环。
"""
import pytest

pytestmark = pytest.mark.l3

from app.services import asr as asr_module
from app.services import audio as audio_module
from app.services import denoise as denoise_module
from app.services import note_gen as note_gen_module
from app.services import req_extract as req_extract_module


def _register(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_recording_to_requirement_closed_loop(client, monkeypatch):
    """录音 → 转写 → 去噪 → 笔记 → 提炼 → 确认，全程跑通。"""
    # mock 全部 AI 依赖（含音频转码——ffmpeg 属环境依赖，测试不依赖真实二进制）
    class FakeAudio:
        def prepare_audio(self, path):
            return b"wav-bytes"

    class FakeASR:
        def transcribe(self, audio_bytes):
            return "客户说想要一个自动回复功能，嗯，就是能自动回消息"

    class FakeDenoiseLLM:
        def chat(self, messages):
            import json
            # 新契约：返回 JSON 数组（sentence/keep/reason）
            return json.dumps([
                {"sentence": "客户说想要一个自动回复功能", "keep": True, "reason": "干货"},
                {"sentence": "嗯", "keep": False, "reason": "寒暄"},
            ])

    class FakeNoteLLM:
        def chat(self, messages):
            import json
            return json.dumps({
                "summary": "客户要自动回复",
                "points": [{"topic": "自动回复", "detail": "自动回消息"}],
                "decisions": [],
                "todos": [{"owner": "技术", "item": "评估可行性", "pending": True}],
            })

    class FakeReqLLM:
        def chat(self, messages):
            import json
            return json.dumps([{"title": "自动回复功能", "description": "客户想要自动回复", "source_ref": "客户说想要一个自动回复功能", "confidence": 0.9, "reason": "客户明确提及"}])

    monkeypatch.setattr(audio_module, "prepare_audio", FakeAudio().prepare_audio)
    monkeypatch.setattr(asr_module, "get_asr", lambda: FakeASR())
    monkeypatch.setattr(denoise_module, "get_denoise_llm", lambda: FakeDenoiseLLM())
    monkeypatch.setattr(note_gen_module, "get_llm", lambda: FakeNoteLLM())
    monkeypatch.setattr(req_extract_module, "get_llm", lambda: FakeReqLLM())

    tech_token = _register(client, "技术录音1", "tech")
    th = {"token": tech_token}

    # 1. 上传录音（后台线程异步处理）
    r = client.post(
        "/recordings/upload",
        files={"audio": ("a.webm", b"fake-audio", "audio/webm")},
        data={"scene": "discussion"},
        headers=th,
    )
    assert r.status_code == 200
    rec_id = r.json()["id"]

    # 2. 等待流水线完成（轮询状态，最长 5 秒）
    import time
    status = None
    s = None
    for _ in range(50):
        s = client.get(f"/recordings/{rec_id}/status", headers=th).json()
        status = s["status"]
        if status == "done":
            break
        time.sleep(0.1)
    assert status == "done"
    assert s["transcript"] == "客户说想要一个自动回复功能"

    # 3. 笔记已生成
    notes = client.get("/notes/", headers=th).json()
    assert len(notes) == 1
    note_id = notes[0]["id"]

    # 4. 提炼候选需求（不落库；返回 {candidates, quality} 契约）
    extract_resp = client.post(f"/notes/{note_id}/extract", headers=th).json()
    candidates = extract_resp["candidates"]
    assert extract_resp["quality"]["degraded"] is False
    assert len(candidates) == 1
    assert candidates[0]["title"] == "自动回复功能"
    assert candidates[0]["source_ref"] == "客户说想要一个自动回复功能"

    # 5. 确认后落库为草稿
    confirmed = client.post(
        f"/notes/{note_id}/confirm-requirements",
        json={"candidates": candidates},
        headers=th,
    ).json()
    assert len(confirmed) == 1

    # 6. 需求库出现草稿
    reqs = client.get("/requirements/", headers=th).json()
    assert any(r["title"] == "自动回复功能" and r["status"] == "draft" for r in reqs)


def test_extract_does_not_persist_without_confirm(client, monkeypatch):
    """防幻觉铁律：extract 只返回候选，不 confirm 就不落库。"""
    class FakeReqLLM:
        def chat(self, messages):
            import json
            return json.dumps([{"title": "候选需求X", "description": "", "source_ref": ""}])

    monkeypatch.setattr(req_extract_module, "get_llm", lambda: FakeReqLLM())

    tech_token = _register(client, "技术录音2", "tech")
    th = {"token": tech_token}

    r = client.post("/notes/99999/extract", headers=th)
    assert r.status_code == 404

    reqs = client.get("/requirements/", headers=th).json()
    assert reqs == []
