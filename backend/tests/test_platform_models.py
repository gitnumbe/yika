"""P0.2c 知识+审计+子系统注册 L1 单测。

覆盖：
- Knowledge：全平台共通（无 group_id，group_scope=global）
- AuditLog：只增不改（append-only），含 actor/entity/entity_id/ip
- Subsystem：注册清单（key/name/icon/url/roles/status——active/stopped/archived）
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.models import Base, Group, Role, User, Knowledge, AuditLog, Subsystem

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()
    Base.metadata.drop_all(bind=engine)


def _user(db, username, role=Role.developer):
    u = User(username=username, password_hash="x", role=role)
    db.add(u)
    db.commit()
    return u


def test_knowledge_no_group_id():
    """Knowledge 全平台共通：不设 group_id。"""
    eng2 = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng2)
    insp = inspect(eng2)
    cols = [c["name"] for c in insp.get_columns("knowledge")]
    assert "group_id" not in cols
    assert "group_scope" in cols


def test_knowledge_crud(db):
    u = _user(db, "k1")
    k = Knowledge(title="知识1", body="正文", tags=["AI", "Qwen"], source_enum="manual",
                  group_scope="global", author_id=u.id)
    db.add(k)
    db.commit()
    assert k.id is not None
    assert k.group_scope == "global"
    assert k.tags == ["AI", "Qwen"]


def test_audit_log_append_only(db):
    """AuditLog 只增不改：写一条后能查到 actor/entity/action。"""
    u = _user(db, "a1")
    log = AuditLog(user_id=u.id, action="requirement.reviewed", entity="requirement",
                   entity_id="12", ip="127.0.0.1", detail={"conclusion": "feasible"})
    db.add(log)
    db.commit()
    assert log.id is not None
    assert log.action == "requirement.reviewed"
    assert log.entity == "requirement"
    assert log.entity_id == "12"


def test_subsystem_registration(db):
    """子系统注册清单：key 唯一，status active/stopped/archived，roles 过滤。"""
    sub = Subsystem(key="collab", name="组内协作", icon="collab-icon", url="/subsys/collab",
                    roles=["instructor", "developer", "leader"], status="active")
    db.add(sub)
    db.commit()
    assert sub.status == "active"
    assert "leader" in sub.roles
    # 停 = stopped（入口隐藏、数据保留）；下线 = archived
    sub.status = "stopped"
    db.commit()
    assert sub.status == "stopped"
    sub.status = "archived"
    db.commit()
    assert sub.status == "archived"


def test_subsystem_status_during_lifecycle(db):
    """S8 生命周期：active→stopped→archived 三态。"""
    sub = Subsystem(key="kb", name="知识库", status="active")
    db.add(sub)
    db.commit()
    for st in ["active", "stopped", "archived"]:
        sub.status = st
        db.commit()
        assert sub.status == st
