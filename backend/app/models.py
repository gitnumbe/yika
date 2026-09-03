import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Role(str, enum.Enum):
    admin = "admin"          # 全局管理员：管用户/建组/派组长/系统配置
    leader = "leader"        # 组长：需求评审拍板（专属）
    instructor = "instructor"  # 讲师：给意见/录需求
    developer = "developer"  # 开发：交付


class Group(Base):
    """业务组（组=业务单元，组内讲师+开发+组长）。组织预留 1:N。"""
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    leader_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    delivered = "delivered"
    paused = "paused"


class ReqStatus(str, enum.Enum):
    draft = "draft"                # 草稿
    pending_review = "pending_review"  # 待评审
    feasible = "feasible"          # 可行
    plan_needed = "plan_needed"    # 需调整-方案待调（返技术）
    info_needed = "info_needed"    # 需调整-信息待补（返提出方）
    infeasible = "infeasible"      # 不可行（归档可重评）
    in_dev = "in_dev"              # 开发中
    delivered = "delivered"        # 已交付


class ReqSource(str, enum.Enum):
    ai_extract = "ai_extract"   # A3 提炼
    manual = "manual"           # 手动录入


class ReqPriority(str, enum.Enum):
    high = "high"
    med = "med"
    low = "low"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(Enum(Role))
    display_name: Mapped[str] = mapped_column(String(64), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 组织预留 1:N（首期 1 个组；group_ids 存组 id 列表，防讲师跨组支援返工）
    group_ids: Mapped[list] = mapped_column(JSON, default=list)
    # 生产级（开发文档 §10.3）：登录安全
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RefreshToken(Base):
    """刷新令牌（只存哈希，可吊销）——生产级双令牌。"""
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(200))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """审计日志（只增不改）——生产级 §10.3。"""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # actor
    action: Mapped[str] = mapped_column(String(50))
    target_type: Mapped[str] = mapped_column(String(50), default="")
    target_id: Mapped[str] = mapped_column(String(100), default="")
    entity: Mapped[str] = mapped_column(String(50), default="")
    entity_id: Mapped[str] = mapped_column(String(100), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    ua: Mapped[str] = mapped_column(String(300), default="")
    detail: Mapped[dict] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    """系统配置（免改码）——生产级 §7.1。"""
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default={})
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Customer(Base):
    """客户（组私有，带 group_id 冗余供组隔离过滤）。"""
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    industry: Mapped[str] = mapped_column(String(100), default="")
    scale: Mapped[str] = mapped_column(String(50), default="")
    main_business: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="manual")
    ai_status: Mapped[str] = mapped_column(String(20), default="pending")
    ai_flags: Mapped[list] = mapped_column(JSON, default=list)
    owner_instructor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Project(Base):
    """项目（客户下，一个客户可多项目；需求挂项目下）。"""
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.planned)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Requirement(Base):
    """需求（挂项目下，继承组归属；v3 状态机 + 来源溯源 + 组长评审）。"""
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[ReqSource] = mapped_column(Enum(ReqSource), default=ReqSource.manual)  # ai_extract/manual
    source_note_id: Mapped[int | None] = mapped_column(ForeignKey("notes.id"), nullable=True)  # 溯源到沟通记录
    status: Mapped[ReqStatus] = mapped_column(Enum(ReqStatus), default=ReqStatus.draft)
    priority: Mapped[ReqPriority] = mapped_column(Enum(ReqPriority), default=ReqPriority.med)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_conclusion: Mapped[str] = mapped_column(Text, default="")
    infeasible_reason: Mapped[str] = mapped_column(Text, default="")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # A3 置信度
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RequirementCandidate(Base):
    """候选需求（A3 临时实体；人工确认后才转正式需求——防幻觉铁律）。"""
    __tablename__ = "requirement_candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)  # 确认时指定
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/confirmed/converted/rejected
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Note(Base):
    """沟通记录/笔记（挂客户下；语音链路产物；A6 结构化笔记）。"""
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    scenario: Mapped[str] = mapped_column(String(30), default="req_discussion")  # consult_training/req_discussion/other
    audio_path: Mapped[str] = mapped_column(String(300), default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    ai_structured: Mapped[dict] = mapped_column(JSON, default=dict)  # A6 四块 summary/points/decisions/todos
    quality_flags: Mapped[dict] = mapped_column(JSON, default=dict)  # A6 低置信字段留空
    note_author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Knowledge(Base):
    """知识（**全平台共通**，跨组可查；不设 group_id，用 group_scope=global 标记）。"""
    __tablename__ = "knowledge"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    source_enum: Mapped[str] = mapped_column(String(20), default="manual")  # manual/ai_extract
    source_ref_id: Mapped[str] = mapped_column(String(200), default="")
    group_scope: Mapped[str] = mapped_column(String(20), default="global")  # 全平台共通
    status: Mapped[str] = mapped_column(String(20), default="published")  # P3.5: draft待审核/published已发布
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # 审核人
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QA(Base):
    __tablename__ = "qa"
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    knowledge_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="answered")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # 生产级（v2.0）：TTS 朗读缓存
    tts_audio_path: Mapped[str] = mapped_column(String(300), default="")


class LearningTask(Base):
    __tablename__ = "learning_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    assigner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo")


class Recording(Base):
    __tablename__ = "recordings"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    scene: Mapped[str] = mapped_column(String(20), default="internal")
    audio_path: Mapped[str] = mapped_column(String(300), default="")
    transcript: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProcessingTask(Base):
    __tablename__ = "processing_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recordings.id"))
    stage: Mapped[str] = mapped_column(String(30), default="transcribe")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # 生产级（开发文档 §8.6）：重试/幂等
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subsystem(Base):
    """子系统注册清单（S1）：外壳按此+角色展示图标墙；停=关入口保数据；下线=归档。"""
    __tablename__ = "subsystems"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    icon: Mapped[str] = mapped_column(String(100), default="")
    url: Mapped[str] = mapped_column(String(200), default="")
    roles: Mapped[list] = mapped_column(JSON, default=list)  # 可访问角色
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/stopped/archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
