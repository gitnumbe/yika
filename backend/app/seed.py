"""P0.3 种子/初始化 —— 启动时幂等创建全局管理员 + 示例业务组。

规则：
- 幂等：已有则跳过，不会重复创建/覆盖。
- 配置走 .env：管理员用户名/密码、示例组名用环境变量（见 config.py），不硬编码。
- 角色枚举 = v3.0：admin / leader / instructor / developer。
- 全局管理员不属于任何业务组（group_ids 为空）。
"""
from sqlalchemy.orm import Session

from .config import settings
from .auth import hash_password
from .models import Group, Role, User

# 示例业务组配置（组名可被 .env 覆盖，未配置则用默认）
DEFAULT_GROUP_NAME = "技术组"


def _get_or_create_user(db: Session, username: str, role: Role, display_name: str,
                        password: str, group_ids: list[int] | None = None) -> User:
    """按 username 幂等获取或创建用户。"""
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        display_name=display_name,
        group_ids=group_ids or [],
        active=True,
    )
    db.add(user)
    db.flush()  # 拿到 id
    return user


def seed(db: Session) -> dict:
    """初始化默认数据。返回本次创建/复用的账户摘要（供启动日志/测试断言）。"""
    created = []

    # 1. 全局管理员（不属于任何业务组）
    admin_username = getattr(settings, "seed_admin_username", None) or "admin"
    admin_password = getattr(settings, "seed_admin_password", None) or "admin123"
    admin = _get_or_create_user(
        db, admin_username, Role.admin, "全局管理员", admin_password, group_ids=[]
    )
    created.append({"username": admin.username, "role": Role.admin.value})

    # 2. 示例业务组 + 组长 + 讲师 + 开发
    group_name = getattr(settings, "seed_group_name", None) or DEFAULT_GROUP_NAME
    group = db.query(Group).filter(Group.name == group_name).first()
    if not group:
        group = Group(name=group_name)
        db.add(group)
        db.flush()

    leader = _get_or_create_user(db, "leader1", Role.leader, "组长小L", "leader123", [group.id])
    instructor = _get_or_create_user(db, "instructor1", Role.instructor, "讲师小A",
                                     "instructor123", [group.id])
    developer = _get_or_create_user(db, "developer1", Role.developer, "开发小B",
                                    "developer123", [group.id])

    # 组长同时是组的 leader_user_id（组长可兼任，见组织模型）
    if not group.leader_user_id:
        group.leader_user_id = leader.id

    created.append({"username": leader.username, "role": Role.leader.value, "group": group.name})
    created.append({"username": instructor.username, "role": Role.instructor.value, "group": group.name})
    created.append({"username": developer.username, "role": Role.developer.value, "group": group.name})

    db.commit()
    return {"group": group.name, "users": created}


def seed_if_empty(db: Session) -> dict | None:
    """仅当库为空（无 admin）时执行 seed，供 main 启动/测试用。返回 seed 结果或 None。"""
    if db.query(User).filter(User.role == Role.admin).first():
        return None
    return seed(db)
