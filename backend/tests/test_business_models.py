"""P0.2b 业务主数据 L1 单测：Customer/Project/Requirement/RequirementCandidate/Note。

覆盖：
- 每张业务表必带 group_id 冗余（组隔离过滤用）
- Requirement 状态机枚举（v3：draft→pending_review→feasible/plan_needed/info_needed/infeasible→in_dev→delivered）
- Requirement 来源溯源（ai_extract/manual + source_note_id）
- RequirementCandidate 候选需求（防幻觉：confirm 后才转正式）
- Note 挂客户 + A6 结构化 JSON
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Group, Role, User, Customer, Project, ProjectStatus,
    Requirement, RequirementCandidate, Note, ReqStatus, ReqSource, ReqPriority,
)

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()
    Base.metadata.drop_all(bind=engine)


def _mk_user(db, username, role):
    u = User(username=username, password_hash="x", role=role)
    db.add(u)
    db.commit()
    return u


def test_all_business_tables_have_group_id():
    """客户/项目/需求/候选/笔记 均带 group_id 冗余。"""
    eng2 = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng2)
    insp = inspect(eng2)
    for tbl in ["customers", "projects", "requirements", "requirement_candidates", "notes"]:
        cols = [c["name"] for c in insp.get_columns(tbl)]
        assert "group_id" in cols, f"{tbl} 缺 group_id"


def test_customer_group_private(db):
    g = Group(name="A组")
    db.add(g)
    db.commit()
    u = _mk_user(db, "l1", Role.leader)
    c = Customer(group_id=g.id, name="客户X", created_by=u.id)
    db.add(c)
    db.commit()
    assert c.group_id == g.id


def test_project_under_customer(db):
    g = Group(name="B组"); db.add(g); db.commit()
    u = _mk_user(db, "l2", Role.leader)
    c = Customer(group_id=g.id, name="客户Y", created_by=u.id)
    db.add(c); db.commit()
    p = Project(customer_id=c.id, name="项目1", group_id=g.id, status=ProjectStatus.planned)
    db.add(p); db.commit()
    assert p.customer_id == c.id
    assert p.status == ProjectStatus.planned
    assert p.group_id == g.id


def test_requirement_state_machine_enum(db):
    """v3 状态机枚举全集。"""
    g = Group(name="C组"); db.add(g); db.commit()
    u = _mk_user(db, "l3", Role.leader)
    c = Customer(group_id=g.id, name="客户Z", created_by=u.id); db.add(c); db.commit()
    p = Project(customer_id=c.id, name="P", group_id=g.id); db.add(p); db.commit()
    r = Requirement(project_id=p.id, group_id=g.id, title="需求1", created_by=u.id)
    db.add(r); db.commit()
    assert r.status == ReqStatus.draft
    assert {s.value for s in ReqStatus} == {
        "draft", "pending_review", "feasible", "plan_needed",
        "info_needed", "infeasible", "in_dev", "delivered",
    }


def test_requirement_priority_enum(db):
    assert {x.value for x in ReqPriority} == {"high", "med", "low"}


def test_requirement_source_trace(db):
    """需求来源溯源：ai_extract/manual + source_note_id。"""
    assert {x.value for x in ReqSource} == {"ai_extract", "manual"}
    g = Group(name="D组"); db.add(g); db.commit()
    u = _mk_user(db, "l4", Role.leader)
    c = Customer(group_id=g.id, name="客户W", created_by=u.id); db.add(c); db.commit()
    p = Project(customer_id=c.id, name="P", group_id=g.id); db.add(p); db.commit()
    note = Note(customer_id=c.id, group_id=g.id, transcript="转写", note_author_id=u.id)
    db.add(note); db.commit()
    r = Requirement(project_id=p.id, group_id=g.id, title="R", source=ReqSource.ai_extract, source_note_id=note.id, created_by=u.id)
    db.add(r); db.commit()
    assert r.source == ReqSource.ai_extract
    assert r.source_note_id == note.id


def test_note_ai_structured(db):
    """Note 挂客户 + A6 结构化四块。"""
    g = Group(name="E组"); db.add(g); db.commit()
    u = _mk_user(db, "l5", Role.instructor)
    c = Customer(group_id=g.id, name="客户V", created_by=u.id); db.add(c); db.commit()
    note = Note(customer_id=c.id, group_id=g.id, note_author_id=u.id,
                ai_structured={"summary": "摘要", "points": ["要点1"], "decisions": [], "todos": []},
                quality_flags={"low_confidence": ["summary"]})
    db.add(note); db.commit()
    assert note.customer_id == c.id
    assert note.ai_structured["summary"] == "摘要"
    assert note.quality_flags["low_confidence"] == ["summary"]


def test_requirement_candidate_before_confirm(db):
    """候选需求：pending 未确认，确认后才转正式需求（防幻觉）。"""
    g = Group(name="F组"); db.add(g); db.commit()
    u = _mk_user(db, "l6", Role.leader)
    c = Customer(group_id=g.id, name="客户U", created_by=u.id); db.add(c); db.commit()
    note = Note(customer_id=c.id, group_id=g.id, note_author_id=u.id); db.add(note); db.commit()
    cand = RequirementCandidate(note_id=note.id, title="候选", status="pending", group_id=g.id)
    db.add(cand); db.commit()
    assert cand.status == "pending"
    # 确认时指定项目，状态变 confirmed；人工确认后转正式需求
    p = Project(customer_id=c.id, name="P", group_id=g.id); db.add(p); db.commit()
    cand.project_id = p.id
    cand.status = "confirmed"
    db.commit()
    assert cand.status == "confirmed"
    assert cand.project_id == p.id
