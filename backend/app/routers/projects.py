"""P3.2 项目 CRUD（挂客户下，组私有 + 客户归属校验）。

- 项目必须在某客户下；客户须在本组（跨组借客户建项目 → 404/403）
- 项目继承其客户所属组（group_id），跨组读不到
- 组隔离：本组看改；admin 跨组
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..core.permissions import current_group_ids, group_filter
from ..database import get_session
from ..models import Customer, Project, User
from ..schemas import ProjectIn, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])
ROLE = require_role("admin", "developer", "instructor", "leader")


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_session), user: User = Depends(ROLE)):
    q = db.query(Project)
    cond = group_filter(Project.group_id, user)
    if cond is True:
        return q.all()
    return q.filter(cond).all()


@router.get("/{pid}", response_model=ProjectOut)
def get_project(pid: int, db: Session = Depends(get_session), user: User = Depends(ROLE)):
    return _get_or_404(db, pid, user)


@router.post("/", response_model=ProjectOut)
def create_project(body: ProjectIn, db: Session = Depends(get_session), user: User = Depends(ROLE)):
    # 客户必须存在且在本组（项目继承客户组）
    cust = db.get(Customer, body.customer_id)
    if not cust:
        raise HTTPException(404, "客户不存在")
    cond = group_filter(Customer.group_id, user)
    gids = current_group_ids(user)
    if cond is not True and cust.group_id not in gids:
        raise HTTPException(403, "不能在跨组客户下建项目")
    p = Project(name=body.name, customer_id=body.customer_id,
                group_id=cust.group_id, description=body.description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{pid}", response_model=ProjectOut)
def update_project(pid: int, body: ProjectIn, db: Session = Depends(get_session), user: User = Depends(ROLE)):
    p = _get_or_404(db, pid, user)
    p.name = body.name
    if body.description is not None:
        p.description = body.description
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{pid}", status_code=204)
def delete_project(pid: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "leader"))):
    """删除项目仅组长/admin（开发保留读取，防止误删）。"""
    p = _get_or_404(db, pid, user)
    db.delete(p)
    db.commit()


def _get_or_404(db: Session, pid: int, user: User) -> Project:
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    cond = group_filter(Project.group_id, user)
    if cond is True:
        return p
    if p.group_id not in current_group_ids(user):
        raise HTTPException(404, "项目不存在")
    return p
