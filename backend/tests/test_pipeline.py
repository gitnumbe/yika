import json

import pytest

pytestmark = pytest.mark.l1

from app.services import pipeline as pl
from app.services import asr as asr_module
from app.services import audio as audio_module
from app.services import denoise as denoise_module
from app.services import note_gen as note_gen_module


def test_pipeline_orders_stages(monkeypatch, db):
    """验证流水线按 音频准备→转写→去噪→笔记 顺序调用，并落 Note。"""
    calls = []

    class FakeAudio:
        def prepare_audio(self, path):
            calls.append("audio")
            return b"wav-bytes"

    class FakeASR:
        def transcribe(self, audio_bytes):
            calls.append("asr")
            return "原始转写"

    class FakeDenoiseLLM:
        def chat(self, messages):
            calls.append("denoise")
            return json.dumps([
                {"sentence": "原始转写", "keep": True, "reason": "保留"},
            ])

    class FakeNoteLLM:
        def chat(self, messages):
            calls.append("note")
            return json.dumps({"summary": "摘要", "points": [{"topic": "a", "detail": "b"}], "decisions": [], "todos": []})

    monkeypatch.setattr(audio_module, "prepare_audio", FakeAudio().prepare_audio)
    monkeypatch.setattr(asr_module, "get_asr", lambda: FakeASR())
    monkeypatch.setattr(denoise_module, "get_denoise_llm", lambda: FakeDenoiseLLM())
    monkeypatch.setattr(note_gen_module, "get_llm", lambda: FakeNoteLLM())

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

    # 顺序必须是 audio -> asr -> denoise -> note
    assert calls == ["audio", "asr", "denoise", "note"]
    assert rec.status == "done"
    assert rec.transcript == "原始转写"  # 去噪 keep=true 保留原文

    from app.models import Note
    note = db.query(Note).first()
    assert note is not None
    assert note.summary == "摘要"

    os.remove("_tmp_test_audio.webm")


def test_pipeline_raises_on_transcode_error(monkeypatch, db):
    """转码失败抛 AudioTranscodeError（由任务层标记重试）。"""
    from app.services.audio import AudioTranscodeError

    def bad_prepare(path):
        raise AudioTranscodeError("ffmpeg not found")

    monkeypatch.setattr(audio_module, "prepare_audio", bad_prepare)

    from app.models import Recording, User
    import os

    user = User(username="u2", password_hash="h", role="instructor")
    db.add(user)
    db.commit()
    with open("_tmp_test_audio2.webm", "wb") as f:
        f.write(b"fake")
    rec = Recording(audio_path="_tmp_test_audio2.webm", scene="internal", author_id=user.id)
    db.add(rec)
    db.commit()

    with pytest.raises(AudioTranscodeError):
        pl.process_recording(db, rec.id)
    assert rec.status == "preparing"  # 停在准备态，未污染下游

    os.remove("_tmp_test_audio2.webm")
