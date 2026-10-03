# Phase 1 Context

## 唯一规范基线

`SimTrouble_FreezePack_v0.2/` 是当前唯一上位冻结基线。Phase 0 的三份尽调文档只提供复用和架构依据，不得覆盖 Freeze Pack 的产品边界。

## 已冻结产品事实

- V0 场景：工业机器人柔性搬运工作站。
- 训练模块：基础操作、异常处置。
- 四类异常：`object_pose_offset`、`grasp_failure`、`obstacle_collision_risk`、`placement_target_conflict`。
- 诊断状态：`START → OBSERVE → INVESTIGATE → HYPOTHESIZE → TEST → UPDATE → DIAGNOSE → REFLECT → FINISH`。
- 五维能力：Hypothesis、Evidence、Efficiency、Updating、Safety。
- Tutor 只能追问、提示、解释、复盘；不得拥有 Ground Truth、未披露证据、完整 Optimal Path、评分或状态迁移权。
- V0 使用 Mock Simulation；真实 Isaac/Gazebo 属于 Phase 9。

## 冻结解释原则

- 对 Freeze Pack 已给出的字段、枚举、接口和路由进行结构化，不新增业务能力。
- Freeze Pack 未定义的算法、状态迁移条件、评分权重、提示升级规则、仿真实现细节保持未实现。
- 为表达 JSON 结构所需的技术字段只做最小定义；不得借 Schema 引入新产品需求。
- 任何需要改变 Freeze Pack 的事项进入 Contract Change Proposal，不在本阶段自行决定。
