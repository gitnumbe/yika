"""P6 语音链路新增点测试（mock ASR/LLM，不实测语音推理）。

覆盖：
- P6.2 ASR provider 切换（third_party 兜底 provider 的请求形态）
- P6.3 A6 四块完整性度量（完整→达标；缺失→留空不强行生成）
- P6.4 Recording 直接挂 customer（upload 传 customer_id + 组隔离校验）
- P6.5 录音→流水线落 Note 挂 customer（customer_id 优先于 project 反查）→ A3 素材可用
"""
import json
import uuid

import pytest

pytestmark = pytest.mark.l3

from app.models import Recording  # noqa: E402


# ---------- P6.2 ASR provider 切换 ----------

def test_asr_third_party_provider_shape(monkeypatch):
    """third_party provider：POST {url}/v1/audio/transcriptions，带 Bearer + model。"""
    import httpx

    from app.services import asr as asr_module

    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"text": "第三方转写结果"}

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        return FakeResp()

    monkeypatch.setattr(httpx, "post", fake_post)

    prov = asr_module.ThirdPartyASRProvider(
        "http://tp.example.com", api_key="k-secret", model="whisper-x"
    )
    text = prov.transcribe(b"wav-bytes", language="zh")
    assert text == "第三方转写结果"
    assert captured["url"] == "http://tp.example.com/v1/audio/transcriptions"
    assert captured["headers"] == {"Authorization": "Bearer k-secret"}
    assert captured["data"] == {"model": "whisper-x", "language": "zh"}


def test_asr_get_provider_switch(monkeypatch):
    """get_asr() 按 settings.asr_provider 切换 qwen / third_party。"""
    from app.services import asr as asr_module

    # 默认 qwen
    monkeypatch.setattr(asr_module.settings, "asr_provider", "qwen")
    p = asr_module.get_asr()
    assert isinstance(p, asr_module.QwenASRProvider)

    # third_party（配了 url 才可用）
    monkeypatch.setattr(asr_module.settings, "asr_provider", "third_party")
    monkeypatch.setattr(asr_module.settings, "asr_third_party_url", "http://tp.example.com")
    p2 = asr_module.get_asr()
    assert isinstance(p2, asr_module.ThirdPartyASRProvider)
    assert p2.base_url == "http://tp.example.com"


# ---------- P6.3 A6 四块完整性度量 ----------

def test_a6_completeness_full_pass():
    """四块齐全且字段完整 → 满分达标。"""
    from app.core.ai.note_gen import completeness

    data = {
        "summary": "客户想要自动回复",
        "points": [{"topic": "自动回复", "detail": "客服响应慢"}],
        "decisions": [{"content": "先做自动回复"}],
        "todos": [{"owner": "张三", "item": "出方案", "pending": True}],
    }
    c = completeness(data)
    assert c["score"] == 100
    assert c["blocks_present"] == 4
    assert c["pass"] is True


def test_a6_completeness_missing_todos_leaves_empty():
    """todos 缺失 → 留空不强行生成，如实计分（缺失块=0分，不达标但也不伪造）。"""
    from app.core.ai.note_gen import completeness

    data = {
        "summary": "客户想要自动回复",
        "points": [{"topic": "自动回复", "detail": "客服响应慢"}],
        "decisions": [{"content": "先做自动回复"}],
        # todos 缺失（LLM 没提炼出待办）
    }
    c = completeness(data)
    assert c["score"] == 95  # summary40 + points30 + decisions25 = 95
    assert c["blocks_present"] == 3
    assert c["blocks"]["todos"] is False


def test_a6_completeness_empty_all():
    """全空 → 0 分不达标（降级结构如实反映）。"""
    from app.core.ai.note_gen import completeness

    c = completeness({"summary": "", "points": [], "decisions": [], "todos": []})
    assert c["score"] == 0
    assert c["pass"] is False


# ---------- P6.4 Recording 挂 customer（upload 接口）----------

def test_upload_recording_with_customer(client, make_org_user, monkeypatch):
    """upload 传 customer_id → Recording 落 customer_id。"""
    # 不启动真实后台流水线（假音频会触发真 ffmpeg/ASR），仅验证落库
    from app.routers import recordings as rec_router
    monkeypatch.setattr(rec_router.tasks, "start_pipeline", lambda rid: None)

    u = make_org_user(role="developer")
    tok = u["token"]

    # 建客户（属于该用户组）
    cust = client.post("/customers/", json={"name": "语音客户", "industry": "制造"},
                       headers={"token": tok})
    assert cust.status_code == 201, cust.text
    cid = cust.json()["id"]

    # 上传录音（假音频字节，pipeline 会因 ffmpeg/ASR mock 缺失转失败，但 Recording 已落库）
    r = client.post(
        "/recordings/upload",
        headers={"token": tok},
        files={"audio": ("rec.webm", b"fakemedia", "video/webm")},
        data={"customer_id": str(cid), "scene": "req_discussion"},
    )
    assert r.status_code == 200, r.text
    rid = r.json()["id"]

    # 验证 Recording.customer_id 落库
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        rec = db.get(Recording, rid)
        assert rec is not None
        assert rec.customer_id == cid
    finally:
        db.close()


def test_upload_cross_group_customer_forbidden(client, make_org_user, monkeypatch):
    """跨组 customer 上传被拒（组隔离）。"""
    from app.routers import recordings as rec_router
    monkeypatch.setattr(rec_router.tasks, "start_pipeline", lambda rid: None)

    uA = make_org_user(role="developer")
    tokA = uA["token"]
    cid = client.post("/customers/", json={"name": "A组客户"}, headers={"token": tokA}).json()["id"]

    uB = make_org_user(role="developer")
    tokB = uB["token"]
    r = client.post(
        "/recordings/upload",
        headers={"token": tokB},
        files={"audio": ("rec.webm", b"fakemedia", "video/webm")},
        data={"customer_id": str(cid)},
    )
    # 跨组不允许挂该客户（返回错误而非 200 成功）
    assert r.status_code == 200
    assert "forbidden" in r.json().get("error", "").lower() or "forbidden" in r.json().get("error", "")


# ---------- P6.5 录音→Note 挂 customer（customer_id 优先）----------

def test_pipeline_note_uses_recording_customer_id(monkeypatch, db):
    """流水线落 Note 用 Recording.customer_id（优先），不依赖 project 反查。"""
    from app.services import pipeline as pl
    from app.services import asr as asr_module
    from app.services import audio as audio_module
    from app.services import denoise as denoise_module
    from app.services import note_gen as note_gen_module
    from app.models import Customer, Group, Note, User

    # 建组 + 客户（无 project！录音只挂 customer）
    group = Group(name=f"语音组{uuid.uuid4().hex[:6]}")
    db.add(group)
    db.flush()
    cust = Customer(group_id=group.id, name="语音客户", created_by=1)
    db.add(cust)
    db.commit()

    # mock 音频/ASR/去噪/笔记
    monkeypatch.setattr(audio_module, "prepare_audio", lambda path: b"wav")

    class FakeASR:
        def transcribe(self, audio_bytes, language=None):
            return "客户说想要自动回复"

    class FakeDenoise:
        def chat(self, messages):
            return json.dumps([{"sentence": "客户说想要自动回复", "keep": True, "reason": "保留"}])

    class FakeNote:
        def chat(self, messages):
            return json.dumps({
                "summary": "客户要自动回复",
                "points": [{"topic": "自动回复", "detail": "客服响应慢"}],
                "decisions": [{"content": "先做自动回复"}],
                "todos": [{"owner": "李四", "item": "提方案", "pending": True}],
            })

    monkeypatch.setattr(asr_module, "get_asr", lambda: FakeASR())
    monkeypatch.setattr(denoise_module, "get_denoise_llm", lambda: FakeDenoise())
    monkeypatch.setattr(note_gen_module, "get_llm", lambda: FakeNote())

    # 录音只挂 customer_id，无 project_id
    user = db.query(User).first()
    rec = Recording(customer_id=cust.id, scene="req_discussion",
                    audio_path="_tmp_p6.webm", author_id=user.id)
    db.add(rec)
    db.commit()

    pl.process_recording(db, rec.id)

    note = db.query(Note).filter(Note.customer_id == cust.id).first()
    assert note is not None, "Note 应落库并挂 customer"
    assert note.customer_id == cust.id
    assert note.group_id == group.id
    assert note.ai_structured["summary"] == "客户要自动回复"
    assert rec.status == "done"
