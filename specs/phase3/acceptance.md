# Phase 3 Acceptance

> Status: PLANNED — checklist cannot be executed until DG-01 to DG-04 are resolved where applicable.

## Decision and scope gate

- [ ] DG-01 合法 transition table 已由 Contract Owner 批准并写入 Spec；
- [ ] DG-02 每条迁移的前置条件和完成语义已批准；
- [ ] DG-03 Trace event 语义与受控 action type 已批准；
- [ ] DG-04 Trace storage 边界已批准；
- [ ] 未修改冻结 stage enum、公共 Schema 或 API；若确需修改，存在已批准 CCP。

## State Machine tests

- [ ] 每条已批准迁移均可确定性执行；
- [ ] 所有未批准的跳转、回退和回环均被拒绝；
- [ ] 拒绝路径不修改 `current_stage` 或其他 Session 数据；
- [ ] 迁移前置条件逐条覆盖通过和拒绝用例；
- [ ] 前端/Tutor/任意调用方不能绕开 State Machine 直接推进阶段。

## Trace tests

- [ ] 每次成功迁移追加一个符合 `learner-session.schema.json` 的 TraceEvent；
- [ ] Trace 顺序与实际事件顺序一致，既有事件不被覆盖；
- [ ] `stage`、`action_type`、`result` 的值符合 DG-03；
- [ ] `evidence_id`、`current_hypothesis`、`tutor_hint` 只按已批准语义记录；
- [ ] Trace 不包含 Ground Truth、完整 Optimal Path、未释放 Evidence 或评分密钥；
- [ ] DG-04 选择的保存边界有对应成功与失败测试。

## Integration and regression

- [ ] 从 `START` 到 `FINISH` 的一条已批准完整路径可在 `ST-001` Session 上执行；
- [ ] 如 DG-01 批准循环，每一条循环均有正向与非法相邻路径测试；
- [ ] Phase 1 Contract tests 与 Phase 2 Training Core tests 全部通过；
- [ ] Core source 未引入 LLM、LangGraph、Isaac、ROS 或 Gazebo；
- [ ] 未实现 Skill 评分、HTTP API、前端、Tutor 或 Simulation Adapter。
