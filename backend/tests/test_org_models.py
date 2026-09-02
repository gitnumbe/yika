"""P0.2a 组织模型 L1 单测：Group / User(Role/1:N group_ids) / RefreshToken。

覆盖：
- v3.0 角色枚举 admin/leader/instructor/developer（v2 tech 已改为 developer）
- 业务组 Group 建组、组长关联
- User group_ids 预留 1:N（可存多个组）
- 登录安全字段（failed_attempts/locked_until）保留
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Group, Role, User, RefreshToken

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
    """v3.0 角色：admin/leader/instructor/developer（无 tech）。"""
    assert {r.value for r in Role} == {"admin", "leader", "instructor", "developer"}


def test_group_creation(db):
    g = Group(name="A组")
    db.add(g)
    db.commit()
    assert g.id is not None
    assert g.name == "A组"


def test_user_group_1n_reserved(db):
    """User.group_ids 预留 1:N：首期 1 个组，但结构可存多组。"""
    g1, g2 = Group(name="A组"), Group(name="B组")
    db.add_all([g1, g2])
    db.commit()
    # 首期一人一组（1 个 id），但结构预留 list
    u = User(username="leader1", password_hash="x", role=Role.leader, group_ids=[g1.id])
    db.add(u)
    db.commit()
    assert u.group_ids == [g1.id]
    # 预留：结构可容纳多组（跨组支援场景）
    u.group_ids = [g1.id, g2.id]
    db.commit()
    assert u.group_ids == [g1.id, g2.id]


def test_user_login_security_fields(db):
    """登录安全字段保留（生产级）。"""
    u = User(username="u", password_hash="h", role=Role.instructor)
    db.add(u)
    db.commit()
    assert u.failed_attempts == 0
    assert u.locked_until is None
    assert u.last_login_at is None


def test_refresh_token_crud(db):
    """RefreshToken 双令牌持久化。"""
    u = User(username="t", password_hash="h", role=Role.developer)
    db.add(u)
    db.commit()
    rt = RefreshToken(user_id=u.id, token_hash="hashed", expires_at=__import__("datetime").datetime.utcnow())
    db.add(rt)
    db.commit()
    assert rt.id is not None
    assert rt.revoked_at is None


def test_user_has_display_name_and_active(db):
    u = User(username="d", password_hash="h", role=Role.developer, display_name="技术小王")
    db.add(u)
    db.commit()
    assert u.display_name == "技术小王"
    assert u.active is True
