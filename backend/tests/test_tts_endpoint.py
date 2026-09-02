"""L2 TTS 朗读端点测试（mock dots-tts 服务，不实调模型）。

验证：笔记/答疑朗读懒合成 + 缓存复用 + 权限 + wav 取用。
"""
import json

import pytest

pytestmark = pytest.mark.l2


def _register(client, username, role="instructor"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]


def test_note_tts_synthesize_then_cached(client, monkeypatch, tmp_path):
    """首次朗读合成 wav 并缓存；再次朗读命中缓存（不再调服务）。"""
    import json as _json
    from app.services import tts as tts_module
    from app.services import note_gen as note_gen_module
    from app.services import llm as llm_module

    class FakeNoteLLM:
        def chat(self, messages):
            return _json.dumps({"summary": "客户要自动回复", "points": [{"topic": "a", "detail": "b"}], "decisions": [], "todos": []})

    # 造笔记（借助录音流水线 mock 或直接走 note_gen）
    monkeypatch.setattr(note_gen_module, "get_llm", lambda: FakeNoteLLM())
    monkeypatch.setattr(llm_module, "get_llm", lambda: FakeNoteLLM())

    calls = {"n": 0}

    class FakeTTS:
        def speak(self, text, voice_ref="default"):
            calls["n"] += 1
            return b"RIFF....wavedata"

    monkeypatch.setattr(tts_module, "get_tts", lambda: FakeTTS())
    # 隔离到 tmp 存储
    monkeypatch.setattr("app.routers.tts.STORAGE_ROOT", str(tmp_path))

    tok = _register(client, "朗读用户")
    th = {"token": tok}

    # 造一条笔记（走 note_gen 生成 Note + 用户）
    from app.database import SessionLocal
    from app.models import Note, User
    db = SessionLocal()
    u = db.query(User).filter(User.username == "朗读用户").first()
    note_data = note_gen_module.generate_note("客户想要自动回复功能")
    note = Note(
        scene="discussion",
        transcript="客户想要自动回复功能",
        author_id=u.id,
        summary=note_data["summary"],
        points=json.dumps(note_data.get("points") or [], ensure_ascii=False),
        decisions=json.dumps(note_data.get("decisions") or [], ensure_ascii=False),
        todos=json.dumps(note_data.get("todos") or [], ensure_ascii=False),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    note_id = note.id
    db.close()

    # 首次朗读 → 合成
    r = client.post(f"/notes/{note_id}/tts", headers=th)
    assert r.status_code == 200
    data = r.json()
    assert data["cached"] is False
    assert calls["n"] == 1
    assert data["audio_url"].endswith(".wav")

    # 再次朗读 → 缓存命中
    r2 = client.post(f"/notes/{note_id}/tts", headers=th)
    assert r2.status_code == 200
    assert r2.json()["cached"] is True
    assert calls["n"] == 1  # 未再调服务

    # wav 可取
    wav = client.get(data["audio_url"], headers=th)
    assert wav.status_code == 200
    assert wav.headers["content-type"] == "audio/wav"
    assert wav.content[:4] == b"RIFF"


def test_note_tts_requires_auth(client):
    tok = _register(client, "未登录用户")
    # 不带 token
    r = client.post("/notes/1/tts")
    assert r.status_code == 401


def test_note_tts_404(client):
    tok = _register(client, "无笔记用户")
    th = {"token": tok}
    r = client.post("/notes/99999/tts", headers=th)
    assert r.status_code == 404
