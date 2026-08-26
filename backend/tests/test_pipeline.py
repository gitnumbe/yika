import pytest

pytestmark = pytest.mark.l1

from app.services import pipeline as pl
from app.services import asr as asr_module
from app.services import denoise as denoise_module
from app.services import note_gen as note_gen_module


def test_pipeline_orders_stages(monkeypatch, db):
    """验证流水线按 转写→去噪→笔记 顺序调用，并落 Note。"""
    calls = []

    class FakeASR:
        def transcribe(self, audio_bytes):
            calls.append("asr")
            return "原始转写"

    class FakeDenoiseLLM:
        def chat(self, messages):
            calls.append("denoise")
            return "清洗后"

    class FakeNoteLLM:
        def chat(self, messages):
            calls.append("note")
            import json
            return json.dumps({"summary": "摘要", "points": "要点", "decisions": "决策", "todos": "待办"})

    monkeypatch.setattr(asr_module, "get_asr", lambda: FakeASR())
    monkeypatch.setattr(denoise_module, "get_denoise_llm", lambda: FakeDenoiseLLM())
    monkeypatch.setattr(note_gen_module, "get_llm", lambda: FakeNoteLLM())

    # 造一条 Recording + 音频文件
    from app.models import Recording, User
    import os

    user = User(username="u", password_hash="h", role="instructor")
    db.add(user)
    db.commit()
    with open("_tmp_test_audio.webm", "wb") as f:
        f.write(b"fake")
    rec = Recording(audio_path="_tmp_test_audio.webm", scene="internal", author_id=user.id)
    db.add(rec)
    db.commit()

    pl.process_recording(db, rec.id)

    # 顺序必须是 asr -> denoise -> note
    assert calls == ["asr", "denoise", "note"]
    # 状态走到 done
    assert rec.status == "done"
    # 转录被清洗文本覆盖
    assert rec.transcript == "清洗后"

    # 生成了 Note
    from app.models import Note
    note = db.query(Note).first()
    assert note is not None
    assert note.summary == "摘要"

    os.remove("_tmp_test_audio.webm")
