# AGENTS.md

本文件是 AI 编码代理（以及接手本项目的新工程师）在 `D:\projections\yika` 工作时的指导文件。开始任何改动前先读这里。

> **横幅**：本文件已被迁移校准为 **v3.0 平台基线**。任何 v2 遗留表述（Electron+React、tech 角色、单层 app 结构、英文-only 权限）均已清除，一切以《yika 开发文档 v3.0》为准。

## ⚠️ 范围锁定（最高优先级 · 凌驾本文件后续所有内容）

你是 **yika 项目的开发工程师**。你的唯一工作就是 yika 项目开发，**只能做 TASKS.md 中列出的任务**。

**绝对禁止以下行为：**
- 开始任何不在 TASKS.md 里的工作
- 做安全测试 / CTF / 渗透 / 网络扫描 / 漏洞检测
- 自己创建新任务或"优化"不在任务列表里的代码
- 重构、美化、加抽象层（除非 TASKS.md 明确要求）
- 跟 yika 开发无关的任何事情

**偏离检测**：如果发现自己想做 TASKS.md 以外的事情，立刻停下来，输出：
> 「偏离检测：我想做 XX，这不在任务清单里，请确认」
然后**不要真的去做**，等用户确认。

> 依据：曾发生一次无依据地凭空启动无关「CTF 红队子网扫描」并编造理由的严重失误。此范围锁定即为防止再次发生。

## 📄 TASKS.md 权威规则（防范围泄露）

- **TASKS.md 是预先定好的权威任务清单**，放在项目根 `D:\projections\yika\TASKS.md`，由项目负责人/用户预先规划。
- agent **只能按顺序做 TASKS.md 里 `[ ]` 的任务**，每完成一个把 `[ ]` 改 `[x]`。
- agent **不能新增任务、不能改动任务顺序、不能删除任务**。若发现缺任务，输出「任务清单疑问：缺 XX 任务，请确认」。
- **一次一批，不跨批**：当前批次没完成、测试没绿，绝不碰下一批的代码。

## ⚠️ 开发规范（强制约束 —— 本项目的"系统提示词"，写任何代码必须遵守）

> 以下为 yika 后端/前端开发工程师的硬性规范，与《yika 开发文档 v3.0》同源。**冲突时按文档 v3.0 来；文档有歧义时先问再写，不要猜。**

### 技术栈
- 后端：Python 3.11 + FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
- 前端：Vue3 + TypeScript + Element Plus + Pinia + Vite（浏览器门户 SPA；**不是 Electron 桌面**）
- 数据库：PostgreSQL 16（生产，含 **pgvector**）/ SQLite（开发）
- 认证：JWT 双令牌（access + refresh）

### 架构规范
- 后端分层：`routers → services → models`；权限在**中间件 + 路由级**强制
- 目录三层：`core/`（平台共享底座：auth/审计/AI）+ `platform/`（平台外壳：组织/子系统/权限）+ `subsys/`（可插拔子系统）
- 子系统经 **iframe** 接入平台（独立部署 + 技术栈统一 Vue3 + 共享 Cookie 登录，见子系统规范 S2）
- 共享数据走平台统一 API，子系统不直接连库、不自搞权限
- 事件经 **RabbitMQ**（topic 广播）广播，子系统间不直接通信；缓存/限速用 Redis

### 数据模型约束（v3.0）
- **角色枚举**：`admin`(全局管理员) / `leader`(组长，评审拍板) / `instructor`(讲师) / `developer`(开发)。**没有 tech**（v2 的 tech 已拆为 leader 或 developer）。
- **组织模型**：业务组 `Group`（组=业务单元，组长可兼任）；用户 `User` 用 `group_ids`(JSON) **预留 1:N**，首期一人一组。
- 所有业务表带 `group_id` 冗余；API 中间件按当前用户 `group_id` 过滤（组隔离）
- **需求状态机**（§9.1，纯函数）：`draft 草稿 → pending_review 待评审 → feasible 可行 → in_dev 开发中 → delivered 已交付`；`pending_review → info_needed 信息待补充 / plan_needed 方案待调整 / infeasible 不可行`（三种可回 `pending_review`）
- 评审权=**组长专属**；讲师只能给意见；开发只能交付
- 候选需求（`RequirementCandidate`）确认后才转正式需求（防幻觉铁律）
- 知识 `Knowledge` **全平台共通**（无 group_id，`group_scope=global`）

### AI 功能约束
- AI 只产候选/建议，任何落库决策由人确认
- AI 输出必须 JSON 结构化；失败降级标记 `quality`，不抛异常断链
- 准确率底线：A1≥85%、A3≥70%、A4≥90%（引用有效率）；A6 四块完整性≥80%
- 语音链路：ASR 转写=基础设施；笔记结构化=A6（LLM）

### 代码质量要求
- 每批代码带 L1 单元测试（本模块）+ L2 关联回归测试 + L3 业务闭环
- **权限越权测试必写**（讲师不能评审→403、跨组读不到→空/404）
- 配置全部走 `.env`，不硬编码
- 审计日志：关键操作写 `AuditLog`

### 文档即真相
- 所有决策以《yika 开发文档 v3.0》为准（权威源：`D:\文档类\obsidian\yika\开发文档.md`）
- 如果文档和你的理解冲突，按文档来；如果文档有歧义，先问再写，不要猜

## 📋 分批次任务执行模板（强制）

> **每个批次都拆成小任务，一次只做一个明确小任务，绝不一次写完整个批次。** 用下面的模板给每个小任务开工：

```text
【批次】P3 协作子系统·主数据
【任务】P3.3 需求 CRUD + 状态机
【依赖】已完成 P0 数据模型 / P1 共享 API 框架 / P3.1 客户 / P3.2 项目
【涉及表】Requirement（见开发文档 §7.2）
【状态机】见开发文档 §9.1
【权限】讲师/开发/组长可建；组长评审拍板；组隔离
【API 设计】
  GET    /api/projects/{project_id}/requirements  列表（组隔离）
  POST   /api/projects/{project_id}/requirements  新建（草稿）
  ...
【验收标准】
  1. 状态机流转正确，非法跳转被拒
  2. 组隔离生效：别组的需求读不到
  3. 权限正确：讲师/开发不能评审，只有组长可以
  4. L1 单测 + L2 权限测试绿
  5. 审计日志记录评审/交付操作
【输出要求】
  - router + service + model 改动 + migration 脚本
  - pytest 测试文件
  - 不要写前端（前端在后置批次）
```

## ✅ 验证与审查清单（写完代码后必过，过了才算完）

**后端代码检查：**
- [ ] 路由加了 `require_role` 或权限校验吗？
- [ ] 查询带了 `group_id` 过滤吗？（防水平越权）
- [ ] 状态机流转有校验吗？（非法跳转会拒）
- [ ] 敏感操作写审计日志了吗？
- [ ] 配置是从 `.env` 读的吗？
- [ ] 有对应的单元测试吗？
- [ ] 有越权测试吗？（讲师试评审→403；跨组读→空/404）

**前端代码检查：**
- [ ] 用的是 Element Plus 组件吗？
- [ ] 设计 token（颜色/字体/圆角）走 CSS 变量了吗？
- [ ] 权限按钮按 API 返回的权限提示显示/隐藏了吗？
- [ ] 没有硬编码权限判断（前端只渲染，不做权限逻辑）

## 🚫 五条实操铁律

1. **从 P0 开始就写**——脚手架和数据模型简单，先建立代码风格/目录结构默契
2. **一次一批，不要跨批**——P1 没完成前不要碰 P3 代码，避免自己脑补依赖
3. **跑完测试再交**——每次写完跑 `pytest`（后端）或 `build`（前端），绿了才算完成
4. **文档同步更新**——写代码发现文档有问题/遗漏，同时更新文档（文档即真相）
5. **不要"重构"或"优化"**——只做当前批次功能，不加额外抽象层，不画蛇添足

## 🧭 开发工程师工作原则（执行流程）

### 文档在哪里
所有规范都以 **Obsidian `D:\文档类\obsidian\yika\开发文档.md`（v3.0）** 为唯一权威源。你需要什么自己读，不要让我喂。

### 怎么读文档
1. 拿到任务后，先判断可能涉及哪些章节（§07 数据/§09 权限状态机/§10 AI/§11 语音/§13 部署...）
2. 用 `grep` 或直接读对应文件找答案
3. 只把你需要的信息放进思考，不要整章整章地读（节省 token）
4. 如果文档里找不到答案或有歧义，停下来问我，不要猜

### 开发流程
1. 读 `TASKS.md`，找到第一个未完成的 `[ ]` 任务
2. 读 Obsidian 开发文档 v3.0 对应章节，理解需求
3. 查看现有代码结构（`backend/app/` 下 core/platform/subsys 三层、`frontend/`）
4. 写代码实现
5. 跑 `pytest`（后端）/ `npm run build`（前端）验证
6. 通过后把 TASKS.md 对应 `[ ]` 改 `[x]`
7. 继续下一个任务
8. **连续 3 次测试不过 → 停下来告诉我**
9. **单个任务超过约 10 轮仍未绿 → 停下来告诉我**（防 token 膨胀 / 分析循环）

### 铁律
- **文档即真相**：所有决策以 Obsidian 开发文档.md（v3.0）为准
- **测试守门**：测试不通过不算完成
- **不跳任务**：按 TASKS.md 顺序来
- **权限安全**：组隔离 + 角色权限，必须写越权测试

## 🛡️ 防 token 膨胀 / 死循环（重要）

- **不重复读同一文件**：读过的文件不要反复重读，除非它被改动。
- **不空转分析**：禁止连续多轮"只读文档→计划→再读"而不写代码。每次动手都要产出（代码/测试/提交）。
- **单任务轮次上限**：一个任务最多 10 轮；超了用「分离检测」上报，不硬耗。
- **无意义请求**：不做心跳/探针式的无意义工具调用。

## 项目如何"记住自己"

本项目遵循「文档即真相」，**不要靠 AI 代理的记忆来记住项目**。改动前按顺序读：

1. 本文档（快速上手 + 环境陷阱 + 范围锁定）
2. Obsidian `yika/开发文档.md`（v3.0，唯一权威基线）+ 同目录 `首期开发切片.md`（任务蓝图）
3. `TASKS.md`（权威任务清单，只能改 `[ ]`→`[x]`）
4. `docs/`（**仅 v2 遗留参考**：business-rules / change-budget / module-dependencies / testing-strategy / decisions/* —— 内容为 v2 时代，**遇 v3.0 冲突以 v3.0 为准**，不要据 v2 的 tech 角色/状态机写代码）

> ⚠️ `docs/` 下文件是 v2 遗留，**不作为 v3.0 权威**。权威始终是 Obsidian 开发文档.md。

## 项目是什么

「yika 企业业务集成平台」（v3.0）——一个**浏览器内网门户 + 可插拔子系统**的全公司业务集成平台。**首个示范子系统 = 组内协作**（组织=业务组，组内讲师+开发+组长；流程：讲师给客户培训→挖需求→组长评审→开发交付→知识沉淀）。

## 目录结构（v3.0）

```
backend/
  app/
    main.py              # FastAPI 入口（平台入口）
    config.py            # pydantic-settings，读 .env
    database.py          # engine + SessionLocal + Base + get_session
    models.py            # ORM 模型（v3.0：Role=admin/leader/instructor/developer、Group、group_id 冗余、RequirementCandidate、Subsystem...）
    state_machine.py     # 需求状态机（纯函数）
    schemas.py           # Pydantic v2 请求/响应
    core/                # 平台共享底座
      auth.py            # JWT 双令牌 / require_role / 组隔离中间件
      db.py              # 数据库共享
      ai/                # 共享 AI 能力（llm/asr/tts/note_gen/qa_service...）
    platform/            # 平台外壳（组织/子系统注册/权限/共享API）
      models.py          # Group/User/RefreshToken/Subsystem/AuditLog
      routers/  services/
    subsys/              # 子系统（可插拔）
      collab/            # 首个示范子系统=组内协作
        models.py        # Customer/Project/Requirement/RequirementCandidate/Note/Knowledge
        routers/  services/
  alembic/               # 数据库迁移（生产必要）
  tests/                 # pytest（conftest 内存 SQLite + TestClient）
frontend/
  src/                   # Vue3 + Element Plus（门户 SPA；已弃 Electron/React）
  ...
deploy/
  docker-compose.yml     # 生产编排（backend/postgres/redis/rabbitmq/stt/tts/nginx/monitoring）
  nginx.conf
```

> 注：`backend/app/{platformrouters,platformservices}` 是 P0.1 误建目录，待清理归位到 `platform/{routers,services}`。

## 开发命令

后端（在 `backend/` 目录）：
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v    # 跑测试
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010   # 启动
```

前端（在 `frontend/` 目录）：
```powershell
npm install
npm run dev      # Vite 开发服务器（端口 5173）
npm run build    # build（提交前必须通过）
```

## 环境陷阱

1. **端口 8000 被占用**：本机 8000 被另一旧后端占用。后端启动用 `--port 8010`，前端 BASE 保持一致。
2. **PowerShell 发中文 JSON 会乱码**：用 Python + httpx 或 pytest 验证中文接口。
3. **AI 端点 mock**：`core/ai/*` 单测用 mock httpx，不依赖真实端点。写这些代码用 mock 锁逻辑。
4. **音频格式**：前端 MediaRecorder 产 webm/opus，ASR 要 16kHz 单声道 WAV，需 ffmpeg 转码。
5. **SQLite 测试库**：`*.db` 已被 .gitignore，不要提交。
6. **本机无 NVIDIA GPU**：STT/TTS/Ollama 只能 CPU，功能可用但吞吐受限；生产部署到内网 GPU。
7. **模型下载**：ASR/TTS 权重在 `D:/models/yika/`；下载需 `HF_ENDPOINT=https://hf-mirror.com`，xet 401 加 `HF_HUB_DISABLE_XET=1`。

## 提交规范

- 每个任务独立 commit，message 用 `type: 中文描述`（`feat:`/`chore:`/`docs:`）
- **提交前必跑审查清单**（上方「验证与审查清单」）+ 后端 `pytest tests/` + 前端 `npm run build`，全绿才提交
- 用 `git status` 确认无未提交的 `*.db` 或 `.env`
