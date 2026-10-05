# Phase 3 Contract

> Status: APPROVED FOR IMPLEMENTATION — DG-01 through DG-04 are frozen in `decision-record.md`.

## Frozen invariants

- Stage enum 与 `learner-session.schema.json` 完全一致，不新增、删除或改名；
- `CaseSession` 内部持有的 `LearnerSession.current_stage` 是当前阶段的唯一事实源；对外只提供不能回写权威状态的快照/只读视图；
- 只有 Core Domain 的 Diagnostic State Machine 可以改变 `current_stage`；
- 成功迁移必须原子地更新阶段并追加审计事件，不允许只完成其中一项；
- Trace 只追加，不删除、不覆盖、不重新排序；
- `TraceEvent` 只能使用已冻结的七个字段，不增加公共字段；
- 拒绝路径不得改变 stage、Evidence、Hypothesis、Action、计数或 Skill 等领域状态；只允许按 DG-03 追加对应拒绝审计事件；
- Phase 3 不解释 Case `scoring_rules`，不计算 Skill，不调用 Tutor/LLM/Simulation。

## Intended modules

Phase 3 实现只允许触及：

```text
core/state_machine/
core/session_trace/
core/case_engine/case_session.py
tests/state_machine/
tests/session_trace/
tests/phase3_integration/
```

具体类名、方法签名与文件拆分属于后续任务 Spec；本规划不提前冻结实现形态。

## Pre-implementation code gates

The Phase 2 cross-audit in `docs/phase2-code-cross-audit.md` identified integrity gaps that must close before State Machine behavior is added:

- **CG-01 Session authority:** external callers cannot receive a mutable reference capable of changing authoritative Session state;
- **CG-02 Trace append-only boundary:** existing Trace events, order and nested payloads cannot be rewritten through exposed references;
- **CG-03 input/time validity:** an explicit empty Session ID is rejected, and Phase 3 Trace timestamps are timezone-aware and deterministic in tests;
- **CG-04 regression compatibility:** Evidence, Hypothesis, Action and Progress behavior remains compatible with the frozen public contracts.

These gates authorize only internal integrity work. They do not expand DG-01 through DG-04 and do not authorize public Schema/API changes.

## Resolved decisions

The normative details are in `decision-record.md`.

- **DG-01:** only the eight forward adjacent edges in the frozen map are legal; no loops, rollback, skip or self-transition.
- **DG-02:** transition eligibility is topology-only; no unfrozen business guards or automatic stage advancement.
- **DG-03:** `stage` is the authoritative post-event stage, event names and public-safe `result` shapes are controlled, rejected operations append only their audit event.
- **DG-04:** Trace is stored only in the in-memory authoritative `LearnerSession.trace`; no SQLAlchemy/SQLite/repository work is included.

## Error boundary

非法状态请求必须由 Core 内部错误显式拒绝：领域状态保持不变，仅按 DG-03 追加 `StateTransitionRejected`。具体 HTTP status code 与公共错误 envelope 尚未冻结，Phase 3 不得顺带修改 API Contract。
