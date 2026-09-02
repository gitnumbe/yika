"""P1.3 子系统注册清单（S1）—— 平台外壳按此+角色展示图标墙。

- 增：注册子系统（admin）
- 停：status=stopped（隐藏入口但数据保留）
- 下线：status=archived（标记归档，数据保留）
- 粒度2：不做物理删除（S8 决策）
- 「可访问列表」：按当前用户角色过滤未停/未下线的子系统，供外壳导航
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth import get_current_user, require_role
from ...database import get_session
from ...models import Role, Subsystem, User

router = APIRouter(prefix="/subsystems", tags=["platform-subsys"])


class SubsystemIn(BaseModel):
    key: str
    name: str
    icon: str = ""
    url: str = ""
    roles: list[str] = []


class SubsystemOut(BaseModel):
    id: int
    key: str
    name: str
    icon: str
    url: str
    roles: list
    status: str
    model_config = {"from_attributes": True}


def _out(s: Subsystem) -> SubsystemOut:
    return SubsystemOut(id=s.id, key=s.key, name=s.name, icon=s.icon, url=s.url,
                        roles=s.roles or [], status=s.status)


# ---------- admin 管理 ----------
@router.post("", response_model=SubsystemOut, status_code=201)
def create_subsystem(body: SubsystemIn, db: Session = Depends(get_session),
                     user: User = Depends(require_role("admin"))):
    if db.query(Subsystem).filter(Subsystem.key == body.key).first():
        raise HTTPException(400, "子系统标识已存在")
    s = Subsystem(key=body.key, name=body.name, icon=body.icon, url=body.url,
                  roles=body.roles, status="active")
    db.add(s)
    db.commit()
    db.refresh(s)
    return _out(s)


@router.get("", response_model=list[SubsystemOut])
def list_subsystems(db: Session = Depends(get_session), user: User = Depends(require_role("admin"))):
    return [_out(s) for s in db.query(Subsystem).all()]


@router.post("/{key}/stop", response_model=SubsystemOut)
def stop_subsystem(key: str, db: Session = Depends(get_session), user: User = Depends(require_role("admin"))):
    """停：关入口，数据保留。"""
    s = _get_or_404(db, key)
    s.status = "stopped"
    db.commit()
    db.refresh(s)
    return _out(s)


@router.post("/{key}/archive", response_model=SubsystemOut)
def archive_subsystem(key: str, db: Session = Depends(get_session), user: User = Depends(require_role("admin"))):
    """下线：标记归档，数据保留。"""
    s = _get_or_404(db, key)
    s.status = "archived"
    db.commit()
    db.refresh(s)
    return _out(s)


@router.post("/{key}/activate", response_model=SubsystemOut)
def activate_subsystem(key: str, db: Session = Depends(get_session), user: User = Depends(require_role("admin"))):
    """恢复：archived/stopped → active。"""
    s = _get_or_404(db, key)
    s.status = "active"
    db.commit()
    db.refresh(s)
    return _out(s)


# ---------- 当前用户可访问子系统（外壳导航，按角色过滤） ----------
@router.get("/mine", response_model=list[SubsystemOut])
def my_subsystems(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """返回当前用户角色可访问、且未停/未下线的子系统（S1 角色过滤 + S8 状态）。"""
    query = db.query(Subsystem).filter(Subsystem.status == "active")
    result = []
    for s in query.all():
        roles = s.roles or []
        if not roles or user.role.value in roles:
            result.append(_out(s))
    return result


def _get_or_404(db: Session, key: str) -> Subsystem:
    s = db.query(Subsystem).filter(Subsystem.key == key).first()
    if not s:
        raise HTTPException(404, "子系统不存在")
    return s
