"""P1.5 共享主数据 API（S3）—— 平台统一读写入口，子系统经此访问共享主数据，不直连库。

S3 规则：平台=共享主数据（客户/知识/组织）的统一 API 层 + 组隔离强制；子系统私有数据自治。
本模块提供：
- GET  /api/shared/customers            本组可见客户（组隔离）
- GET  /api/shared/knowledge            全平台知识（共通）
- GET  /api/shared/me                   当前用户身份（角色/组）
均走平台的 require_role + group_id 过滤，子系统零权限代码。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...auth import get_current_user
from ...core.permissions import group_filter
from ...database import get_session
from ...models import Customer, Knowledge, User

router = APIRouter(prefix="/api/shared", tags=["platform-shared"])


@router.get("/customers")
def shared_customers(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """本组可见客户（组隔离）；admin 跨组全见。供子系统读取。"""
    q = db.query(Customer)
    cond = group_filter(Customer.group_id, user)
    items = q.all() if cond is True else q.filter(cond).all()
    return [{"id": c.id, "name": c.name, "industry": c.industry,
             "scale": c.scale, "group_id": c.group_id} for c in items]


@router.get("/knowledge")
def shared_knowledge(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    """全平台知识（共通，无组隔离）。供子系统读取。"""
    items = db.query(Knowledge).all()
    return [{"id": k.id, "title": k.title, "body": k.body} for k in items]


@router.get("/me")
def shared_me(user: User = Depends(get_current_user)):
    """当前用户身份（角色/组），供子系统识别。"""
    return {"id": user.id, "username": user.username, "role": user.role.value,
            "display_name": user.display_name, "group_ids": user.group_ids or []}
