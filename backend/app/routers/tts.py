"""TTS 朗读端点（决策 09 · 开发文档 §5.6/§8.7）。

懒合成 + 缓存复用：
- 首次朗读 → 调本地 dots.tts 合成 → 存 wav → 记录 audio_tts_path
- 再次朗读 → 直接返回已缓存 wav（校验文件存在）
- TTS 服务不可用 → 503（前端降级为纯文字展示，不阻塞主流程）
"""
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth import require_role
from ..config import settings
from ..database import get_session
from ..models import Note, QA, User
from ..services import tts

router = APIRouter(tags=["tts"])

# 存储根目录（生产挂卷）
STORAGE_ROOT = getattr(settings, "storage_root", "storage")


def _tts_storage_dir() -> str:
    d = os.path.join(STORAGE_ROOT, "tts")
    os.makedirs(d, exist_ok=True)
    return d


def _read_note_text(n: Note) -> str:
    """从笔记拼朗读文本（v3）：摘要 + 要点，读 A6 结构化 ai_structured 四块。"""
    ai = n.ai_structured or {}
    parts = []
    if ai.get("summary"):
        parts.append(str(ai["summary"]))
    for key in ("points", "decisions", "todos"):
        items = ai.get(key) or []
        if isinstance(items, dict):
            items = [items]
        if isinstance(items, str):
            items = [items]
        for it in items:
            if isinstance(it, dict):
                parts.append(str(it.get("detail") or it.get("item") or it.get("content") or ""))
            else:
                parts.append(str(it))
    return "。".join(p for p in parts if p)


def _synthesize(note: Note, text: str) -> str:
    """调 dots.tts 合成，返回 wav 路径；失败抛 HTTPException。"""
    try:
        audio = tts.get_tts().speak(text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"TTS 服务不可用：{type(e).__name__}")
    fname = f"note_{note.id}.wav"
    path = os.path.join(_tts_storage_dir(), fname)
    with open(path, "wb") as f:
        f.write(audio)
    return fname


@router.post("/notes/{note_id}/tts")
def note_tts(note_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    """朗读笔记：懒合成 + 缓存（v3 Note 无 audio_tts_path 列，缓存靠确定性文件名 note_{id}.wav 是否存在判定）。返回 {audio_url, cached, source}。"""
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    text = _read_note_text(note) or note.transcript or ""
    if not text.strip():
        raise HTTPException(400, "笔记无可朗读内容")

    fname = f"note_{note.id}.wav"
    cached = os.path.join(STORAGE_ROOT, "tts", fname)
    if os.path.exists(cached):
        return {"audio_url": f"/tts/wav/{fname}", "cached": True, "source": "note"}

    _synthesize(note, text)
    return {"audio_url": f"/tts/wav/{fname}", "cached": False, "source": "note"}


@router.post("/qa/{qa_id}/tts")
def qa_tts(qa_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    """朗读答疑回答：懒合成 + 缓存。"""
    qa = db.get(QA, qa_id)
    if not qa:
        raise HTTPException(404, "答疑不存在")
    qa_text = (qa.answer or "").strip()
    if not qa_text:
        raise HTTPException(400, "该答疑尚无回答")

    cache_path = getattr(qa, "tts_audio_path", "") or ""
    if cache_path:
        cached = os.path.join(STORAGE_ROOT, cache_path)
        if os.path.exists(cached):
            return {"audio_url": f"/tts/wav/{cache_path}", "cached": True, "source": "qa"}

    try:
        audio = tts.get_tts().speak(qa_text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"TTS 服务不可用：{type(e).__name__}")
    fname = f"qa_{qa_id}.wav"
    os.makedirs(os.path.join(STORAGE_ROOT, "tts"), exist_ok=True)
    with open(os.path.join(STORAGE_ROOT, "tts", fname), "wb") as f:
        f.write(audio)
    if hasattr(qa, "tts_audio_path"):
        qa.tts_audio_path = f"tts/{fname}"
        db.commit()
    return {"audio_url": f"/tts/wav/{fname}", "cached": False, "source": "qa"}


@router.get("/tts/wav/{name}")
def serve_wav(name: str, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    """取已合成的 wav 文件（MIME audio/wav，可 <audio> 播放）。"""
    # 防路径穿越：仅允许合法文件名
    if not re.match(r"^(note|qa)_\d+\.wav$", name):
        raise HTTPException(400, "非法文件名")
    path = os.path.join(STORAGE_ROOT, "tts", name)
    if not os.path.exists(path):
        raise HTTPException(404, "音频不存在")
    return FileResponse(path, media_type="audio/wav")
