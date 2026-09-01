import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Note, ReqSource, Requirement, User
from ..schemas import ConfirmRequirements
from ..services import req_extract

router = APIRouter(prefix="/notes", tags=["notes"])


def _note_dict(n: Note) -> dict:
    """Note → dict（points/decisions/todos 存储为 JSON 字符串，读出还原数组）。"""
    def _parse(v):
        if not v:
            return []
        if isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return v  # 兼容旧数据（纯文本）
    return {
        "id": n.id,
        "summary": n.summary,
        "points": _parse(n.points),
        "decisions": _parse(n.decisions),
        "todos": _parse(n.todos),
        "scene": n.scene,
        "project_id": n.project_id,
        "transcript": n.transcript,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/")
def list_notes(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return [_note_dict(n) for n in db.query(Note).order_by(Note.created_at.desc()).all()]


@router.post("/{note_id}/extract")
def extract(note_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    # 只返回候选 + quality，不落库（防幻觉铁律）
    return req_extract.extract_candidates(note.transcript or note.points or "")


@router.post("/{note_id}/confirm-requirements")
def confirm(note_id: int, body: ConfirmRequirements, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    created = []
    for c in body.candidates:
        r = Requirement(
            title=c.title,
            description=c.description,
            source=ReqSource.discussion,
            source_ref=c.source_ref,
            project_id=body.project_id,
            customer_id=body.customer_id,
            author_id=user.id,
        )
        db.add(r)
        created.append(r)
    db.commit()
    return [{"id": r.id, "title": r.title} for r in created]
