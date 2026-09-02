from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_role
from ..core.permissions import current_group_ids, group_filter
from ..database import get_session
from ..models import Customer, User
from ..schemas import CustomerIn, CustomerOut
from ..config import settings

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    # 组隔离：按当前用户组过滤（admin 跨组全见）
    q = db.query(Customer)
    cond = group_filter(Customer.group_id, user)
    if cond is True:
        return q.all()
    return q.filter(cond).all()


@router.post("/", response_model=CustomerOut)
def create_customer(body: CustomerIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "developer", "instructor", "leader"))):
    gids = current_group_ids(user)
    if user.role.value != "admin" and not gids:
        raise HTTPException(403, "无所属组，不能创建客户")
    # 客户归属：优先取用户的第一个组；admin 可指定
    data = body.model_dump()
    if "group_id" not in data or data.get("group_id") is None:
        data["group_id"] = gids[0] if gids else None
    data["created_by"] = user.id
    c = Customer(**data)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

