# Phase 3 Contract

> Status: DRAFT FOR DECISION — no implementation authorization yet.

## Frozen invariants

- Stage enum 与 `learner-session.schema.json` 完全一致，不新增、删除或改名；
- `CaseSession.session.current_stage` 是当前 Session 阶段的唯一事实源；
- 只有 Core Domain 的 Diagnostic State Machine 可以改变 `current_stage`；
- 成功迁移必须原子地更新阶段并追加审计事件，不允许只完成其中一项；
- Trace 只追加，不删除、不覆盖、不重新排序；
- `TraceEvent` 只能使用已冻结的七个字段，不增加公共字段；
- 无论成功或拒绝，失败路径不得造成部分 Session mutation；
- Phase 3 不解释 Case `scoring_rules`，不计算 Skill，不调用 Tutor/LLM/Simulation。

## Intended modules

在 Decision Gates 关闭后，Phase 3 预计只触及：

```text
core/state_machine/
core/session_trace/
core/case_engine/case_session.py
tests/state_machine/
tests/session_trace/
tests/phase3_integration/
```

具体类名、方法签名与文件拆分属于后续任务 Spec；本规划不提前冻结实现形态。

## Decision Gates

### DG-01 — Legal transition topology

需由 Contract Owner 明确完整 transition table：

- 仅允许冻结图的单向相邻迁移；或
- 允许诊断循环，并逐条列出可回退/回环边。

在此决定前，不实现 transition rules。不得依据 ADR 中的示例自行扩展成完整表。

### DG-02 — Transition prerequisites and completion semantics

需明确每条迁移是否要求 Evidence、Hypothesis、Test result、Diagnosis 或 Reflection 等前置条件，以及 Session 在何种动作后进入 `FINISH`。在此决定前，不把字段存在性或动作次数推断为业务门槛。

### DG-03 — Trace event semantics

需明确：

- `TraceEvent.stage` 表示事件发生前阶段、发生后阶段还是目标阶段；
- State transition 的 `action_type` 受控词汇；
- 非法迁移请求是否写入 Trace，以及如何在现有 `result` 字段表达；
- 状态迁移以外哪些 Phase 2 动作必须在本阶段补录 Trace。

这些决定不得通过新增 Schema 字段绕开；确需变更 Contract 时先提交 Change Proposal。

### DG-04 — Trace storage boundary

需明确 Phase 3 的“Trace 保存”是：

- 仅在当前 `LearnerSession.trace` 中追加，持久化由后续 Backend/Persistence Spec 负责；或
- 本 Phase 同时包含 SQLAlchemy/SQLite repository。

在决定前不新增 SQLAlchemy 依赖、不创建数据库模型或迁移。

## Error boundary

非法状态请求必须被显式拒绝且不修改 Session。具体异常类、错误码和公共 HTTP 映射尚未冻结；Phase 3 只能在 DG-01 至 DG-03 关闭后的任务 Spec 中定义 Core 内部错误行为，不能顺带修改 API Contract。
