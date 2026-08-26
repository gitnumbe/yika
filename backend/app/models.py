import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Role(str, enum.Enum):
    admin = "admin"
    tech = "tech"
    instructor = "instructor"


class ProjectStatus(str, enum.Enum):
    prep = "prep"
    training = "training"
    exploration = "exploration"
    review = "review"
    dev = "dev"
    delivered = "delivered"


class ReqStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    feasible = "feasible"
    in_dev = "in_dev"
    delivered = "delivered"
    info_needed = "info_needed"
    plan_needed = "plan_needed"
    infeasible = "infeasible"


class ReqSource(str, enum.Enum):
    training = "training"
    discussion = "discussion"
    manual = "manual"
    reuse = "reuse"
    internal = "internal"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(Enum(Role))


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    industry: Mapped[str] = mapped_column(String(100), default="")
    contact: Mapped[str] = mapped_column(String(100), default="")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.prep)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[ReqSource] = mapped_column(Enum(ReqSource), default=ReqSource.manual)
    source_ref: Mapped[str] = mapped_column(String(200), default="")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ReqStatus] = mapped_column(Enum(ReqStatus), default=ReqStatus.draft)
    review_conclusion: Mapped[str] = mapped_column(Text, default="")
    infeasible_reason: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, default=0)


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    scene: Mapped[str] = mapped_column(String(20), default="internal")
    transcript: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    points: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[str] = mapped_column(Text, default="")
    todos: Mapped[str] = mapped_column(Text, default="")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Knowledge(Base):
    __tablename__ = "knowledge"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="manual")


class QA(Base):
    __tablename__ = "qa"
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    knowledge_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="answered")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
