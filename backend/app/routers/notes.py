"""P3.4/语音链路 · 沟通记录(Note) + 需求候选提炼 + 人工确认转正式需求。

- Note 挂 customer 下(customer_id/group_id)，scenario 分场景，ai_structured 存 A6 结构化。
- /{id}/extract：从转录提炼需求候选，**只返回不落库**（防幻觉铁律）。
- /{id}/confirm-requirements：人工确认候选 → 转正式需求（挂 project、溯源 source_note_id=note.id）。
- 组隔离：本组看改笔记；admin 跨组。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..core.permissions import current_group_ids, group_filter
from ..database import get_session
from ..models import Note, Project, ReqSource, Requirement, User
from ..schemas import ConfirmRequirements
from ..services import req_extract

router = APIRouter(prefix="/notes", tags=["notes"])


def _note_dict(n: Note) -> dict:
    """Note → dict（ai_structured 已是 JSON 字段，直接取）。"""
    ai = n.ai_structured or {}
    return {
        "id": n.id,
        "customer_id": n.customer_id,
        "group_id": n.group_id,
        "scenario": n.scenario,
        "transcript": n.transcript,
        "audio_path": n.audio_path,
        "ai_structured": ai,
        "quality_flags": n.quality_flags or {},
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _check_note_access(n: Note, user: User) -> None:
    """笔记组归属：本组或 admin 可见；否则 404（防越权探测）。"""
    cond = group_filter(Note.group_id, user)
    if cond is not True and current_group_ids(user) and n.group_id not in current_group_ids(user):
        raise HTTPException(404, "笔记不存在")


@router.get("/")
def list_notes(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    q = db.query(Note)
    cond = group_filter(Note.group_id, user)
    return [_note_dict(n) for n in (q.all() if cond is True else q.filter(cond).all())]


@router.post("/{note_id}/extract")
def extract(note_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    _check_note_access(note, user)
    text = note.transcript or ""
    # 只返回候选 + quality，不落库（防幻觉铁律）
    return req_extract.extract_candidates(text)


@router.post("/{note_id}/confirm-requirements")
def confirm(note_id: int, body: ConfirmRequirements, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    _check_note_access(note, user)
    # v3：需求挂 project 下，从 project 解析 group 归属；溯源到本 Note。
    project = db.get(Project, body.project_id) if body.project_id else None
    if not project:
        raise HTTPException(400, "确认需求须指定存在的项目")
    # 项目须在本组（防跨组借项目落需求）
    cond = group_filter(Project.group_id, user)
    if cond is not True and current_group_ids(user) and project.group_id not in current_group_ids(user):
        raise HTTPException(404, "项目不存在")
    created = []
    for c in body.candidates:
        r = Requirement(
            title=c.title,
            description=c.description,
            source=ReqSource.manual,        # 人工确认（候选原本 AI 提炼，此处人工拍板转正式）
            source_note_id=note.id,          # P3.4 溯源到本沟通记录
            project_id=project.id,
            group_id=project.group_id,
            created_by=user.id,
            ai_confidence=c.confidence if hasattr(c, "confidence") else None,
        )
        db.add(r)
        created.append(r)
    db.commit()
    return [{"id": r.id, "title": r.title, "status": r.status.value, "group_id": r.group_id} for r in created]
