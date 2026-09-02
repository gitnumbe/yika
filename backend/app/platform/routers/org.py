"""P1.2 组织模型 API —— Group/User 管理、组长指派（全局管理员专属）。

权限：仅 `admin` 可建组/派组长/管理用户（v3.0 §9.2 权限矩阵）。
组长/讲师/开发 访问组织管理 → 403。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth import get_current_user, hash_password, require_role
from ...database import get_session
from ...models import Group, Role, User

router = APIRouter(prefix="/org", tags=["platform-org"])


# ---------- schema ----------
class GroupIn(BaseModel):
    name: str


class GroupOut(BaseModel):
    id: int
    name: str
    leader_user_id: int | None
    model_config = {"from_attributes": True}


class AssignLeaderIn(BaseModel):
    leader_user_id: int


class UserIn(BaseModel):
    username: str
    password: str
    role: str
    display_name: str = ""
    group_ids: list[int] = []


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    active: bool
    group_ids: list
    model_config = {"from_attributes": True}


def _to_group_out(g: Group) -> GroupOut:
    return GroupOut(id=g.id, name=g.name, leader_user_id=g.leader_user_id)


# ---------- 业务组 ----------
@router.post("/groups", response_model=GroupOut, status_code=201)
def create_group(body: GroupIn, db: Session = Depends(get_session),
                 user: User = Depends(require_role("admin"))):
    if db.query(Group).filter(Group.name == body.name).first():
        raise HTTPException(400, "组名已存在")
    g = Group(name=body.name)
    db.add(g)
    db.commit()
    db.refresh(g)
    return _to_group_out(g)


@router.get("/groups", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_session), user: User = Depends(require_role("admin"))):
    return [_to_group_out(g) for g in db.query(Group).all()]


@router.post("/groups/{group_id}/leader", response_model=GroupOut)
def assign_leader(group_id: int, body: AssignLeaderIn, db: Session = Depends(get_session),
                  user: User = Depends(require_role("admin"))):
    g = db.get(Group, group_id)
    if not g:
        raise HTTPException(404, "组不存在")
    leader = db.get(User, body.leader_user_id)
    if not leader:
        raise HTTPException(404, "组长用户不存在")
    if leader.role != Role.leader:
        raise HTTPException(400, "被指派者必须为组长角色")
    g.leader_user_id = leader.id
    db.commit()
    db.refresh(g)
    return _to_group_out(g)


# ---------- 用户管理 ----------
@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserIn, db: Session = Depends(get_session),
                user: User = Depends(require_role("admin"))):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    if body.role not in [r.value for r in Role]:
        raise HTTPException(400, "非法角色")
    u = User(username=body.username,
             password_hash=hash_password(body.password),
             role=body.role, display_name=body.display_name, group_ids=body.group_ids)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_session), user: User = Depends(require_role("admin"))):
    return db.query(User).all()
