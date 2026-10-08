# Phase 3 Context

## Authoritative inputs

1. `SimTrouble_FreezePack_v0.2/02_CONTRACTS.md`；
2. `SimTrouble_FreezePack_v0.2/05_DEVELOPMENT_ROADMAP.md`；
3. `contracts/schemas/learner-session.schema.json`；
4. `specs/phase2/` 与现有 Training Core；
5. `docs/architecture-decisions.md` 仅作为不与上述冻结内容冲突的架构方向。

## Existing foundation

- `DiagnosticStage` 已包含 `START`、七个诊断阶段和 `FINISH`；
- 新 Session 从 `START` 开始；
- `LearnerSession.trace` 已存在并由 `TraceEvent` 校验；
- Trace 最小字段已冻结为 `timestamp`、`stage`、`action_type`、`evidence_id`、`current_hypothesis`、`tutor_hint`、`result`；
- Phase 2 的 Evidence 请求、Hypothesis 提交和 Action 记录当前不会改变阶段。

## Authority and trust boundary

- Core Domain 决定 State transition；
- 前端不能直接修改 Session；
- Tutor 不能跳状态；
- Trace 不得泄漏 Ground Truth、完整 Optimal Path、未释放 Evidence 或评分密钥；
- Phase 3 不引入外部输入层，因此不修改 HTTP API Contract。

## Resolution rule

Phase 3 使用最严格的冻结基线解释：

- 状态图只授权图中明确存在的有向边；
- Schema/Contract 未定义的业务前置条件、字段和副作用视为未授权；
- ADR 只在不扩展冻结 Schema/API 的范围内补充事件命名；
- 已列入技术栈但没有本阶段 Contract 的组件不提前实现。

DG-01 至 DG-04 的具体结论和依据记录在 `decision-record.md`。任何扩展必须先通过 CCP 或后续 Phase Spec。
