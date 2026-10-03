# Simulation Adapter Contract v0

## 责任边界

Training Core 只能依赖以下六个能力：

```python
class SimulationAdapter:
    def reset_scenario(self, case_id: str): ...
    def get_state(self) -> dict: ...
    def perform_action(self, action: dict) -> dict: ...
    def get_evidence(self, evidence_id: str) -> dict: ...
    def inject_fault(self, fault_config: dict) -> None: ...
    def get_result(self) -> dict: ...
```

该代码块是接口说明，不是 Phase 1 产品实现。

## 方法语义

| 方法 | 输入 | 输出/效果 | 不负责 |
|---|---|---|---|
| `reset_scenario` | 已存在的 `case_id` | 将 Adapter 恢复到该 Case 可开始状态 | 加载培训规则、评分 |
| `get_state` | 无 | 平台中立的当前状态字典 | 暴露 Isaac/ROS/Gazebo 类型 |
| `perform_action` | Core 已校验的 action 字典 | 平台中立的动作结果字典 | 决定诊断状态迁移 |
| `get_evidence` | Case 中存在的 `evidence_id` | 对应 evidence 字典 | 决定证据是否允许披露 |
| `inject_fault` | Case 的 `fault` 配置 | Adapter 内部应用异常 | 把 fault ground truth 暴露给学员/Tutor |
| `get_result` | 无 | 平台中立的当前任务结果字典 | 计算 Skill 分数 |

## 最小状态边界

为兼容 Phase 9，`get_state()` 的平台中立表示只预留以下规范字段：

- `object_pose`
- `target_pose`
- `gripper_state`
- `task_status`

本阶段不冻结 pose 数值格式、ROS topic、Isaac API、碰撞传感器、相机、深度、力反馈或控制协议；这些必须在真实 Adapter 的独立 Spec 中决定。

## 强制隔离

Training Core 不得 import：

- `isaacsim`
- ROS / ROS 2 packages
- Gazebo-specific packages

V0 实现目标是 `MockSimulationAdapter`，但其实现属于 Phase 8，不属于本阶段。
