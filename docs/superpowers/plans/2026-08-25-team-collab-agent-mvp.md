# 组内队员协作 Agent —— MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个可本机多开运行的 MVP：账号登录、客户/项目/需求档案、需求状态机、录音→转写→去噪→笔记→需求提炼完整链路、答疑 agent + 知识库、数据备份导出。

**Architecture:** Electron + React 桌面壳作为客户端，通过内网 HTTP 调用 FastAPI 后端。后端用 SQLite 存数据，AI 能力走抽象层（大模型=内网 OpenAI 兼容接口·实例以 `.env` 为准，去噪=本机 Ollama 小模型 `qwen3:4b-instruct`，STT=Qwen3-ASR-1.7B 本地服务·决策 09，TTS=dots.tts-mf）。录音转写是耗时任务，用后台任务 + 任务状态表驱动，客户端轮询进度。

**Tech Stack:** Python 3.10 + FastAPI + SQLAlchemy 2.0 + PyJWT + pytest；Electron + React + TypeScript + Vite。

**Spec:** `docs/superpowers/specs/2026-08-25-team-collab-agent-design.md`

## Global Constraints

- 后端 Python 3.10，数据库 SQLite（起步），ORM 用 SQLAlchemy 2.0。
- LLM 双源：大模型（内网 OpenAI 兼容接口，当前实例 `deepseek-v4-flash-vision-exp`，`base_url`/`api_key`/`model` 从环境变量读取——**模型名只在 `.env` 与开发文档 §4.0 基线表登记，正文不写死**）；去噪小模型（本机 Ollama `qwen3:4b-instruct`）。
- ASR(STT)：Qwen3-ASR-1.7B 本地服务（决策 09，替代 FunASR），`ASR_BASE_URL` 从环境变量读取，接口做成可替换抽象。
- 所有 LLM 产出只进"候选区"，落库决策由人确认（防幻觉铁律）。
- 需求状态枚举：`draft`、`pending_review`、`feasible`、`in_dev`、`delivered`、`info_needed`（信息待补充→讲师）、`plan_needed`（方案待调整→技术）、`infeasible`（不可行，可重新评估）。
- 数据模型从一开始就是多用户的（每条数据挂 user_id 或 author_id）。
- 角色枚举：`admin`、`tech`、`instructor`。
- 所有路径用英文标识符，UI 文案用中文。

---

## 文件结构总览

```
backend/
  app/
    __init__.py
    main.py            # FastAPI 入口，挂路由
    config.py          # 环境变量配置（LLM/ASR/base）
    database.py        # SQLAlchemy engine + session
    models.py          # 全部 ORM 模型
    schemas.py         # Pydantic 请求/响应模型
    auth.py            # JWT 签发 + 依赖注入
    state_machine.py   # 需求状态机（纯函数）
    routers/
      __init__.py
      auth.py          # 注册/登录
      customers.py     # 客户
      projects.py      # 项目
      requirements.py  # 需求
      knowledge.py     # 知识库
      qa.py            # 答疑
      recordings.py    # 录音/转写/笔记/提炼
      backup.py        # 备份导出
    services/
      __init__.py
      llm.py           # LLM 抽象层（大模型 + 去噪小模型）
      asr.py           # STT 抽象层（Qwen3-ASR）
      tts.py           # TTS 抽象层（dots.tts·v2.0）
      denoise.py       # 去噪（Ollama 二分类）
      note_gen.py      # 笔记整理（四块结构化）
      req_extract.py   # 需求提炼（候选需求）
      qa_service.py    # 答疑检索+回流
      pipeline.py      # 录音后处理流水线编排
    tasks.py           # 后台任务（转写流水线）
  tests/
    __init__.py
    conftest.py        # 测试 fixture（内存 SQLite + TestClient）
    test_auth.py
    test_state_machine.py
    test_requirements.py
    test_denoise.py
    test_note_gen.py
    test_req_extract.py
    test_qa.py
  requirements.txt
  .env.example

frontend/
  package.json
  vite.config.ts
  tsconfig.json
  electron/main.js      # Electron 主进程
  src/
    main.tsx
    App.tsx
    api/client.ts       # fetch 封装 + token
    context/AuthContext.tsx
    pages/Login.tsx
    pages/Dashboard.tsx
    pages/Projects.tsx
    pages/Requirements.tsx
    pages/Notes.tsx
    pages/Knowledge.tsx
    pages/QA.tsx
    components/Recorder.tsx   # 悬浮球录音
    components/NoteEditor.tsx  # 笔记 + 候选需求编辑
```

---

### Task 1: 后端脚手架

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `app.config.Settings`（pydantic-settings，字段 `llm_base_url`、`llm_api_key`、`llm_model`、`ollama_base_url`、`ollama_model`、`asr_base_url`、`database_url`、`secret_key`）；`app.database.get_session()` 生成器；`app.database.Base`；`app.main.app`（FastAPI 实例）。

- [ ] **Step 1: 写 requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
pydantic==2.9.2
pydantic-settings==2.6.0
PyJWT==2.9.0
bcrypt==4.2.0
python-multipart==0.0.12
httpx==0.27.2
pytest==8.3.3
```

- [ ] **Step 2: 写 .env.example**

```
LLM_BASE_URL=http://<内网Qwen地址>/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-v4-flash-vision-exp
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b-instruct
ASR_BASE_URL=http://<STT服务>/v1
TTS_BASE_URL=http://<TTS服务>/v1
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=change-me
```

- [ ] **Step 3: 写 config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash-vision-exp"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    asr_base_url: str = ""
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "change-me"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 4: 写 database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: 写 main.py（最小健康检查）**

```python
from fastapi import FastAPI

app = FastAPI(title="Team Collab Agent")

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: 写 conftest.py（fixture：独立测试库 + TestClient）**

```python
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"

from app.database import Base, get_session
from app.main import app

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def client(db):
    def override():
        yield db
    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 7: 运行测试验证**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 收集到测试但无失败（此时 conftest 引用 models 前，Base 尚未 import models，需确保 main.py 后续 Task 3 会 import models）

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "chore: backend scaffold (FastAPI + SQLAlchemy + config)"
```

---

### Task 2: 前端脚手架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/electron/main.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

**Interfaces:**
- Produces: `frontend/src/api/client.ts` 里的 `apiFetch`（后续任务使用）；Electron 主进程加载 `http://localhost:5173`（dev）或打包后的 `dist/index.html`。

- [ ] **Step 1: 写 package.json**

```json
{
  "name": "team-collab-agent",
  "private": true,
  "version": "0.1.0",
  "main": "electron/main.js",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "electron": "electron ."
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "electron": "^32.0.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.3"
  }
}
```

- [ ] **Step 2: 写 vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
```

- [ ] **Step 3: 写 electron/main.js**

```javascript
const { app, BrowserWindow } = require("electron");
const path = require("path");

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  if (process.env.VITE_DEV) {
    win.loadURL("http://localhost:5173");
  } else {
    win.loadFile(path.join(__dirname, "../dist/index.html"));
  }
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => app.quit());
```

- [ ] **Step 4: 写 index.html + src/main.tsx + src/App.tsx（占位首页）**

```tsx
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>
);
```

```tsx
// src/App.tsx
export default function App() {
  return <div>Team Collab Agent</div>;
}
```

- [ ] **Step 5: 验证 dev 启动**

Run: `cd frontend && npm install && npm run dev`
Expected: Vite 启动，浏览器访问 `localhost:5173` 显示 "Team Collab Agent"（Electron 打包验证放 Task 16）

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "chore: frontend scaffold (Electron + React + Vite)"
```

---

### Task 3: 数据模型

**Files:**
- Create: `backend/app/models.py`
- Modify: `backend/app/main.py`（import models 确保建表）

**Interfaces:**
- Produces: ORM 类 `User`、`Customer`、`Project`、`Requirement`、`Note`、`Knowledge`、`QA`、`LearningTask`、`Recording`、`ProcessingTask`（字段见下）。后续所有 task 依赖这些字段名。

- [ ] **Step 1: 写 models.py**

```python
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
import enum

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
```

- [ ] **Step 2: 在 main.py 末尾 import models 并建表**

```python
from . import models
from .database import Base, engine

Base.metadata.create_all(bind=engine)
```

- [ ] **Step 3: 运行测试验证建表无异常**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 通过（conftest 里的 `Base.metadata.create_all` 现在包含全部模型）

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py backend/app/main.py
git commit -m "feat: define data models (user/customer/project/requirement/note/knowledge/qa/recording)"
```

---

### Task 4: 认证（注册/登录 + JWT）

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`（挂 auth 路由）
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `app.auth.hash_password(pw) -> str`、`app.auth.verify_password(pw, hashed) -> bool`、`app.auth.create_token(user_id: int, role: str) -> str`、`app.auth.get_current_user(db, token) -> User`、`app.auth.require_role(role)` 依赖。
- Consumes: `app.models.User`、`app.database.get_session`。

- [ ] **Step 1: 写 auth.py**

```python
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .config import settings
from .database import get_session
from .models import User

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def create_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")

def get_current_user(token: str = Header(None), db: Session = Depends(get_session)) -> User:
    if not token:
        raise HTTPException(401, "未登录")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "登录已失效")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "用户不存在")
    return user

def require_role(*roles: str):
    def dep(user: User = Depends(get_current_user)):
        if user.role.value not in roles:
            raise HTTPException(403, "权限不足")
        return user
    return dep
```

- [ ] **Step 2: 写 schemas.py（认证部分）**

```python
from pydantic import BaseModel

class RegisterIn(BaseModel):
    username: str
    password: str
    role: str

class LoginIn(BaseModel):
    username: str
    password: str

class TokenOut(BaseModel):
    token: str
    role: str
```

- [ ] **Step 3: 写 routers/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import User, Role
from .. import auth
from ..schemas import RegisterIn, LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_session)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    if body.role not in [r.value for r in Role]:
        raise HTTPException(400, "非法角色")
    user = User(username=body.username, password_hash=auth.hash_password(body.password), role=body.role)
    db.add(user); db.commit(); db.refresh(user)
    return TokenOut(token=auth.create_token(user.id, user.role.value), role=user.role.value)

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not auth.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return TokenOut(token=auth.create_token(user.id, user.role.value), role=user.role.value)
```

- [ ] **Step 4: main.py 挂路由**

```python
from .routers import auth as auth_router
app.include_router(auth_router.router)
```

- [ ] **Step 5: 写测试 test_auth.py**

```python
def test_register_login(client):
    r = client.post("/auth/register", json={"username": "alice", "password": "pw123", "role": "instructor"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert token

    r2 = client.post("/auth/login", json={"username": "alice", "password": "pw123"})
    assert r2.status_code == 200
    assert r2.json()["role"] == "instructor"

def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "bob", "password": "pw", "role": "tech"})
    r = client.post("/auth/login", json={"username": "bob", "password": "wrong"})
    assert r.status_code == 401
```

- [ ] **Step 6: 运行测试**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/auth.py backend/app/schemas.py backend/app/routers backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: JWT auth (register/login)"
```

---

### Task 5: 客户 + 项目 CRUD

**Files:**
- Create: `backend/app/routers/customers.py`
- Create: `backend/app/routers/projects.py`
- Modify: `backend/app/schemas.py`（加 Customer/Project schema）
- Modify: `backend/app/main.py`（挂路由）
- Test: `backend/tests/test_customers_projects.py`

**Interfaces:**
- Produces: `GET/POST /customers`、`GET/POST /projects`。
- Consumes: `auth.require_role`、`app.models.Customer`、`app.models.Project`。

- [ ] **Step 1: schemas.py 追加**

```python
class CustomerIn(BaseModel):
    name: str
    industry: str = ""
    contact: str = ""

class CustomerOut(CustomerIn):
    id: int
    class Config:
        from_attributes = True

class ProjectIn(BaseModel):
    name: str
    customer_id: int

class ProjectOut(BaseModel):
    id: int
    name: str
    customer_id: int
    status: str
    class Config:
        from_attributes = True
```

- [ ] **Step 2: 写 routers/customers.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import Customer, User
from ..auth import require_role
from ..schemas import CustomerIn, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("/", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return db.query(Customer).all()

@router.post("/", response_model=CustomerOut)
def create_customer(body: CustomerIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    c = Customer(**body.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c
```

- [ ] **Step 3: 写 routers/projects.py（同结构）**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import Project, User
from ..auth import require_role
from ..schemas import ProjectIn, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return db.query(Project).all()

@router.post("/", response_model=ProjectOut)
def create_project(body: ProjectIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    p = Project(**body.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return p
```

- [ ] **Step 4: main.py 挂路由**

```python
from .routers import customers, projects
app.include_router(customers.router)
app.include_router(projects.router)
```

- [ ] **Step 5: 写测试（注册用户 + 建客户 + 建项目）**

```python
def _token(client, username="tech1", role="tech"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]

def test_create_customer_and_project(client):
    token = _token(client)
    h = {"token": token}
    c = client.post("/customers/", json={"name": "A公司", "industry": "制造"}, headers=h)
    assert c.status_code == 200
    cid = c.json()["id"]
    p = client.post("/projects/", json={"name": "A公司智能客服", "customer_id": cid}, headers=h)
    assert p.status_code == 200
    assert p.json()["customer_id"] == cid
```

- [ ] **Step 6: 运行测试**

Run: `cd backend && python -m pytest tests/test_customers_projects.py -v`
Expected: passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/customers.py backend/app/routers/projects.py backend/app/schemas.py backend/app/main.py backend/tests/test_customers_projects.py
git commit -m "feat: customer + project CRUD"
```

---

### Task 6: 需求 CRUD + 状态机

**Files:**
- Create: `backend/app/state_machine.py`
- Create: `backend/app/routers/requirements.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_state_machine.py`
- Test: `backend/tests/test_requirements.py`

**Interfaces:**
- Produces: `app.state_machine.allowed_transitions: dict[ReqStatus, set[ReqStatus]]`、`app.state_machine.can_transition(frm, to) -> bool`、`app.state_machine.transition(req, to, reason="") -> Requirement`；路由 `GET/POST /requirements`、`POST /requirements/{id}/transition`。
- Consumes: `app.models.Requirement`、`ReqStatus`。

- [ ] **Step 1: 写 state_machine.py（纯函数，无 IO）**

```python
from .models import Requirement, ReqStatus

allowed_transitions = {
    ReqStatus.draft: {ReqStatus.pending_review},
    ReqStatus.pending_review: {ReqStatus.feasible, ReqStatus.info_needed, ReqStatus.plan_needed, ReqStatus.infeasible},
    ReqStatus.feasible: {ReqStatus.in_dev},
    ReqStatus.in_dev: {ReqStatus.delivered},
    ReqStatus.info_needed: {ReqStatus.pending_review},
    ReqStatus.plan_needed: {ReqStatus.pending_review},
    ReqStatus.infeasible: {ReqStatus.pending_review},
    ReqStatus.delivered: set(),
}

def can_transition(frm: ReqStatus, to: ReqStatus) -> bool:
    return to in allowed_transitions.get(frm, set())

def transition(req: Requirement, to: ReqStatus, reason: str = "") -> Requirement:
    if not can_transition(req.status, to):
        raise ValueError(f"非法状态流转: {req.status.value} -> {to.value}")
    req.status = to
    if to == ReqStatus.infeasible:
        req.infeasible_reason = reason
    return req
```

- [ ] **Step 2: 写 test_state_machine.py（纯单元测试）**

```python
import pytest
from app.state_machine import can_transition
from app.models import ReqStatus as S

def test_review_branches():
    assert can_transition(S.pending_review, S.feasible)
    assert can_transition(S.pending_review, S.info_needed)
    assert can_transition(S.pending_review, S.plan_needed)
    assert can_transition(S.pending_review, S.infeasible)

def test_adjust_returns_to_review():
    assert can_transition(S.info_needed, S.pending_review)
    assert can_transition(S.plan_needed, S.pending_review)

def test_infeasible_reopen():
    assert can_transition(S.infeasible, S.pending_review)

def test_illegal_transitions_rejected():
    assert not can_transition(S.draft, S.delivered)
    assert not can_transition(S.delivered, S.in_dev)
    assert not can_transition(S.draft, S.infeasible)
```

- [ ] **Step 3: 运行状态机测试**

Run: `cd backend && python -m pytest tests/test_state_machine.py -v`
Expected: 4 passed

- [ ] **Step 4: schemas.py 追加需求 schema**

```python
class RequirementIn(BaseModel):
    title: str
    description: str = ""
    source: str = "manual"
    source_ref: str = ""
    project_id: int | None = None
    customer_id: int | None = None
    priority: int = 0

class TransitionIn(BaseModel):
    to: str
    reason: str = ""
```

- [ ] **Step 5: 写 routers/requirements.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import Requirement, ReqStatus, User
from ..auth import require_role
from ..schemas import RequirementIn, TransitionIn
from .. import state_machine

router = APIRouter(prefix="/requirements", tags=["requirements"])

@router.post("/")
def create_requirement(body: RequirementIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    r = Requirement(**body.model_dump(), author_id=user.id)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "status": r.status.value, "title": r.title}

@router.get("/")
def list_requirements(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return [{"id": r.id, "title": r.title, "status": r.status.value, "project_id": r.project_id} for r in db.query(Requirement).all()]

@router.post("/{req_id}/transition")
def transition_requirement(req_id: int, body: TransitionIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech"))):
    r = db.get(Requirement, req_id)
    if not r:
        raise HTTPException(404, "需求不存在")
    try:
        state_machine.transition(r, ReqStatus(body.to), body.reason)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"id": r.id, "status": r.status.value, "infeasible_reason": r.infeasible_reason}
```

- [ ] **Step 6: 写 test_requirements.py（走 API 验证状态机 + 权限）**

```python
def _token(client, username="tech1", role="tech"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]

def test_full_review_flow(client):
    t = _token(client)
    h = {"token": t}
    r = client.post("/requirements/", json={"title": "自动回复客户咨询"}, headers=h).json()
    rid = r["id"]
    # draft -> pending_review
    client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h)
    # pending_review -> info_needed
    client.post(f"/requirements/{rid}/transition", json={"to": "info_needed", "reason": "需向客户确认并发量"}, headers=h)
    # info_needed -> pending_review
    r2 = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h)
    assert r2.json()["status"] == "pending_review"

def test_illegal_transition_rejected(client):
    t = _token(client)
    h = {"token": t}
    rid = client.post("/requirements/", json={"title": "x"}, headers=h).json()["id"]
    # draft 直接跳到 delivered 应被拒
    r = client.post(f"/requirements/{rid}/transition", json={"to": "delivered"}, headers=h)
    assert r.status_code == 400

def test_instructor_cannot_transition(client):
    t = _token(client, username="inst1", role="instructor")
    h = {"token": t}
    rid = client.post("/requirements/", json={"title": "x"}, headers=h).json()["id"]
    r = client.post(f"/requirements/{rid}/transition", json={"to": "pending_review"}, headers=h)
    assert r.status_code == 403
```

- [ ] **Step 7: 运行测试**

Run: `cd backend && python -m pytest tests/test_requirements.py -v`
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/state_machine.py backend/app/routers/requirements.py backend/app/schemas.py backend/app/main.py backend/tests/test_state_machine.py backend/tests/test_requirements.py
git commit -m "feat: requirement CRUD + state machine with role gate"
```

---

### Task 7: 知识库 CRUD

**Files:**
- Create: `backend/app/routers/knowledge.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_knowledge.py`

**Interfaces:**
- Produces: `GET/POST /knowledge`。
- Consumes: `app.models.Knowledge`。

- [ ] **Step 1: schemas.py 追加**

```python
class KnowledgeIn(BaseModel):
    title: str
    content: str
    source: str = "manual"

class KnowledgeOut(KnowledgeIn):
    id: int
    class Config:
        from_attributes = True
```

- [ ] **Step 2: 写 routers/knowledge.py（结构同 customers.py）**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import Knowledge, User
from ..auth import require_role
from ..schemas import KnowledgeIn, KnowledgeOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.get("/", response_model=list[KnowledgeOut])
def list_knowledge(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return db.query(Knowledge).all()

@router.post("/", response_model=KnowledgeOut)
def create_knowledge(body: KnowledgeIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech"))):
    k = Knowledge(**body.model_dump())
    db.add(k); db.commit(); db.refresh(k)
    return k
```

- [ ] **Step 3: main.py 挂路由**

```python
from .routers import knowledge
app.include_router(knowledge.router)
```

- [ ] **Step 4: 写测试（技术可建，讲师只读）**

```python
def _token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]

def test_tech_create_instructor_read(client):
    t = _token(client, "tech1", "tech")
    client.post("/knowledge/", json={"title": "agent 基础", "content": "..."}, headers={"token": t})
    i = _token(client, "inst1", "instructor")
    r = client.get("/knowledge/", headers={"token": i})
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_instructor_cannot_create(client):
    i = _token(client, "inst2", "instructor")
    r = client.post("/knowledge/", json={"title": "x", "content": "y"}, headers={"token": i})
    assert r.status_code == 403
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_knowledge.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/knowledge.py backend/app/schemas.py backend/app/main.py backend/tests/test_knowledge.py
git commit -m "feat: knowledge base CRUD (tech write, instructor read)"
```

---

### Task 8: LLM 抽象层（大模型 + 去噪小模型）

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/llm.py`
- Test: `backend/tests/test_llm.py`

**Interfaces:**
- Produces: `app.services.llm.get_llm() -> LLMProvider`（大模型，实例随 `.env` 配置）、`app.services.llm.get_denoise_llm() -> LLMProvider`（Ollama）。`LLMProvider.chat(messages: list[dict]) -> str`。
- Consumes: `app.config.settings`。

- [ ] **Step 1: 写 llm.py**

```python
import httpx
from ..config import settings

class LLMProvider:
    def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError

class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": messages},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        resp = httpx.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

def get_llm() -> LLMProvider:
    return OpenAICompatProvider(settings.llm_base_url, settings.llm_api_key, settings.llm_model)

def get_denoise_llm() -> LLMProvider:
    return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
```

- [ ] **Step 2: 写 test_llm.py（mock httpx，验证请求格式，不发真实请求）**

```python
import httpx
from app.services.llm import OpenAICompatProvider, OllamaProvider

def test_openai_provider_formats_request(monkeypatch):
    calls = {}
    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["json"] = kwargs["json"]
        class R:
            def raise_for_status(self): pass
            def json(self): return {"choices": [{"message": {"content": "hi"}}]}
        return R()
    monkeypatch.setattr(httpx, "post", fake_post)
    p = OpenAICompatProvider("http://x/v1", "sk", os.environ.get("LLM_MODEL", "deepseek-v4-flash-vision-exp"))
    assert p.chat([{"role": "user", "content": "你好"}]) == "hi"
    assert calls["url"] == "http://x/v1/chat/completions"
    assert calls["json"]["model"] == os.environ.get("LLM_MODEL", "deepseek-v4-flash-vision-exp")

def test_ollama_provider_formats_request(monkeypatch):
    calls = {}
    def fake_post(url, **kwargs):
        calls["url"] = url
        calls["json"] = kwargs["json"]
        class R:
            def raise_for_status(self): pass
            def json(self): return {"message": {"content": "ok"}}
        return R()
    monkeypatch.setattr(httpx, "post", fake_post)
    p = OllamaProvider("http://127.0.0.1:11434", "qwen3:4b-instruct")
    assert p.chat([{"role": "user", "content": "x"}]) == "ok"
    assert calls["url"] == "http://127.0.0.1:11434/api/chat"
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_llm.py -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/llm.py backend/tests/test_llm.py
git commit -m "feat: LLM abstraction layer (big-model OpenAI-compat + denoise Ollama)"
```

---

### Task 9: STT/TTS 抽象层（Qwen3-ASR + dots.tts）

**Files:**
- Create: `backend/app/services/asr.py`
- Test: `backend/tests/test_asr.py`

**Interfaces:**
- Produces: `app.services.asr.get_asr() -> ASRProvider`、`ASRProvider.transcribe(audio_bytes: bytes) -> str`。
- Consumes: `app.config.settings`。

- [ ] **Step 1: 写 asr.py**

```python
import httpx
from ..config import settings

class ASRProvider:
    def transcribe(self, audio_bytes: bytes) -> str:
        raise NotImplementedError

class QwenASRProvider(ASRProvider):   # 决策 09：Qwen3-ASR（原 FunASR 已变更）
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def transcribe(self, audio_bytes: bytes) -> str:
        resp = httpx.post(
            f"{self.base_url}/recognition",
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
        # Qwen3-ASR 返回 {text, segments, language}；此处约定 HTTP 契约（开发文档 §5.1）
        return data.get("text", "")

def get_asr() -> ASRProvider:
    return QwenASRProvider(settings.asr_base_url)
```

- [ ] **Step 2: 写 test_asr.py（mock httpx）**

```python
import httpx
from app.services.asr import QwenASRProvider

def test_funasr_formats_request(monkeypatch):
    def fake_post(url, **kwargs):
        assert url.endswith("/recognition")
        assert "files" in kwargs
        class R:
            def raise_for_status(self): pass
            def json(self): return {"text": "大家好"}
        return R()
    monkeypatch.setattr(httpx, "post", fake_post)
    assert QwenASRProvider("http://asr").transcribe(b"fake-audio") == "大家好"
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_asr.py -v`
Expected: 1 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/asr.py backend/tests/test_asr.py
git commit -m "feat: STT/TTS abstraction layer (Qwen3-ASR + dots.tts)"
```

---

### Task 10: 录音上传 + 转写流水线

**Files:**
- Create: `backend/app/routers/recordings.py`
- Create: `backend/app/tasks.py`
- Create: `backend/app/services/pipeline.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_recordings.py`

**Interfaces:**
- Produces: `POST /recordings/upload`（multipart，字段 `audio` + `project_id` + `scene`）、`GET /recordings/{id}/status`；`app.services.pipeline.process_recording(db, recording_id)`（后台调用）。
- Consumes: `Recording`、`ProcessingTask`、`asr`、`denoise`（Task 11 提供）、`note_gen`（Task 12 提供）。

> 注：pipeline 依赖 denoise/note_gen，本任务先实现「上传→转写」，去噪和笔记在 Task 11/12 补进 pipeline。为避免循环依赖，pipeline 的 `process_recording` 本任务先只做转写，后续任务增量扩展。

- [ ] **Step 1: schemas.py 追加**

```python
class RecordingStatus(BaseModel):
    id: int
    status: str
    transcript: str = ""
    note_id: int | None = None
```

- [ ] **Step 2: 写 services/pipeline.py（本任务：转写阶段）**

```python
from ..models import Recording, Note
from . import asr

def process_recording(db, recording_id: int) -> None:
    rec = db.get(Recording, recording_id)
    if not rec:
        return
    rec.status = "transcribing"
    db.commit()
    with open(rec.audio_path, "rb") as f:
        audio = f.read()
    text = asr.get_asr().transcribe(audio)
    rec.transcript = text
    rec.status = "transcribed"
    db.commit()
```

- [ ] **Step 3: 写 tasks.py（后台线程执行）**

```python
import threading
from .database import SessionLocal
from .services.pipeline import process_recording

def run_pipeline(recording_id: int):
    db = SessionLocal()
    try:
        process_recording(db, recording_id)
    finally:
        db.close()

def start_pipeline(recording_id: int):
    threading.Thread(target=run_pipeline, args=(recording_id,), daemon=True).start()
```

- [ ] **Step 4: 写 routers/recordings.py**

```python
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import Recording, User
from ..auth import require_role
from .. import tasks

router = APIRouter(prefix="/recordings", tags=["recordings"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
def upload(audio: UploadFile = File(...), project_id: int | None = Form(None), scene: str = Form("internal"), db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.wav")
    with open(path, "wb") as f:
        f.write(audio.file.read())
    rec = Recording(project_id=project_id, scene=scene, audio_path=path, author_id=user.id)
    db.add(rec); db.commit(); db.refresh(rec)
    tasks.start_pipeline(rec.id)
    return {"id": rec.id, "status": rec.status}

@router.get("/{rec_id}/status")
def status(rec_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    rec = db.get(Recording, rec_id)
    if not rec:
        return {"error": "not found"}
    return {"id": rec.id, "status": rec.status, "transcript": rec.transcript}
```

- [ ] **Step 5: 写 test_recordings.py（mock asr，验证上传后状态流转）**

```python
from app.services import asr as asr_module

def _token(client, username="tech1", role="tech"):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]

def test_upload_triggers_pipeline(client, monkeypatch):
    class FakeASR:
        def transcribe(self, audio_bytes):
            return "这是转写结果"
    monkeypatch.setattr(asr_module, "get_asr", lambda: FakeASR())
    t = _token(client)
    r = client.post("/recordings/upload", files={"audio": ("a.wav", b"fake", "audio/wav")}, data={"scene": "internal"}, headers={"token": t})
    assert r.status_code == 200
    assert r.json()["status"] in ("uploaded", "transcribing", "transcribed")
```

- [ ] **Step 6: 运行测试**

Run: `cd backend && python -m pytest tests/test_recordings.py -v`
Expected: passed（注意后台线程异步，断言只验状态在合法集合内）

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/recordings.py backend/app/tasks.py backend/app/services/pipeline.py backend/app/schemas.py backend/app/main.py backend/tests/test_recordings.py
git commit -m "feat: recording upload + async transcribe pipeline"
```

---

### Task 11: 去噪（Ollama 二分类）

**Files:**
- Create: `backend/app/services/denoise.py`
- Modify: `backend/app/services/pipeline.py`（转写后接去噪）
- Test: `backend/tests/test_denoise.py`

**Interfaces:**
- Produces: `app.services.denoise.denoise_transcript(transcript: str) -> str`（返回过滤后的干货文本）。
- Consumes: `app.services.llm.get_denoise_llm()`。

- [ ] **Step 1: 写 denoise.py**

```python
from .llm import get_denoise_llm

PROMPT = """你是会议记录清洗助手。下面是转写文本。请删除寒暄、重复、口水话、与主题无关的内容，保留有信息量的句子。直接输出清洗后的文本，不要解释。\n\n转写文本：\n{transcript}"""

def denoise_transcript(transcript: str) -> str:
    llm = get_denoise_llm()
    return llm.chat([{"role": "user", "content": PROMPT.format(transcript=transcript)}])
```

- [ ] **Step 2: pipeline.py 接去噪**

```python
from . import asr, denoise

# 在 transcribe 之后：
text = asr.get_asr().transcribe(audio)
rec.transcript = text
clean = denoise.denoise_transcript(text)
rec.transcript = clean  # 存清洗后文本
rec.status = "transcribed"
db.commit()
```

- [ ] **Step 3: 写 test_denoise.py（mock LLM）**

```python
from app.services import denoise as d

def test_denoise_calls_llm(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            assert "删除寒暄" in messages[0]["content"]
            return "清洗后"
    monkeypatch.setattr(d, "get_denoise_llm", lambda: FakeLLM())
    assert d.denoise_transcript("嗯，大家好，我们开始吧") == "清洗后"
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_denoise.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/denoise.py backend/app/services/pipeline.py backend/tests/test_denoise.py
git commit -m "feat: denoise transcript via Ollama"
```

---

### Task 12: 笔记整理（四块结构化）

**Files:**
- Create: `backend/app/services/note_gen.py`
- Modify: `backend/app/services/pipeline.py`（转写→去噪→笔记，写 Note）
- Test: `backend/tests/test_note_gen.py`

**Interfaces:**
- Produces: `app.services.note_gen.generate_note(transcript: str) -> dict`（返回 `{"summary", "points", "decisions", "todos"}` 四键，值均为 str）。
- Consumes: `app.services.llm.get_llm()`、`app.models.Note`。

- [ ] **Step 1: 写 note_gen.py**

```python
import json
from .llm import get_llm

PROMPT = """你是会议记录整理助手。请把下面的转写文本整理成结构化笔记，严格输出 JSON，包含四个字段：summary(一句话摘要)、points(分段要点)、decisions(达成的决策)、todos(待办/疑问)。不要输出 JSON 以外的内容。\n\n转写文本：\n{transcript}"""

def generate_note(transcript: str) -> dict:
    llm = get_llm()
    raw = llm.chat([{"role": "user", "content": PROMPT.format(transcript=transcript)}])
    # 容错：剥离可能的 markdown 代码块包裹
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    return {
        "summary": data.get("summary", ""),
        "points": data.get("points", ""),
        "decisions": data.get("decisions", ""),
        "todos": data.get("todos", ""),
    }
```

- [ ] **Step 2: pipeline.py 写 Note**

```python
from . import asr, denoise, note_gen
from ..models import Recording, Note

def process_recording(db, recording_id):
    rec = db.get(Recording, recording_id)
    if not rec:
        return
    rec.status = "transcribing"; db.commit()
    with open(rec.audio_path, "rb") as f:
        audio = f.read()
    text = asr.get_asr().transcribe(audio)
    rec.transcript = text
    clean = denoise.denoise_transcript(text)
    rec.transcript = clean
    rec.status = "noting"; db.commit()
    note_data = note_gen.generate_note(clean)
    note = Note(project_id=rec.project_id, scene=rec.scene, transcript=clean, author_id=rec.author_id, **note_data)
    db.add(note); db.commit(); db.refresh(note)
    rec.status = "done"; db.commit()
```

- [ ] **Step 3: 写 test_note_gen.py（mock LLM 返回 JSON）**

```python
import json
from app.services import note_gen as ng

def test_generate_note_parses_json(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return json.dumps({"summary": "s", "points": "p", "decisions": "d", "todos": "t"})
    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("随便什么转写")
    assert r == {"summary": "s", "points": "p", "decisions": "d", "todos": "t"}

def test_generate_note_strips_code_fence(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            return '```json\n{"summary":"s","points":"p","decisions":"d","todos":"t"}\n```'
    monkeypatch.setattr(ng, "get_llm", lambda: FakeLLM())
    r = ng.generate_note("x")
    assert r["summary"] == "s"
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_note_gen.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/note_gen.py backend/app/services/pipeline.py backend/tests/test_note_gen.py
git commit -m "feat: note generation (4-block structured JSON)"
```

---

### Task 13: 需求提炼（候选需求）

**Files:**
- Create: `backend/app/services/req_extract.py`
- Create: `backend/app/routers/notes.py`（笔记列表 + 触发提炼 + 候选确认）
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_req_extract.py`

**Interfaces:**
- Produces: `app.services.req_extract.extract_candidates(note_text: str) -> list[dict]`（每条 `{"title", "description", "source_ref"}`）；路由 `GET /notes`、`POST /notes/{id}/extract`（返回候选，不落库）、`POST /notes/{id}/confirm-requirements`（把人工确认后的候选落库为 draft）。
- Consumes: `app.services.llm.get_llm()`、`Requirement`、`Note`。

- [ ] **Step 1: 写 req_extract.py**

```python
import json
from .llm import get_llm

PROMPT = """你是需求分析师。请从下面的沟通笔记中提取客户潜在需求，输出 JSON 数组，每条包含 title(需求标题)、description(需求描述)、source_ref(引用原文原句，用于溯源)。只输出 JSON 数组，不要其他内容。\n\n笔记：\n{text}"""

def extract_candidates(note_text: str) -> list[dict]:
    llm = get_llm()
    raw = llm.chat([{"role": "user", "content": PROMPT.format(text=note_text)}]).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)
    return [{"title": x.get("title", ""), "description": x.get("description", ""), "source_ref": x.get("source_ref", "")} for x in data]
```

- [ ] **Step 2: schemas.py 追加**

```python
class CandidateRequirement(BaseModel):
    title: str
    description: str = ""
    source_ref: str = ""

class ConfirmRequirements(BaseModel):
    project_id: int | None = None
    customer_id: int | None = None
    candidates: list[CandidateRequirement]
```

- [ ] **Step 3: 写 routers/notes.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import Note, Requirement, User, ReqSource
from ..auth import require_role
from ..schemas import ConfirmRequirements
from ..services import req_extract

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/")
def list_notes(db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    return [{"id": n.id, "summary": n.summary, "scene": n.scene, "project_id": n.project_id} for n in db.query(Note).all()]

@router.post("/{note_id}/extract")
def extract(note_id: int, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    return req_extract.extract_candidates(note.transcript or note.points)

@router.post("/{note_id}/confirm-requirements")
def confirm(note_id: int, body: ConfirmRequirements, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    created = []
    for c in body.candidates:
        r = Requirement(
            title=c.title, description=c.description, source=ReqSource.discussion,
            source_ref=c.source_ref, project_id=body.project_id, customer_id=body.customer_id,
            author_id=user.id,
        )
        db.add(r); created.append(r)
    db.commit()
    return [{"id": r.id, "title": r.title} for r in created]
```

- [ ] **Step 4: 写 test_req_extract.py（mock LLM，验证候选解析 + 确认落库）**

```python
from app.services import req_extract as re

def test_extract_candidates(monkeypatch):
    class FakeLLM:
        def chat(self, messages):
            import json
            return json.dumps([{"title": "自动回复", "description": "客户想要自动回复", "source_ref": "客户说想要自动回复"}])
    monkeypatch.setattr(re, "get_llm", lambda: FakeLLM())
    r = re.extract_candidates("客户说想要自动回复")
    assert len(r) == 1
    assert r[0]["title"] == "自动回复"
    assert r[0]["source_ref"] == "客户说想要自动回复"
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_req_extract.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/req_extract.py backend/app/routers/notes.py backend/app/schemas.py backend/app/main.py backend/tests/test_req_extract.py
git commit -m "feat: requirement extraction (candidate + human confirm)"
```

---

### Task 14: 答疑 agent（检索 + 回流）

**Files:**
- Create: `backend/app/services/qa_service.py`
- Create: `backend/app/routers/qa.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_qa.py`

**Interfaces:**
- Produces: `app.services.qa_service.answer(question: str, db) -> dict`（返回 `{"answer", "source", "needs_human"}`）；路由 `POST /qa/ask`、`POST /qa/{id}/answer`（技术人员作答，回流知识库）。
- Consumes: `app.services.llm.get_llm()`、`Knowledge`、`QA`。

- [ ] **Step 1: 写 qa_service.py**

```python
from .llm import get_llm
from ..models import Knowledge

def _search_knowledge(db, question: str) -> Knowledge | None:
    # MVP 用关键词重叠做简单检索，后续可换向量检索
    words = set(question)
    best, best_score = None, 0
    for k in db.query(Knowledge).all():
        score = len(words & set(k.title + k.content))
        if score > best_score:
            best, best_score = k, score
    return best if best_score > 0 else None

def answer(db, question: str) -> dict:
    hit = _search_knowledge(db, question)
    if hit:
        return {"answer": hit.content, "source": hit.title, "needs_human": False}
    return {"answer": "", "source": "", "needs_human": True}
```

- [ ] **Step 2: schemas.py 追加**

```python
class QAAsk(BaseModel):
    question: str

class QAAnswerIn(BaseModel):
    answer: str
```

- [ ] **Step 3: 写 routers/qa.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import QA, Knowledge, User
from ..auth import require_role
from ..schemas import QAAsk, QAAnswerIn
from ..services import qa_service

router = APIRouter(prefix="/qa", tags=["qa"])

@router.post("/ask")
def ask(body: QAAsk, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech", "instructor"))):
    result = qa_service.answer(db, body.question)
    qa = QA(question=body.question, answer=result["answer"], status="answered" if not result["needs_human"] else "pending", author_id=user.id)
    db.add(qa); db.commit(); db.refresh(qa)
    return {"id": qa.id, **result}

@router.post("/{qa_id}/answer")
def answer_question(qa_id: int, body: QAAnswerIn, db: Session = Depends(get_session), user: User = Depends(require_role("admin", "tech"))):
    qa = db.get(QA, qa_id)
    if not qa:
        raise HTTPException(404, "问题不存在")
    qa.answer = body.answer
    qa.status = "answered"
    # 回流知识库
    k = Knowledge(title=qa.question[:50], content=body.answer, source="qa")
    db.add(k); db.flush()
    qa.knowledge_id = k.id
    db.commit()
    return {"id": qa.id, "status": qa.status}
```

- [ ] **Step 4: 写 test_qa.py**

```python
def _token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]

def test_ask_hits_knowledge(client):
    t = _token(client, "tech1", "tech")
    h = {"token": t}
    client.post("/knowledge/", json={"title": "什么是agent", "content": "agent是能自主执行任务的AI"}, headers=h)
    r = client.post("/qa/ask", json={"question": "什么是agent"}, headers=h)
    assert r.json()["needs_human"] == False
    assert "agent" in r.json()["answer"]

def test_ask_no_hit_marks_pending(client):
    i = _token(client, "inst1", "instructor")
    r = client.post("/qa/ask", json={"question": "完全不知道的问题xyz"}, headers={"token": i})
    assert r.json()["needs_human"] == True

def test_tech_answer_reflows_to_knowledge(client):
    t = _token(client, "tech1", "tech")
    h = {"token": t}
    qid = client.post("/qa/ask", json={"question": "如何部署agent"}, headers=h).json()["id"]
    client.post(f"/qa/{qid}/answer", json={"answer": "部署步骤是..."}, headers=h)
    r = client.get("/knowledge/", headers=h)
    assert any("如何部署" in k["title"] for k in r.json())
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_qa.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/qa_service.py backend/app/routers/qa.py backend/app/schemas.py backend/app/main.py backend/tests/test_qa.py
git commit -m "feat: QA agent (keyword retrieval + answer reflux)"
```

---

### Task 15: 数据备份导出

**Files:**
- Create: `backend/app/routers/backup.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_backup.py`

**Interfaces:**
- Produces: `GET /backup/export`（返回 JSON 全量数据，含用户/客户/项目/需求/笔记/知识库/答疑）。
- Consumes: 各 ORM 模型。

- [ ] **Step 1: 写 routers/backup.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_session
from ..models import User, Customer, Project, Requirement, Note, Knowledge, QA
from ..auth import require_role

router = APIRouter(prefix="/backup", tags=["backup"])

def _dump(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@router.get("/export")
def export(db: Session = Depends(get_session), user=Depends(require_role("admin"))):
    return {
        "users": [_dump(u) for u in db.query(User).all()],
        "customers": [_dump(c) for c in db.query(Customer).all()],
        "projects": [_dump(p) for p in db.query(Project).all()],
        "requirements": [_dump(r) for r in db.query(Requirement).all()],
        "notes": [_dump(n) for n in db.query(Note).all()],
        "knowledge": [_dump(k) for k in db.query(Knowledge).all()],
        "qa": [_dump(q) for q in db.query(QA).all()],
    }
```

- [ ] **Step 2: 写 test_backup.py（仅 admin 可导出）**

```python
def _token(client, username, role):
    client.post("/auth/register", json={"username": username, "password": "pw", "role": role})
    return client.post("/auth/login", json={"username": username, "password": "pw"}).json()["token"]

def test_export_requires_admin(client):
    t = _token(client, "tech1", "tech")
    r = client.get("/backup/export", headers={"token": t})
    assert r.status_code == 403
    a = _token(client, "admin1", "admin")
    r2 = client.get("/backup/export", headers={"token": a})
    assert r2.status_code == 200
    assert "requirements" in r2.json()
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_backup.py -v`
Expected: 1 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/backup.py backend/app/main.py backend/tests/test_backup.py
git commit -m "feat: data backup/export (admin only)"
```

---

### Task 16: 前端登录 + 工作台框架

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/App.tsx`（路由 + 鉴权守卫）

**Interfaces:**
- Produces: `apiFetch(path, options)`（自动带 token、401 跳登录）、`AuthContext`（`token`、`role`、`login()`、`logout()`）。
- Consumes: 后端 `/auth/login`、`/auth/register`。

- [ ] **Step 1: 写 api/client.ts**

```typescript
const BASE = "http://127.0.0.1:8000";

export function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("token");
  return fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { token } : {}),
      ...(options.headers || {}),
    },
  }).then((r) => {
    if (r.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return r.json();
  });
}
```

- [ ] **Step 2: 写 context/AuthContext.tsx**

```tsx
import React, { createContext, useContext, useState } from "react";
import { apiFetch } from "../api/client";

interface AuthCtx { token: string | null; role: string | null; login: (u: string, p: string) => Promise<void>; logout: () => void; }
const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [role, setRole] = useState(localStorage.getItem("role"));
  async function login(u: string, p: string) {
    const r = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ username: u, password: p }) });
    localStorage.setItem("token", r.token);
    localStorage.setItem("role", r.role);
    setToken(r.token); setRole(r.role);
  }
  function logout() { localStorage.removeItem("token"); localStorage.removeItem("role"); setToken(null); setRole(null); }
  return <Ctx.Provider value={{ token, role, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
```

- [ ] **Step 3: 写 Login.tsx + Dashboard.tsx + App.tsx（路由守卫）**

```tsx
// pages/Login.tsx
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const [u, setU] = useState(""); const [p, setP] = useState("");
  async function submit() { await login(u, p); window.location.href = "/"; }
  return (
    <div>
      <input placeholder="用户名" value={u} onChange={(e) => setU(e.target.value)} />
      <input placeholder="密码" type="password" value={p} onChange={(e) => setP(e.target.value)} />
      <button onClick={submit}>登录</button>
    </div>
  );
}
```

```tsx
// pages/Dashboard.tsx
import { useAuth } from "../context/AuthContext";
export default function Dashboard() {
  const { role, logout } = useAuth();
  return <div>欢迎，角色：{role} <button onClick={logout}>退出</button></div>;
}
```

```tsx
// App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

function Guard({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Guard><Dashboard /></Guard>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

- [ ] **Step 4: 手动验证**

Run: 后端 `cd backend && uvicorn app.main:app --port 8000`；前端 `cd frontend && npm run dev`。浏览器打开 `localhost:5173`，用之前注册的账号登录，登录后跳 Dashboard 显示角色。

Expected: 登录成功跳转，刷新仍保持登录态（localStorage token）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api frontend/src/context frontend/src/pages frontend/src/App.tsx
git commit -m "feat: frontend auth + dashboard frame"
```

---

### Task 17: 前端 项目/需求界面

**Files:**
- Create: `frontend/src/pages/Projects.tsx`
- Create: `frontend/src/pages/Requirements.tsx`
- Modify: `frontend/src/App.tsx`（加路由）

**Interfaces:**
- Consumes: `/customers`、`/projects`、`/requirements`、`/requirements/{id}/transition`。

- [ ] **Step 1: 写 Projects.tsx（列表 + 新建客户/项目）**

```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

export default function Projects() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  async function load() {
    setCustomers(await apiFetch("/customers/"));
    setProjects(await apiFetch("/projects/"));
  }
  useEffect(() => { load(); }, []);
  async function addCustomer() {
    const name = prompt("客户名称"); if (!name) return;
    await apiFetch("/customers/", { method: "POST", body: JSON.stringify({ name }) });
    load();
  }
  async function addProject() {
    const name = prompt("项目名称"); if (!name) return;
    const customer_id = Number(prompt("客户ID"));
    await apiFetch("/projects/", { method: "POST", body: JSON.stringify({ name, customer_id }) });
    load();
  }
  return (
    <div>
      <h2>项目</h2>
      <button onClick={addCustomer}>新建客户</button>
      <button onClick={addProject}>新建项目</button>
      <ul>{projects.map((p) => <li key={p.id}>{p.name}（状态：{p.status}）</li>)}</ul>
    </div>
  );
}
```

- [ ] **Step 2: 写 Requirements.tsx（列表 + 状态流转按钮）**

```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

const NEXT: Record<string, { label: string; to: string }[]> = {
  draft: [{ label: "提交评审", to: "pending_review" }],
  pending_review: [
    { label: "可行", to: "feasible" },
    { label: "信息待补充", to: "info_needed" },
    { label: "方案待调整", to: "plan_needed" },
    { label: "不可行", to: "infeasible" },
  ],
  info_needed: [{ label: "重新提交评审", to: "pending_review" }],
  plan_needed: [{ label: "重新提交评审", to: "pending_review" }],
  infeasible: [{ label: "重新评估", to: "pending_review" }],
  feasible: [{ label: "开始开发", to: "in_dev" }],
  in_dev: [{ label: "标记交付", to: "delivered" }],
};

export default function Requirements() {
  const { role } = useAuth();
  const [items, setItems] = useState<any[]>([]);
  async function load() { setItems(await apiFetch("/requirements/")); }
  useEffect(() => { load(); }, []);
  async function transition(id: number, to: string) {
    await apiFetch(`/requirements/${id}/transition`, { method: "POST", body: JSON.stringify({ to }) });
    load();
  }
  return (
    <div>
      <h2>需求</h2>
      <ul>
        {items.map((r) => (
          <li key={r.id}>
            {r.title}（{r.status}）
            {(role === "tech" || role === "admin") && (NEXT[r.status] || []).map((a) => (
              <button key={a.to} onClick={() => transition(r.id, a.to)}>{a.label}</button>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: App.tsx 加路由 + Dashboard 加导航链接**

```tsx
import Projects from "./pages/Projects";
import Requirements from "./pages/Requirements";
// Routes 内加：
<Route path="/projects" element={<Guard><Projects /></Guard>} />
<Route path="/requirements" element={<Guard><Requirements /></Guard>} />
```

- [ ] **Step 4: 手动验证**

Expected: 登录后能建客户/项目；需求能走完整状态流转（草稿→评审→可行/调整/不可行→…），讲师登录看不到流转按钮。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Projects.tsx frontend/src/pages/Requirements.tsx frontend/src/App.tsx
git commit -m "feat: frontend projects + requirements with state transitions"
```

---

### Task 18: 前端 录音 + 笔记界面

**Files:**
- Create: `frontend/src/components/Recorder.tsx`
- Create: `frontend/src/pages/Notes.tsx`
- Create: `frontend/src/components/NoteEditor.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `/recordings/upload`（FormData）、`/recordings/{id}/status`、`/notes`、`/notes/{id}/extract`、`/notes/{id}/confirm-requirements`。

- [ ] **Step 1: 写 Recorder.tsx（MediaRecorder 录音 + 上传）**

```tsx
import { useRef, useState } from "react";
import { apiFetch } from "../api/client";

export default function Recorder() {
  const [recording, setRecording] = useState(false);
  const [scene, setScene] = useState("internal");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    chunksRef.current = [];
    rec.ondataavailable = (e) => chunksRef.current.push(e.data);
    rec.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const fd = new FormData();
      fd.append("audio", blob, "rec.webm");
      fd.append("scene", scene);
      const r = await apiFetch("/recordings/upload", { method: "POST", body: fd });
      alert("已上传，转写处理中，ID=" + r.id);
    };
    rec.start();
    recorderRef.current = rec;
    setRecording(true);
  }
  function stop() { recorderRef.current?.stop(); setRecording(false); }

  return (
    <div>
      <select value={scene} onChange={(e) => setScene(e.target.value)}>
        <option value="internal">内部沟通</option>
        <option value="discussion">客户需求</option>
      </select>
      <button onClick={recording ? stop : start}>{recording ? "停止录音" : "开始录音"}</button>
    </div>
  );
}
```

> 注：`apiFetch` 的 `Content-Type` 需对 FormData 例外。修改 `client.ts`：当 `body instanceof FormData` 时不设 `Content-Type`。

- [ ] **Step 2: 写 Notes.tsx（笔记列表 + 触发提炼）**

```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import NoteEditor from "../components/NoteEditor";

export default function Notes() {
  const [notes, setNotes] = useState<any[]>([]);
  async function load() { setNotes(await apiFetch("/notes/")); }
  useEffect(() => { load(); }, []);
  return (
    <div>
      <h2>笔记</h2>
      <ul>
        {notes.map((n) => (
          <li key={n.id}>
            {n.summary || n.id}（{n.scene}）
            <NoteEditor noteId={n.id} />
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: 写 NoteEditor.tsx（提炼候选 + 编辑 + 确认落库）**

```tsx
import { useState } from "react";
import { apiFetch } from "../api/client";

export default function NoteEditor({ noteId }: { noteId: number }) {
  const [candidates, setCandidates] = useState<any[]>([]);
  async function extract() { setCandidates(await apiFetch(`/notes/${noteId}/extract`, { method: "POST" })); }
  async function confirm() {
    await apiFetch(`/notes/${noteId}/confirm-requirements`, { method: "POST", body: JSON.stringify({ candidates }) });
    alert("已入库");
    setCandidates([]);
  }
  return (
    <div>
      <button onClick={extract}>提炼需求</button>
      {candidates.map((c, i) => (
        <div key={i}>
          <input value={c.title} onChange={(e) => setCandidates(candidates.map((x, j) => j === i ? { ...x, title: e.target.value } : x))} />
          <button onClick={() => setCandidates(candidates.filter((_, j) => j !== i))}>删除</button>
        </div>
      ))}
      {candidates.length > 0 && <button onClick={confirm}>确认入库</button>}
    </div>
  );
}
```

- [ ] **Step 4: 修改 client.ts（FormData 例外）**

```typescript
export function apiFetch(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem("token");
  const isForm = options.body instanceof FormData;
  return fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(token ? { token } : {}),
      ...(options.headers || {}),
    },
  }).then((r) => { if (r.status === 401) { localStorage.removeItem("token"); window.location.href = "/login"; } return r.json(); });
}
```

- [ ] **Step 5: App.tsx 加路由（/notes）+ Dashboard 导航**

- [ ] **Step 6: 手动验证**

Expected: 录音→上传→后端转写（需真实 ASR 或 mock）→笔记出现→提炼出候选→编辑后确认→需求库出现草稿。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components frontend/src/pages/Notes.tsx frontend/src/api/client.ts frontend/src/App.tsx
git commit -m "feat: frontend recorder + notes + requirement extraction"
```

---

### Task 19: 前端 知识库 + 答疑界面

**Files:**
- Create: `frontend/src/pages/Knowledge.tsx`
- Create: `frontend/src/pages/QA.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `/knowledge`、`/qa/ask`、`/qa/{id}/answer`。

- [ ] **Step 1: 写 Knowledge.tsx（列表 + 技术新建）**

```tsx
import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Knowledge() {
  const { role } = useAuth();
  const [items, setItems] = useState<any[]>([]);
  async function load() { setItems(await apiFetch("/knowledge/")); }
  useEffect(() => { load(); }, []);
  async function add() {
    const title = prompt("标题"); const content = prompt("内容");
    if (!title || !content) return;
    await apiFetch("/knowledge/", { method: "POST", body: JSON.stringify({ title, content }) });
    load();
  }
  return (
    <div>
      <h2>知识库</h2>
      {(role === "tech" || role === "admin") && <button onClick={add}>新建知识条目</button>}
      <ul>{items.map((k) => <li key={k.id}>{k.title}</li>)}</ul>
    </div>
  );
}
```

- [ ] **Step 2: 写 QA.tsx（提问 + 技术作答）**

```tsx
import { useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function QA() {
  const { role } = useAuth();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<any>(null);
  async function ask() {
    setResult(await apiFetch("/qa/ask", { method: "POST", body: JSON.stringify({ question: q }) }));
  }
  async function answer(id: number) {
    const ans = prompt("输入回答");
    if (!ans) return;
    await apiFetch(`/qa/${id}/answer`, { method: "POST", body: JSON.stringify({ answer: ans }) });
    alert("已回答并回流知识库");
  }
  return (
    <div>
      <h2>答疑</h2>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="输入你的问题" />
      <button onClick={ask}>提问</button>
      {result && (
        <div>
          {result.needs_human
            ? <p>暂无答案，已转技术人员（问题ID={result.id}）</p>
            : <p>{result.answer}</p>}
          {result.needs_human && (role === "tech" || role === "admin") && <button onClick={() => answer(result.id)}>作答</button>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: App.tsx 加路由（/knowledge、/qa）+ Dashboard 导航**

- [ ] **Step 4: 手动验证**

Expected: 讲师提问命中知识库直接得答案；未命中显示"转技术"；技术作答后知识库多一条回流条目。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Knowledge.tsx frontend/src/pages/QA.tsx frontend/src/App.tsx
git commit -m "feat: frontend knowledge + QA"
```

---

## 收尾：集成验证

- [ ] 后端全量测试：`cd backend && python -m pytest tests/ -v`（全部通过）
- [ ] 前端 `npm run build` 无 TS 报错
- [ ] 端到端手动走查：注册两个账号（tech + instructor）→ 技术建客户/项目 → 讲师录音上传 → 笔记生成 → 提炼需求 → 技术评审流转 → 讲师答疑 → 技术作答回流 → admin 导出备份
