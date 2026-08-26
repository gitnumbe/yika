# 项目文档导航（本项目如何"记住自己"）

> 目标：**不靠 AI 代理的记忆来记住项目，而是让项目文档本身记住它。** 任何 AI 代理或新工程师接手，读这个目录就能理解"是什么、为什么、怎么做"。

## 阅读顺序（推荐）

1. **`AGENTS.md`**（仓库根目录）—— AI 代理的快速上手指导：技术栈、目录结构、核心约定、开发命令、环境陷阱。
2. **`docs/superpowers/specs/2026-08-25-team-collab-agent-design.md`** —— 设计规格：完整需求、架构、数据模型、评审决策。
3. **`docs/superpowers/plans/2026-08-25-team-collab-agent-mvp.md`** —— 实现计划：19 个任务的执行细节。
4. **`docs/business-rules.md`** —— 业务规则总览：权限矩阵、状态机、防幻觉铁律等"必须遵守的规则"。
5. **`docs/decisions/*.md`** —— 每个核心功能的独立决策说明：**为什么这么设计**，以及备选方案为何被否。

## 文档索引

| 文档 | 回答的问题 |
|---|---|
| `AGENTS.md` | 怎么上手、怎么跑、有哪些坑 |
| `specs/...design.md` | 系统长什么样、要做什么 |
| `plans/...mvp.md` | 具体怎么一步步实现 |
| `business-rules.md` | 业务上必须遵守的规则是什么 |
| `module-dependencies.md` | 改某个模块会影响谁（影响分析，防全局失控） |
| `decisions/01-pure-internal-tool.md` | 为什么是纯内部工具、客户无账号 |
| `decisions/02-multi-user-data-model.md` | 为什么数据模型从第一天就是多用户 |
| `decisions/03-llm-dual-source.md` | 为什么要大模型 + 小模型双源 |
| `decisions/04-recording-pipeline.md` | 为什么不做说话人分离、用小模型去噪 |
| `decisions/05-requirement-state-machine.md` | 为什么状态机这样设计（两类调整/不可行可重评） |
| `decisions/06-anti-hallucination.md` | 为什么 LLM 只产候选、人工确认（防幻觉铁律） |
| `decisions/07-qa-agent.md` | 为什么答疑 MVP 用关键词检索、如何回流 |
| `decisions/08-deployment-path.md` | 为什么先内网电脑、后公司服务器 |

## 维护约定

- **改代码前先读对应决策文档**，确认改动是否违背了当初的设计原则。
- **如果发现某个决策过时了**（技术边界变化、需求变化），不要直接改代码绕过它，而是：更新对应 `decisions/*.md`，标记"已变更 + 新决策 + 变更原因"，再改代码。
- **新做了一个非平凡的架构/业务决策**，就新增一个 `decisions/NN-*.md`，并在本文档索引里登记。
