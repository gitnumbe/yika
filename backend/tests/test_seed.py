"""P0.3 种子/初始化 L1 单测。

覆盖：
- 角色枚举（v3.0：admin/leader/instructor/developer，无 tech）
- seed() 幂等：重复调用不重复创建
- 全局管理员不属于业务组；组长/讲师/开发挂到示例组
- 组 leader_user_id 指向组长
- 密码 bcrypt 可验证（登录可用）
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Group, Role, User
from app.seed import seed, seed_if_empty
from app.auth import verify_password

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    Base.metadata.drop_all(bind=engine)


def test_role_enum_v3():
    """验证 v3.0 四角色枚举（无 tech）。"""
    values = [r.value for r in Role]
    assert "admin" in values
    assert "leader" in values
    assert "instructor" in values
    assert "developer" in values
    assert "tech" not in values


def test_seed_creates_admin_and_group(db):
    """seed 创建全局管理员 + 示例业务组 + 组长/讲师/开发。"""
    result = seed(db)
    assert result["group"] == "技术组"
    usernames = [u["username"] for u in result["users"]]
    assert "admin" in usernames
    assert "leader1" in usernames
    assert "instructor1" in usernames
    assert "developer1" in usernames

    # 校验库内
    admin = db.query(User).filter(User.username == "admin").one()
    assert admin.role == Role.admin
    assert admin.group_ids == []  # 全局管理员不属于业务组

    leader = db.query(User).filter(User.username == "leader1").one()
    assert leader.role == Role.leader

    group = db.query(Group).filter(Group.name == "技术组").one()
    assert group.leader_user_id == leader.id  # 组长兼任组 leader_user_id


def test_seed_idempotent(db):
    """seed 幂等：重复调用不重复创建账户/组。"""
    r1 = seed(db)
    r2 = seed(db)
    assert db.query(User).filter(User.username == "admin").count() == 1
    assert db.query(Group).filter(Group.name == "技术组").count() == 1
    assert len(r2["users"]) == 4  # 仍返回固定账户，但未重复建


def test_seed_password_verifies(db):
    """种子用户密码可验证（能登录）。"""
    seed(db)
    user = db.query(User).filter(User.username == "developer1").one()
    assert verify_password("developer123", user.password_hash) is True


def test_seed_if_empty_skips_when_admin_exists(db):
    """seed_if_empty：已有 admin 时不重复 seed。"""
    seed(db)
    assert seed_if_empty(db) is None  # 已有 admin，跳过
