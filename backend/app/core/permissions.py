"""P1.4a 权限层 —— group_id 数据归属过滤（防水平越权）。

组隔离规则（v3.0 §9.3）：客户/项目/需求 = 组私有（本组看改）；
知识 = 全平台共通（不过滤）。admin 可跨组（平台管理）。

核心：
- current_group_ids(user) → 用户所属组 id 列表（group_ids JSON）
- group_filter(model, user) → SQLAlchemy 过滤条件（业务表按 group_id 所属组过滤）
- 知识类（无 group_id）不套此过滤
"""
from ..models import User


def current_group_ids(user: User) -> list[int]:
    """返回当前用户所属业务组 id 列表（group_ids 预留 1:N）。"""
    return list(user.group_ids or [])


def in_same_group(user: User, target_group_id: int) -> bool:
    """判断用户是否属于某组（用于组私有数据校验）。"""
    return target_group_id in current_group_ids(user)


def group_filter(column, user: User):
    """生成 group_id 过滤条件。admin 返回恒真（跨组管理）；否则按用户组。"""
    gids = current_group_ids(user)
    if user.role.value == "admin":
        return True  # admin 可跨组
    if not gids:
        return False  # 无组则看不到任何组私有数据
    return column.in_(gids)
