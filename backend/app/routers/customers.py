"""P3.1 客户 CRUD（组私有）+ 客户池导入（组长/管理）。

组隔离：客户=组私有，本组看改；跨组读不到（group_filter）。
导入：仅组长/admin 可将"客户池"(潜在/待跟)客户导入本组（带 source 标记，防幻觉=不自动落库）。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_role
from ..core.permissions import current_group_ids, group_filter
from ..database import get_session
from ..models import Customer, User
from ..schemas import CustomerIn, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])

_READ = ("admin", "developer", "instructor", "leader")


def _scoped(db: Session, user: User) -> Session:
    """组私有访问：返回带组过滤的查询对象（admin 全见）。"""
    return db


def _get_or_404(db: Session, cid: int, user: User) -> Customer:
    c = db.get(Customer, cid)
    if not c:
        raise HTTPException(404, "客户不存在")
    cond = group_filter(Customer.group_id, user)
    if cond is True:  # admin 全见
        return c
    gids = current_group_ids(user)
    if c.group_id not in gids:
        raise HTTPException(404, "客户不存在")
    return c


@router.get("/", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_session), user: User = Depends(require_role(*_READ))):
    q = db.query(Customer)
    cond = group_filter(Customer.group_id, user)
    return q.all() if cond is True else q.filter(cond).all()


@router.post("/", response_model=CustomerOut, status_code=201)
def create_customer(body: CustomerIn, db: Session = Depends(get_session), user: User = Depends(require_role(*_READ))):
    gids = current_group_ids(user)
    if user.role.value != "admin" and not gids:
        raise HTTPException(403, "无所属组，不能创建客户")
    data = body.model_dump()
    if not data.get("group_id"):
        data["group_id"] = gids[0] if gids else None
    data["created_by"] = user.id
    c = Customer(**data)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{cid}", response_model=CustomerOut)
def get_customer(cid: int, db: Session = Depends(get_session), user: User = Depends(require_role(*_READ))):
    c = _get_or_404(db, cid, user)
    return c


@router.put("/{cid}", response_model=CustomerOut)
def update_customer(cid: int, body: CustomerIn, db: Session = Depends(get_session), user: User = Depends(require_role(*_READ))):
    c = _get_or_404(db, cid, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k != "group_id":  # 归属组不可随意改（防越权）
            setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{cid}", status_code=204)
def delete_customer(cid: int, db: Session = Depends(get_session), user: User = Depends(require_role(*_READ))):
    c = _get_or_404(db, cid, user)
    db.delete(c)  # 首期软删欠佳，直接删（P3 主数据，后续可换下线标记）
    db.commit()
    return None


# ---------- 客户池导入（组长/管理） ----------
class CustomerImportIn(BaseModel):
    customers: list[CustomerIn]
    group_id: int | None = None  # 默认导入到当前用户组


@router.post("/import", response_model=list[CustomerOut])
def import_customers(body: CustomerImportIn, db: Session = Depends(get_session),
                     user: User = Depends(require_role("admin", "leader"))):
    """客户池→本组导入（组长/admin）。手动明确导入才落库，AI 只产候选。"""
    gids = current_group_ids(user)
    target_gid = body.group_id or (gids[0] if gids else None)
    if user.role.value != "admin" and not target_gid:
        raise HTTPException(403, "无所属组，不能导入客户")
    out = []
    for cin in body.customers:
        data = cin.model_dump()
        data["group_id"] = target_gid
        data["source"] = "pool"  # 标记为池导入
        data["created_by"] = user.id
        c = Customer(**data)
        db.add(c)
        out.append(c)
    db.commit()
    for c in out:
        db.refresh(c)
    return out
