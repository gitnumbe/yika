import json

import pytest

pytestmark = pytest.mark.l1

from app.services import pipeline as pl
from app.services import asr as asr_module
from app.services import audio as audio_module
from app.services import denoise as denoise_module
from app.services import note_gen as note_gen_module


def _make_biz_context(db, user):
    """v3：Note 挂在 customer 下。建 Group→Customer→Project 供录音关联（project_id）。"""
    from app.models import Customer, Group, Project

    group = Group(name="测试业务组")
    db.add(group)
    db.flush()
    customer = Customer(group_id=group.id, name="演示客户", created_by=user.id)
    db.add(customer)
    db.flush()
    project = Project(customer_id=customer.id, group_id=group.id, name="一期项目")
    db.add(project)
    db.commit()
    return group.id, customer.id, project.id


def _make_user(db, username, role="instructor"):
    from app.models import User

    user = User(username=username, password_hash="h", role=role)
    db.add(user)
    db.commit()
    return user


def _write_tmp_audio(name, content=b"fake"):
    with open(name, "wb") as f:
        f.write(content)


def test_pipeline_orders_stages(monkeypatch, db):
    """验证流水线按 音频准备→转写→去噪→笔记 顺序调用，并落 v3 Note（挂 customer）。"""
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

    from app.models import Recording

    user = _make_user(db, "u")
    group_id, customer_id, project_id = _make_biz_context(db, user)
    _write_tmp_audio("_tmp_test_audio.webm")
    rec = Recording(project_id=project_id, scene="req_discussion",
                    audio_path="_tmp_test_audio.webm", author_id=user.id)
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
    # v3：Note 挂 customer/group 下，四块结构化在 ai_structured
    assert note.customer_id == customer_id
    assert note.group_id == group_id
    assert note.scenario == "req_discussion"
    assert note.ai_structured["summary"] == "摘要"

    import os
    os.remove("_tmp_test_audio.webm")


def test_pipeline_raises_on_transcode_error(monkeypatch, db):
    """转码失败抛 AudioTranscodeError（由任务层标记重试）。"""
    from app.services.audio import AudioTranscodeError

    def bad_prepare(path):
        raise AudioTranscodeError("ffmpeg not found")

    monkeypatch.setattr(audio_module, "prepare_audio", bad_prepare)

    from app.models import Recording

    user = _make_user(db, "u2")
    _write_tmp_audio("_tmp_test_audio2.webm")
    rec = Recording(audio_path="_tmp_test_audio2.webm", scene="req_discussion", author_id=user.id)
    db.add(rec)
    db.commit()

    with pytest.raises(AudioTranscodeError):
        pl.process_recording(db, rec.id)
    assert rec.status == "preparing"  # 停在准备态，未污染下游

    import os
    os.remove("_tmp_test_audio2.webm")
