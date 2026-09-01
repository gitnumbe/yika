# AGENTS.md

本文件是 AI 编码代理（以及接手本项目的新工程师）在 `D:\projections\yika` 工作时的指导文件。开始任何改动前先读这里。

## 项目如何"记住自己"

本项目遵循「文档即真相」，**不要靠 AI 代理的记忆来记住项目**。改动前按顺序读：

1. 本文档（快速上手 + 环境陷阱）
2. `docs/README.md`（文档导航，索引全部决策）
3. `docs/business-rules.md`（业务规则：权限矩阵、状态机、防幻觉铁律）
4. `docs/module-dependencies.md`（模块依赖图 + 影响分析：改动前必读，防止改一处坏全局）
5. `docs/change-budget.md`（变更预算：标注冻结层/受控层/自由层，防止顺手重构）
6. `docs/testing-strategy.md`（三层次测试：单元/关联回测/业务闭环，编译通过≠业务正确）
7. `docs/decisions/*.md`（每个核心功能**为什么这么设计**，含备选方案为何被否）

**规则**：改代码前先读对应决策文档；发现决策过时，先更新 `decisions/*.md`（标记"已变更+原因"）再改代码；做了新架构决策就新增一个 `decisions/NN-*.md`；**改动任何模块前，先按 `module-dependencies.md` 做影响分析**（判断影响等级 + 回归范围）；**改动前先按 `change-budget.md` 声明预算**（哪些能动、哪些是冻结层不能顺手改）。

## 项目是什么

「组内队员协作 Agent」——一个**纯内部**的桌面协作工具，服务两类角色：**技术人员** 和 **讲师**。业务流程：讲师学习 AI 知识 → 给客户培训 → 三方（讲师/技术/客户）沟通挖需求 → 需求评审（技术排不可行项）→ 技术开发交付。

设计文档：`docs/superpowers/specs/2026-08-25-team-collab-agent-design.md`
实现计划：`docs/superpowers/plans/2026-08-25-team-collab-agent-mvp.md`

**改代码前先读这两份文档**，它们是最新的需求与任务权威。

## 技术栈（生产级基线 v2.0 · 权威见 Obsidian `yika/开发文档.md`）

- **后端**：Python 3.11 + FastAPI + SQLAlchemy 2.0 + **Alembic 迁移** + **PostgreSQL 16（生产）/ SQLite（开发）** + PyJWT + bcrypt
- **前端**：Electron + React 18 + TypeScript + Vite + react-router-dom
- **部署**：Docker Compose + Nginx(TLS 反向代理) + Prometheus/Grafana 监控 + 每日备份（见开发文档 §11）
- **AI**（走抽象层，可切换；模型实例只登记在 `.env` 与开发文档 §4.0 基线表，正文一律用逻辑名）：
  - 大模型：内网 OpenAI 兼容接口（当前实例 `deepseek-v4-flash-vision-exp`），配置在 `.env` 的 `LLM_*`
  - 去噪小模型：本机 Ollama（当前 `qwen3:4b-instruct`），配置在 `OLLAMA_*`
  - **STT**：Qwen3-ASR-1.7B（本地自建服务 `ASR_BASE_URL`，`POST /v1/transcribe`）——决策 09，替代 FunASR
  - **TTS**：dots.tts-mf（本地自建服务 `TTS_BASE_URL`，`POST /v1/speak`）——决策 09，笔记/答疑朗读

## 目录结构

```
backend/
  app/
    main.py          # FastAPI 入口，挂所有路由 + 建表
    config.py        # pydantic-settings，读 .env（Settings 单例）
    database.py      # engine + SessionLocal + Base + get_session
    models.py        # 全部 ORM 模型（含枚举 Role/ReqStatus/ProjectStatus/ReqSource）
    auth.py          # JWT：hash_password / create_token / get_current_user / require_role
    state_machine.py # 需求状态机（纯函数，无 IO）
    schemas.py       # Pydantic 请求/响应模型
    routers/         # auth/customers/projects/requirements/knowledge/qa/backup
    services/        # llm.py / asr.py / tts.py / qa_service.py（抽象层 + 业务服务）
    audit.py         # 审计日志（生产 §10.3）
  alembic/           # 数据库迁移（生产必要）
  tests/             # pytest，conftest.py 用内存 SQLite + TestClient
  requirements.txt
frontend/
  electron/main.js   # Electron 主进程
  src/
    api/client.ts    # apiFetch：自动带 token，401 跳登录
    context/AuthContext.tsx
    pages/           # Login/Dashboard/Projects/Requirements/Knowledge/QA
deploy/
  docker-compose.yml # 生产编排（backend/worker/postgres/redis/stt/tts/nginx/monitoring）
  nginx.conf
```

## 核心业务约定（改代码必须遵守）

### 角色与权限

角色枚举：`admin` / `tech`（技术）/ `instructor`（讲师）。权限矩阵见设计文档 §2。

**关键权限边界**（后端用 `require_role` 强制，别在前端放宽）：
- 需求流转（transition）：仅 `admin`/`tech`；讲师只能看
- 知识库写入：仅 `admin`/`tech`；讲师只读
- 备份导出：仅 `admin`
- 答疑作答：仅 `admin`/`tech`

### 需求状态机（state_machine.py）

状态：`draft → pending_review → feasible → in_dev → delivered`，以及
`pending_review → info_needed/plan_needed/infeasible`，`info_needed/plan_needed/infeasible → pending_review`。

- `info_needed` = 信息待补充（返讲师）
- `plan_needed` = 方案待调整（返技术）
- `infeasible` = 不可行（归档，可「重新评估」回到 pending_review）

**非法流转会抛 ValueError**（router 转成 400）。改状态机必须同步改 `tests/test_state_machine.py`。

### 防幻觉铁律（贯穿所有 agent）

**LLM 只产「候选/建议」，任何落库决策由人确认。** 需求提炼产出只进候选区，人工确认后才成 `draft`。这条铁律写进了设计文档，实现任何 agent 时不要破坏它。

### 数据模型多用户

所有数据从第一天就是多用户的（挂 `author_id` / `user_id`），因为将来要迁到公司服务器多人协作。**不要**引入任何单用户假设。

## 开发命令

后端（在 `backend/` 目录）：

```powershell
# 激活虚拟环境（首次：python -m venv .venv && .\.venv\Scripts\python.exe -m pip install -r requirements.txt）
.\.venv\Scripts\python.exe -m pytest tests/ -v   # 跑测试
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010   # 启动（见下方端口注意）
```

前端（在 `frontend/` 目录）：

```powershell
npm install
npm run dev      # Vite 开发服务器（端口 5173）
npm run build    # tsc + vite build（提交前必须通过）
```

## 环境陷阱（务必注意）

1. **端口 8000 被占用**：本机 8000 端口被另一个旧后端（`backend.main:create_app`，PID 15876）占用。我们的前端 `client.ts` 默认连 `127.0.0.1:8000`。本地启动后端时用 `--port 8010`（或先解决端口冲突），并确保前端 BASE 一致。
2. **PowerShell 发中文 JSON 会乱码**：用 `Invoke-RestMethod` 传中文 body 会编码错误。验证中文接口请用 Python + httpx（参考 `backend/e2e_check.py` 的模式，该文件已删，但模式要记住），或直接用 pytest。
3. **AI 端点依赖**：`services/llm.py`、`services/asr.py`、`services/tts.py` 的单元测试用 mock httpx，不依赖真实端点。录音流水线（Task 10-13）和真实联调需要 STT（Qwen3-ASR）、TTS（dots.tts）、内网大模型、Ollama 就绪。写这些部分的代码时用 mock 测试锁逻辑，真实联调单独做（STT/TTS 本地服务 `http://127.0.0.1:8051/8052` 起）。
4. **音频格式**：前端 MediaRecorder 产出 webm/opus，Qwen3-ASR 要 16kHz 单声道 WAV。中间必须 ffmpeg 转码（`-ar 16000 -ac 1`）。这是录音流水线的已知坑。
5. **SQLite 测试库**：跑 pytest 会在 `backend/` 生成 `test.db`，已被 `.gitignore` 忽略（`*.db`），不要手动提交它。
6. **本机无 NVIDIA GPU**（Intel Arc 130T），STT/TTS/Ollama 都只能 CPU 跑——功能可用，但**吞吐受限**；生产部署到内网 GPU 服务器（开发文档 §3.4）。
7. **模型下载**：ASR 权重在 `D:/models/yika/asr/qwen3-asr-1.7b`（已就绪）；TTS 权重在 `D:/models/yika/tts/dots-tts-mf`（见下方注意）。下载需 `HF_ENDPOINT=https://hf-mirror.com`；若遇 xet 401，加 `export HF_HUB_DISABLE_XET=1` 走传统 HTTP。

## 提交规范

- 每个任务独立 commit，message 用 `type: 中文描述`（如 `feat: ...`、`chore: ...`、`docs: ...`）
- 提交前必跑：后端 `pytest tests/`，前端 `npm run build`
- 用 `git status` 确认无未提交的 `*.db` 或 `.env`
