"""L2 TTS 朗读端点测试（mock dots-tts 服务，不实调模型）。

验证：笔记朗读懒合成 + 缓存复用 + 权限 + wav 取用（v3 语义）。
组内用户通过 admin 走 /org/groups + /org/users 创建（v3 无 register 自建场景）。

"""
import json

import pytest

pytestmark = pytest.mark.l2

ADMIN = {"username": "admin", "password": "admin123"}


def _admin_token(client):
    r = client.post("/auth/login", json=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _make_group_user(client, username, role="instructor", password="pw"):
    """admin 建组 + 组内用户，返回该用户登录 token 及归属。"""
    ah = {"token": _admin_token(client)}
    group = client.post("/org/groups", json={"name": f"组_{username}"}, headers=ah)
    assert group.status_code == 201, group.text
    gid = group.json()["id"]
    u = client.post(
        "/org/users",
        json={"username": username, "password": password, "role": role,
              "display_name": username, "group_ids": [gid]},
        headers=ah,
    )
    assert u.status_code == 201, u.text
    uid = u.json()["id"]
    tok = client.post("/auth/login", json={"username": username, "password": password}).json()["token"]
    return {"user_id": uid, "group_id": gid, "token": tok}


def _create_customer_and_note(db, group_id, user_id, transcript="客户想要自动回复功能"):
    from app.models import Customer, Note

    customer = Customer(group_id=group_id, name="演示客户", created_by=user_id)
    db.add(customer)
    db.flush()
    note = Note(
        customer_id=customer.id,
        group_id=group_id,
        scenario="req_discussion",
        transcript=transcript,
        ai_structured={
            "summary": "客户要自动回复",
            "points": [{"topic": "自动回复", "detail": "自动回消息"}],
            "decisions": [],
            "todos": [{"owner": "技术", "item": "评估可行性", "pending": True}],
        },
        quality_flags={},
        note_author_id=user_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note.id


def test_note_tts_synthesize_then_cached(client, monkeypatch, tmp_path, db):
    """首次朗读合成 wav 并缓存；再次朗读命中缓存（不再调服务）。"""
    from app.services import tts as tts_module

    calls = {"n": 0}

    class FakeTTS:
        def speak(self, text, voice_ref="default"):
            calls["n"] += 1
            return b"RIFF....wavedata"

    monkeypatch.setattr(tts_module, "get_tts", lambda: FakeTTS())
    # 隔离到 tmp 存储
    monkeypatch.setattr("app.routers.tts.STORAGE_ROOT", str(tmp_path))

    who = _make_group_user(client, "朗读用户")
    th = {"token": who["token"]}
    note_id = _create_customer_and_note(db, who["group_id"], who["user_id"])

    # 首次朗读 → 合成
    r = client.post(f"/notes/{note_id}/tts", headers=th)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cached"] is False
    assert calls["n"] == 1
    assert data["audio_url"].endswith(".wav")

    # 再次朗读 → 缓存命中
    r2 = client.post(f"/notes/{note_id}/tts", headers=th)
    assert r2.status_code == 200, r2.text
    assert r2.json()["cached"] is True
    assert calls["n"] == 1  # 未再调服务

    # wav 可取
    wav = client.get(data["audio_url"], headers=th)
    assert wav.status_code == 200
    assert wav.headers["content-type"] == "audio/wav"
    assert wav.content[:4] == b"RIFF"


def test_note_tts_requires_auth(client):
    """未登录访问 → 401（真实 TTS 端点路径 /notes/{id}/tts，POST）。"""
    # 注意：login 会种 cookie，勿先登录；全新 client 无凭证 → 应 401
    r = client.post("/notes/1/tts")
    assert r.status_code == 401


def test_note_tts_404(client, db):
    """登录但笔记不存在 → 404。"""
    who = _make_group_user(client, "无笔记用户")
    th = {"token": who["token"]}
    r = client.post("/notes/99999/tts", headers=th)
    assert r.status_code == 404
