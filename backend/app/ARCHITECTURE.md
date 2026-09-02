# v3.0 后端架构（目录结构与代码归属）

> 依据《yika 开发文档 v3.0》§3 总体架构 + §5 子系统规范 S1-S8。
> **P0.1 定版**。后续所有批次的代码按此目录摆放。

## 目录结构

```
backend/app/
├── main.py                  # 平台入口：挂 platform 路由 + 各子系统路由
├── config.py  database.py   # 全局配置(.env) + SQLAlchemy engine/session（app 根，core 引用）
├── models.py                # ← P0.2 全量 v3.0 数据模型（Group/User/... ）
├── core/                    # 平台共享底座（跨子系统复用）
│   ├── auth.py              # JWT 双令牌/登录限速/审计（自旧 app/auth.py 归位）
│   ├── db.py                # engine/session（自旧 database.py 归位）
│   ├── errors.py            # P0.5 统一错误处理
│   ├── logging.py           # P0.5 日志骨架
│   └── ai/                  # 平台级 AI 能力（P5/P6 复用，子系统共用）
│       ├── llm.py asr.py tts.py audio.py denoise.py
│       └── note_gen.py pipeline.py qa_service.py req_extract.py
├── platform/                # 平台外壳逻辑（非业务）
│   ├── models.py            # P1 组织/子系统注册/权限相关模型（或集中 app/models）
│   ├── routers/             # P1 auth组织/子系统注册/权限/共享API
│   └── services/
└── subsys/                  # 可插拔子系统（每个子系统一个包，S1-S8）
    └── collab/              # 首个子系统「组内协作」
        ├── models.py        # Customer/Project/Requirement/RequirementCandidate/Note/Knowledge
        ├── routers/         # P3 主数据、P4 权限交互
        └── services/
```

## 代码归属约定

| 层 | 放什么 | 不该放什么 |
|---|---|---|
| `core/` | 跨子系统共享底座：认证/审计/错误/日志/AI 能力 | 具体业务逻辑（客户/需求 CRUD） |
| `platform/` | 平台外壳：组织/子系统注册/权限/共享 API | 某个子系统的私有业务 |
| `subsys/collab/` | 组内协作子系统的业务（客户/项目/需求/知识库） | 平台底座、其他子系统 |
| `app/models.py` | 全量业务模型 | — |

## 关键规则
1. **子系统不直连库、不自搞权限**（S3/S4）——一律经 platform 共享 API + core 权限中间件。
2. **组隔离**在 API 中间件层强制（按当前用户 group_id 过滤），子路由不做重复逻辑。
3. **AI 服务**（core/ai）为平台共享能力，子系统直接调用，不各自实现。
4. 新增子系统 = 在 `subsys/` 加一个包 + 在平台注册清单登记（S1/S8），不改平台核心。

## P0.1 完成状态
- [x] core/platform/subsys 三层目录就位
- [x] 成熟代码归位：auth→core/auth.py、database→core/db.py、AI services→core/ai/
- [x] import 路径已修正（core 引用 app 根 config/database/models）
- [x] core 包全量 import 通过；基线 47 测试保持全绿（旧代码未破坏）
