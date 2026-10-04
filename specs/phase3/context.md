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

## Planning constraint

冻结材料尚未给出完整可执行 transition table、迁移前置条件或 Trace 持久化边界。Phase 3 不以“合理推测”补齐这些产品行为；依赖这些行为的开发任务在决策冻结前不得开始。
