# 决策 05：需求状态机设计（两类调整 + 不可行可重新评估）

**状态**：已采纳
**日期**：2026-08-25

## 背景

需求从录入到交付要经历：草稿 → 评审 → 开发 → 交付。评审时技术人员要判断每条需求"能不能落地"，排除无法实现的。

评审结论里有三个微妙的分支需要设计清楚：
1. 需求需要"调整"时，退给谁？
2. "不可行"的需求怎么办？删掉还是留档？

## 决策

状态机如下（`backend/app/state_machine.py`）：

```
draft → pending_review → feasible → in_dev → delivered
              ↘ info_needed ──→ pending_review
              ↘ plan_needed ──→ pending_review
              ↘ infeasible ───→ pending_review
```

- **调整分两类**：
  - `info_needed`（信息待补充）→ 返**讲师**：需求没说清、缺信息，讲师去和客户确认后补充重提。
  - `plan_needed`（方案待调整）→ 返**技术**：需求合理但落地方案要改，技术改方案后重新评审。
- **不可行 `infeasible`**：附原因**归档但不删除**，可「重新评估」回到 `pending_review`。

## 为什么这么设计

1. **调整返给谁，由"调整原因"决定**。信息问题找讲师（他们接触客户），方案问题找技术（他们懂实现）。分成两类让"下一步归谁"语义清晰，不模糊。
2. **不可行不删除，是因为技术边界会变**。今天判"不可实现"的需求，未来新模型/新工具/团队能力强了可能就可行了。删掉就永远丢了这笔判断。
3. **状态机是纯函数**，不掺 IO，可独立测试、可复用，也便于未来加状态。

## 备选方案（为何没选）

- **调整不分类**（只有一个"需调整"状态）：退回后不知道归谁，流程会卡住。
- **不可行直接删除**：丢失"为什么不可行"的沉淀，客户反复提同一件事时无法追溯。

## 核心原则

**状态流转要反映真实业务语义，每个状态有明确的"下一步是谁、为什么"。**

## 关联代码

- `backend/app/state_machine.py` — `allowed_transitions` 字典 + `can_transition` + `transition`
- `backend/app/routers/requirements.py` — `/requirements/{id}/transition` 接口
- `backend/tests/test_state_machine.py` — 状态机纯函数测试
- `backend/tests/test_requirements.py` — 接口层状态流转 + 权限测试
