"""P3.5 知识库（全平台共通 + 讲师写入需审核队列）。

权限（v3 §9.2）：
- 写：开发可写(直接 published)；组长可写(直接 published, 可代讲师发)；讲师写 → draft(待审核)；admin 不可写(403)
- 查：全平台共通查 published；组长/开发额外可见待审核 draft(供审核)；作者可看自己 draft
- 审核：组长/开发 将讲师 draft 审为 published（记录 reviewer/reviewed_at）
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_session
from ..models import Knowledge, Role, User
from ..schemas import KnowledgeIn, KnowledgeOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_WRITABLE_ROLES = ("developer", "leader")
_REVIEW_ROLES = ("developer", "leader")
_VISIBLE_ROLES = ("developer", "leader")


def _out(k: Knowledge) -> dict:
    return {
        "id": k.id, "title": k.title, "body": k.body, "tags": k.tags or [],
        "source_enum": k.source_enum, "status": k.status,
        "reviewer_id": k.reviewer_id, "author_id": k.author_id,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


@router.get("/", response_model=list[dict])
def list_knowledge(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    """全平台共通；开发/组长看 published+draft(待审核)，讲师/admin 看 published+自己 draft。"""
    rows = db.query(Knowledge).all()
    out = []
    for k in rows:
        if k.status == "published":
            out.append(_out(k))
        elif user.role.value in _VISIBLE_ROLES:
            out.append(_out(k))            # 开发/组长可看待审核
        elif k.author_id == user.id:
            out.append(_out(k))            # 作者看自己 draft
        # 其它(讲师看他人 draft)不显示
    return out


@router.post("/", response_model=dict)
def create_knowledge(body: KnowledgeIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    if user.role.value == "admin":
        raise HTTPException(403, "全局管理员不直接写知识库")
    # 讲师内容需审核：落 draft；开发/组长直接 published
    status = "draft" if user.role.value == "instructor" else "published"
    data = body.model_dump()
    k = Knowledge(**data, author_id=user.id, status=status)
    db.add(k)
    db.commit()
    db.refresh(k)
    return _out(k)


@router.post("/{kid}/review", response_model=dict)
def review_knowledge(kid: int, db: Session = Depends(get_session), user: User = Depends(require_role("developer", "leader"))):
    """审核：将 draft(通常讲师所写) 审为 published。仅开发/组长。"""
    k = db.get(Knowledge, kid)
    if not k:
        raise HTTPException(404, "知识条目不存在")
    if k.status == "published":
        raise HTTPException(400, "已是发布状态")
    k.status = "published"
    k.reviewer_id = user.id
    k.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(k)
    return _out(k)
