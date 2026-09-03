"""P3.3 需求 CRUD + 状态机（v3）。

- 状态机：draft→pending_review→feasible/info_needed/plan_needed/infeasible→in_dev→delivered
  （见 state_machine.allowed_transitions）
- 评审权限：pending_review 后 → 组长专属拍板（feasible/info_needed/plan_needed/infeasible）
  讲师/开发可给意见但不可最终定；组长发起评审
- 组隔离：需求继承项目所属组，跨组读不到
- 溯源字段：source_note_id（P3.4 候选需求/沟通记录确认后带过来），非 v2 的 source_ref 字符串
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import state_machine
from ..auth import require_role
from ..core.permissions import current_group_ids, group_filter
from ..database import get_session
from ..models import Project, ReqPriority, ReqSource, ReqStatus, Requirement, User
from ..schemas import RequirementCreate, RequirementOut, TransitionIn

router = APIRouter(prefix="/requirements", tags=["requirements"])
ROLE_ALL = require_role("admin", "developer", "instructor", "leader")


@router.post("/", response_model=RequirementOut)
def create_requirement(body: RequirementCreate, db: Session = Depends(get_session),
                       user: User = Depends(ROLE_ALL)):
    # 需求须挂在项目下（继承项目组）
    if not body.project_id:
        raise HTTPException(400, "需求须挂在一个项目下")
    proj = db.get(Project, body.project_id)
    if not proj:
        raise HTTPException(404, "项目不存在")
    cond = group_filter(Project.group_id, user)
    if cond is not True and proj.group_id not in current_group_ids(user):
        raise HTTPException(403, "不能在跨组项目下建需求")
    r = Requirement(
        title=body.title, description=body.description,
        project_id=proj.id, group_id=proj.group_id,
        source=ReqSource(body.source), priority=ReqPriority(body.priority),
        created_by=user.id,
        source_note_id=body.source_note_id, ai_confidence=body.ai_confidence,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _out(r)


@router.get("/", response_model=list[RequirementOut])
def list_requirements(db: Session = Depends(get_session), user: User = Depends(ROLE_ALL)):
    q = db.query(Requirement)
    cond = group_filter(Requirement.group_id, user)
    rows = q.all() if cond is True else q.filter(cond).all()
    return [_out(r) for r in rows]


@router.get("/{req_id}", response_model=RequirementOut)
def get_requirement(req_id: int, db: Session = Depends(get_session), user: User = Depends(ROLE_ALL)):
    return _out(_get_or_404(db, req_id, user))


@router.post("/{req_id}/submit", response_model=RequirementOut)
def submit_for_review(req_id: int, db: Session = Depends(get_session), user: User = Depends(ROLE_ALL)):
    """草稿 → 待评审（作者提交）。"""
    r = _get_or_404(db, req_id, user)
    _do_transition(db, r, ReqStatus.pending_review)
    return _out(r)


@router.post("/{req_id}/transition", response_model=RequirementOut)
def transition_requirement(req_id: int, body: TransitionIn, db: Session = Depends(get_session),
                           user: User = Depends(require_role("admin", "leader", "developer", "instructor"))):
    """状态流转。
    - 评审拍板(待评审→可行/需调整/不可行) = 组长专属（admin 不评审业务，讲师/开发不可）
    - 开发/交付(→开发中/已交付) = 开发/组长/admin 可做（矩阵第58行）
    - 讲师提交后的重提(→待评审) 允许作者；此处 transition 由查到需提交走 submit。
    """
    r = _get_or_404(db, req_id, user)
    to = ReqStatus(body.to)
    # 评审拍板：仅组长（admin 不评审业务）
    if to in (ReqStatus.feasible, ReqStatus.infeasible, ReqStatus.info_needed, ReqStatus.plan_needed):
        if user.role.value != "leader":
            raise HTTPException(403, "仅组长可评审需求")
    # 开发/交付跳转：开发可做；讲师不可做开发类
    elif to in (ReqStatus.in_dev, ReqStatus.delivered):
        if user.role.value == "instructor":
            raise HTTPException(403, "讲师不能推进开发/交付")
    _do_transition(db, r, to, body.reason, user)
    return _out(r)


def _do_transition(db, r, to, reason="", user=None):
    try:
        state_machine.transition(r, to, reason)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # 评审落痕
    if to == ReqStatus.infeasible:
        r.infeasible_reason = reason
    if to in (ReqStatus.feasible, ReqStatus.infeasible, ReqStatus.info_needed, ReqStatus.plan_needed):
        r.reviewer_id = user.id
        r.review_conclusion = reason
    db.commit()
    db.refresh(r)


def _get_or_404(db: Session, rid: int, user: User) -> Requirement:
    r = db.get(Requirement, rid)
    if not r:
        raise HTTPException(404, "需求不存在")
    cond = group_filter(Requirement.group_id, user)
    if cond is True or r.group_id in current_group_ids(user):
        return r
    raise HTTPException(404, "需求不存在")


def _out(r: Requirement):
    return RequirementOut(
        id=r.id, title=r.title, description=r.description,
        status=r.status.value, project_id=r.project_id, group_id=r.group_id,
        source=r.source.value, source_note_id=r.source_note_id,
        priority=r.priority.value, infeasible_reason=r.infeasible_reason,
        review_conclusion=r.review_conclusion, ai_confidence=r.ai_confidence,
    )
