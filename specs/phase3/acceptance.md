# Phase 3 Acceptance

> Status: APPROVED FOR IMPLEMENTATION — DG-01 through DG-04 are resolved; implementation checkboxes remain open.

## Decision and scope gate

- [x] DG-01 仅允许冻结图中的八条单向相邻边；
- [x] DG-02 只使用拓扑条件，不增加业务 guard 或自动推进；
- [x] DG-03 已冻结字段语义、受控 action type 与 public-safe result；
- [x] DG-04 只使用内存 `LearnerSession.trace`，不引入数据库；
- [x] 本次决策未修改冻结 stage enum、公共 Schema 或 API；

## Session integrity gate

- [ ] 外部调用方不能通过 `CaseSession` 暴露的引用直接改变权威 `current_stage`；
- [ ] 创建后的 Session 不能被改成非法 stage、负计数或空 Evidence ID；
- [ ] 仅当 `session_id is None` 时生成 UUID，显式空 ID 被拒绝；
- [ ] Evidence、Hypothesis、Action 与 Progress 的 Phase 2 行为保持兼容。

## State Machine tests

- [ ] 每条已批准迁移均可确定性执行；
- [ ] 所有未批准的跳转、回退和回环均被拒绝；
- [ ] 拒绝路径不修改领域状态，只追加一个 `StateTransitionRejected`；
- [ ] 八条允许边和其他拒绝边均有覆盖；
- [ ] 前端/Tutor/任意调用方不能绕开 State Machine 直接推进阶段。

## Trace tests

- [ ] 新 Session 在 `START` 追加且仅追加一个 `SessionStarted`；
- [ ] 每次成功迁移至少追加一个符合 Schema 的 `StateTransitioned`；`REFLECT → FINISH` 随后追加 `SessionFinished`；
- [ ] Trace 顺序与实际事件顺序一致，既有事件不被覆盖；
- [ ] 已追加事件不能通过外部引用被替换、删除、重排或修改嵌套 payload；
- [ ] timestamp 使用带时区的 UTC 时间，并可通过注入时钟确定性测试；
- [ ] `stage`、`action_type`、`result` 的值符合 DG-03；
- [ ] `action_type` 不超出 `decision-record.md` 的 Phase 3 白名单；
- [ ] `evidence_id`、`current_hypothesis`、`tutor_hint` 只按已批准语义记录；
- [ ] Evidence、Hypothesis 与 Action 的事件数量和顺序符合 DG-03 emission rules；
- [ ] Trace 不包含 Ground Truth、完整 Optimal Path、未释放 Evidence 或评分密钥；
- [ ] Trace 只保存在内存 Session 中，代码和依赖均不包含 SQLAlchemy/SQLite repository。

## Integration and regression

- [ ] 从 `START` 到 `FINISH` 的一条已批准完整路径可在 `ST-001` Session 上执行；
- [ ] 所有循环、回退、跳转、自转换以及从 `FINISH` 出发的迁移均被拒绝并审计；
- [ ] Phase 1 Contract tests 与 Phase 2 Training Core tests 全部通过；
- [ ] Core source 未引入 LLM、LangGraph、Isaac、ROS 或 Gazebo；
- [ ] 未实现 Skill 评分、HTTP API、前端、Tutor 或 Simulation Adapter。
