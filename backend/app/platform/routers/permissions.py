"""P1.4b 权限层 · 界面级权限查询接口。

S4 三层：①外壳导航（角色过滤图标，见 subsystems/mine）②API 级（require_role+组隔离）
③界面呈现。本 router = 第③层：给前端一个「当前用户能不能做某操作」的查询，
前端据此纯渲染（不硬编码权限逻辑）。

返回权限点：
- can_review           需求评审（组长专属）
- can_deliver          交付（开发/组长）
- can_manage_org       组织管理（admin）
- can_manage_subsystem 子系统管理（admin）
- can_write_knowledge  知识写入（admin/developer/leader）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...auth import get_current_user
from ...database import get_session
from ...models import User

router = APIRouter(prefix="/permissions", tags=["platform-perm"])


@router.get("/mine")
def my_permissions(db: Session = Depends(get_session), user: User = Depends(get_current_user)):
    role = user.role.value
    return {
        "role": role,
        "can_review": role == "leader",                          # 组长拍板
        "can_deliver": role in ("developer", "leader"),          # 开发/组长交付
        "can_manage_org": role == "admin",                       # 组织管理
        "can_manage_subsystem": role == "admin",                 # 子系统管理
        "can_write_knowledge": role in ("developer", "leader"),  # 知识写入(开发直接发/讲师需审); admin 不写
    }
