# SimTrouble Tutor 外部项目技术尽调与复用分析

> 状态：Phase 0 冻结候选  
> 尽调基准日：2026-10-03  
> 约束来源：`SimTrouble_FreezePack_v0.2/`（当前唯一冻结基线）及 `docs/product/` 下的原始方案、参赛材料  
> 本文只做技术尽调和决策，不引入产品代码、仿真环境或 LLM 调用。

## 1. 结论先行

1. **V0 仍严格采用 Mock-first。** V0 的作品价值是“可控异常 → 诊断推理训练 → 过程评价 → 能力画像”，不是机器人控制。Training Core 必须与 Isaac Sim、ROS 2、Gazebo 解耦。
2. **真实仿真首选 Gazebo Sim Harmonic + ROS 2 Jazzy + 官方 `franka_ros2` + MoveIt Task Constructor（MTC）。** 这是许可证最清晰、可维护性最好、最符合当前团队硬件条件的路线；但应在 Ubuntu 24.04 原生机、双系统或远程 Linux 主机上部署，不能把当前 Windows 主机当作已具备运行条件。
3. **Isaac Sim 作为条件式备选和接口设计参考，不作为 V0 依赖。** 官方 pick-and-place 示例成熟，状态与失败语义清晰；但本机没有 NVIDIA RTX GPU，达不到 Isaac Sim 6.0 最低显卡要求，且其运行时、资产和再分发许可要与 GitHub 源码许可证分开判断。
4. **不直接复用社区 `panda_ros2_gazebo`。** 它停留在 Ubuntu 20.04 / ROS 2 Foxy，2021 年后无维护，README 明示 pick-and-place 已损坏，且仓库缺少根许可证、包元数据又在 BSD/Apache 之间不一致。
5. **故障注入采用自研最小层。** Bosch `rosbag-fault-injection` 只适合借鉴 seed、时间窗、字段变换和 record-transform 的思路；它是离线 rosbag 工具，不是在线仿真故障控制器，且当前源码存在启动时 `NameError` 和对配置路径使用 `eval/exec` 的问题。
6. **Tutor 采用“程序拥有状态与策略，LangGraph 编排、LLM 只生成受限话术”。** 借鉴 LLMTutor 的苏格拉底式带教、YAML 配置和会话日志；按 Freeze Pack v0.2 在 Phase 5 引入 LangGraph，但只让它承担 Tutor 编排，不让 LangGraph 或 prompt 成为诊断状态机的事实来源。
7. **能力画像采用 OATutor 的“技能标签—行为证据—持续更新”思想，但 V0 坚持可解释规则评分。** 不引入 BKT/IRT/AFM，也不把数学题的对错观测模型硬套到运维诊断行为上。

## 2. 本项目边界与外部项目筛选标准

### 2.1 冻结边界

SimTrouble Tutor V0 是面向“工业机器人柔性搬运工作站”的仿真驱动运维培训闭环，包含 1 个工作站、2 个训练模块、8–12 个稳定 Case、1 个 Tutor Agent、五维能力画像、完整诊断轨迹、Mock Simulation 和 5 个冻结页面（Dashboard、Learning、Scenario Brief、Diagnostic Workspace、Report）。V0 的四类核心异常为：

- `object_pose_offset`
- `grasp_failure`
- `obstacle/collision_risk`
- `placement_target_conflict`

它不是企业维修系统、真实机器人控制器、自动根因诊断器、预测性维护系统、普通 RAG 题库或多设备平台。

### 2.2 筛选维度

每个候选项目均按以下维度检查：

- LICENSE/NOTICE 与内容许可证是否一致；
- 最近提交时间、版本/分支和 README 的运行承诺；
- Python、Node、ROS、操作系统、GPU、Docker 等前置条件；
- 是否存在可直接运行的 pick-and-place、Case/Session、状态持久化、故障注入或学习分析模块；
- 是否能在不污染 Training Core 的前提下通过 Adapter 使用；
- 是“文档声称可运行”“源码静态可读”还是“已在本机实际运行”。

本轮未安装大型仿真环境，也未对 Isaac/Gazebo 做端到端运行验证；除特别注明外，结论来自官方文档、README、许可证和关键源码的静态审查。

## 3. 复用矩阵

| 模块 | 仓库/项目 | License | 维护状态 | 直接复用 | 修改复用 | 只参考架构 | 风险 |
|---|---|---|---|---|---|---|---|
| V0 仿真 | 项目自有 Mock Adapter | 自有 | 待 Phase 1–4 实现 | **是，V0 主路径** | — | — | 需保证与真实仿真使用同一 Adapter contract，避免“假 Mock”绕开业务规则 |
| Isaac 仿真 | [NVIDIA Isaac Sim](https://github.com/isaac-sim/IsaacSim) | GitHub 源码 Apache-2.0；Kit/扩展/资产另有 NVIDIA 条款 | 活跃；6.0 文档与源码持续更新 | 否（V0） | 条件允许时只在 Adapter 侧接入官方示例/API | **是**：状态归一化、分阶段 pick-place、超时/失败语义 | 本机无 RTX；最低 32 GB RAM/RTX 4080 16 GB VRAM；许可不能只看 Apache-2.0 |
| Gazebo 基础 | [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/getstarted/) + [`ros_gz`](https://gazebosim.org/docs/harmonic/ros2_integration/) | Apache-2.0（组件分别保留声明） | Harmonic 为 LTS；ROS 2 Jazzy 是官方推荐组合 | 作为外部依赖直接使用 | Adapter、world、bridge 配置自研 | — | Windows 支持不是主路径；需 Ubuntu 24.04/Jazzy 环境烟测 |
| Franka 集成 | [`frankarobotics/franka_ros2`](https://github.com/frankarobotics/franka_ros2) | Apache-2.0 + NOTICE | 活跃；本轮检出 `6cedf7f`，2026-09-01，v3.5.3 | Adapter 侧依赖官方包 | 自研 world、归一化读取与任务状态聚合 | — | README 明示不正式支持 Windows；项目快速迭代、可能破坏兼容；当前主线以 FR3 生态为主，Panda 资产需单独验证 |
| 搬运任务 | [`moveit/moveit_task_constructor`](https://github.com/moveit/moveit_task_constructor) | BSD-3-Clause | 活跃；本轮检出 `f527048`，2026-09-10 | 作为外部规划依赖 | 自研 Case→stage/scene 的映射和结果归一化 | — | 不是完整产品；任务成功必须以物体最终位姿而非机械臂末端位姿判定 |
| 搬运教程 | [`moveit2_tutorials` MTC pick-and-place](https://github.com/moveit/moveit2_tutorials/blob/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.rst) | BSD-3-Clause | 活跃；本轮检出 `e1b3727`，2026-09-16 | 示例代码可在保留声明后小范围采用 | 改造为独立 Adapter smoke test | — | 教程示例不等于稳定应用；需锁定 ROS/MTC 版本并验证 Panda/FR3 模型匹配 |
| 社区 Panda demo | [`nicholaspalomo/panda_ros2_gazebo`](https://github.com/nicholaspalomo/panda_ros2_gazebo) | **不清晰**：无根 LICENSE；`package.xml` 写 BSD，`setup.py` 写 Apache | 停滞；最后提交 2021-10-23 | **否** | **否** | 可理解旧版节点组织，但不建议作为设计基线 | ROS 2 Foxy/Ubuntu 20.04 已旧；README 明示 picknplace/pickninsert 已损坏；许可证冲突 |
| 故障注入参考 | [`boschresearch/rosbag-fault-injection`](https://github.com/boschresearch/rosbag-fault-injection) | Apache-2.0 | 有更新；本轮检出 `e3e5e9c`，2026-03-06 | 否 | 仅可重写其配置思想，不复制执行器 | **是**：seed、topic/field mask、时间窗、原始/变换记录 | 离线 rosbag，不控制实时仿真；ROS 2 Galactic devcontainer 老旧；源码 `eval/exec`；本轮直接运行关键模块触发 `NameError` |
| Tutor 产品参考 | [`SwissLearningAnalytics/LLMTutor`](https://github.com/SwissLearningAnalytics/LLMTutor) | MPL-2.0 | 活跃；本轮检出 `3ab3484`，2026-10-01 | 否 | 原则上可做文件级隔离复用，但 V0 不建议 | **是**：苏格拉底式话术、YAML tutor、执行日志、反馈 | 其阶段逻辑和答案主要在大 prompt 中；无强制 Evidence Gate；MPL 文件级义务增加发布复杂度 |
| Tutor 编排 | [`langchain-ai/langgraph`](https://github.com/langchain-ai/langgraph) | MIT | 活跃；尽调时最新发布 v1.2.12（2026-09-21） | **Phase 5 按冻结技术栈作为锁版依赖** | 只写项目自有节点/投影 | **是**：checkpoint、thread、interrupt/resume | 必须避免形成第二套状态机；resume 会从节点开头重跑；历史安全公告要求锁补丁版且禁止不可信 checkpoint |
| 学习分析 | [`CAHLR/OATutor`](https://github.com/CAHLR/OATutor) | 软件 MIT；题目内容 CC BY 4.0 | 活跃；本轮检出 `939eb0e`，2026-09-30 | 否 | 可迁移纯思想，自研实现 | **是**：KC 标签、hint pathway、最低掌握度选题、事件日志 | React 16/Material UI 4 架构旧；BKT 参数未针对诊断行为校准；内容与本项目无关且另有署名义务 |

## 4. 仿真平台深度尽调

### 4.1 本机事实与可运行性门槛

本轮只读探测得到：Windows 11 家庭中文版、Intel Core i5-13500H（12C/16T）、约 31.5 GB RAM、Intel Iris Xe（系统报告约 2 GB 显存），未发现 NVIDIA 独立显卡；WSL 枚举返回 `E_ACCESSDENIED`，因此不能断言已具备可用 Ubuntu/WSL2。

这意味着：

- **Isaac Sim 6.0：本机不满足。** 官方最低要求含 Windows 11/Ubuntu 22.04 或 24.04、32 GB RAM、50 GB SSD、GeForce RTX 4080、16 GB VRAM，并要求 RT Core；本机最关键的 RTX/VRAM 条件不满足。[官方系统要求](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/installation/requirements.html)
- **Gazebo/ROS 2：理论上不依赖 RTX，但当前 Windows 不是推荐承载面。** Gazebo 官方把 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic列为推荐组合；Windows 为 best-effort/存在运行问题。`franka_ros2` 也明确不正式支持 Windows。[Gazebo/ROS 兼容表](https://gazebosim.org/docs/jetty/ros_installation/)；[`franka_ros2` README](https://github.com/frankarobotics/franka_ros2)
- **V0：Mock 可在本机稳定开发和演示。** 这正是冻结文档要求 Mock-first 的风险隔离价值。

### 4.2 Isaac Sim

#### 可用资产

Isaac Sim 官方维护了通用操纵器和 pick-place 流程：接近抓取点、下降、闭合夹爪、抬升、接近放置点、下降、释放、撤离，并提供对象位置、目标位置、夹爪观测、任务完成/失败与 `failure_reason` 等语义。[官方 Adding a Manipulator 教程](https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_adding_manipulator.html)

官方仓库的 manipulation skill 还强调两点：成功应以**释放后的物体位姿**而不是末端执行器位姿判断；每个阶段应有超时和明确失败语义。[官方 manipulation-ik 指南](https://github.com/isaac-sim/IsaacSim/blob/develop/skills/manipulation-ik/SKILL.md)

#### 对四个规范字段的支持

- `object_pose`：由场景中被操作物体的 world pose 读取；
- `target_pose`：由 Case 配置/任务对象传入；
- `gripper_state`：由夹爪关节位置或 gripper observable 归一化；
- `task_status`：不能直接透传单一布尔值，需由 `is_done`、失败原因、阶段超时和最终物体位姿聚合。

#### 复用判断

不把 Isaac API 带进 Training Core；若以后获得合规 RTX 工作站，在 `IsaacAdapter` 内引用官方任务/控制器并转换到统一状态即可。官方 GitHub 源码的 Apache-2.0 不自动覆盖 Omniverse Kit、扩展和资产；交付第三方的 turn-key 方案还可能触发 NVIDIA AI Enterprise 条件。[Isaac Sim License FAQ](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/common/license-faq.html)

### 4.3 Gazebo Sim + ROS 2 + Franka + MoveIt

#### 推荐组合

- OS：Ubuntu 24.04 amd64；
- ROS：ROS 2 Jazzy；
- 仿真：Gazebo Harmonic；
- 机器人集成：官方 `franka_ros2`；
- 任务规划：MoveIt 2 + MoveIt Task Constructor；
- 通信：`ros_gz_bridge`、TF、`/joint_states`、规划 action/result。

Gazebo 官方说明 `ros_gz_bridge` 可在 Gazebo Transport 与 ROS 2 之间桥接消息，支持读取 joint states、TF，也能在运行时生成模型；Simulation Interfaces 还能查询实体/世界状态。[ROS 2 integration](https://gazebosim.org/docs/harmonic/ros2_integration/)

#### 对四个规范字段的支持

| 规范字段 | 推荐来源 | 归一化注意事项 |
|---|---|---|
| `object_pose` | Gazebo 实体状态/pose topic，经 `ros_gz_bridge` 或 Simulation Interfaces | 固定 frame，输出位置 + 四元数 + 时间戳；不能混用 world/base frame |
| `target_pose` | Case 的公开配置或规划场景目标 | 目标是训练语义，不应假设仿真器存在统一 `target_pose` topic |
| `gripper_state` | `/joint_states`、gripper action feedback、机器人状态接口 | 归一为 `OPEN/CLOSING/CLOSED/HOLDING/UNKNOWN`；“闭合”不等于“抓住” |
| `task_status` | MoveIt action result + 阶段状态 + 最终物体位姿 + 碰撞/超时监视器 | 由 Adapter 合成 `IDLE/RUNNING/SUCCEEDED/FAILED/TIMEOUT/ABORTED`，不依赖单一 topic |

#### 是否有现成 pick-and-place

有**可组合的官方资产**，但没有一个应直接充当本产品的完整应用：

1. `franka_ros2` 提供 Franka 与 ROS 2/Gazebo 的官方集成基础；
2. MTC 提供 Connect、MoveTo、GenerateGraspPose、ComputeIK、ModifyPlanningScene 等可组合阶段；
3. `moveit2_tutorials` 的 Panda MTC 教程提供可运行示范和 Docker 指引；
4. SimTrouble 自己负责 Case、异常注入、状态归一化、诊断训练和结果判定。

社区 `panda_ros2_gazebo` 不能填补这一层：其 README 明示 pick-and-place 已损坏，而且运行栈停留在 Foxy/Gazebo Classic 风格。

### 4.4 最小故障注入层

V0 不需要通用物理故障框架。最小层位于 Simulation Adapter 内，与 Case 的 `fault_config` 对接：

```text
Case.fault_config
        ↓
SimulationAdapter.inject_fault(spec)
        ↓
Simulator-specific actuator ──→ State Monitor
        ↓                         ↓
reset / named trigger       normalized snapshots
        └──────────────→ Episode Recorder
```

建议的最小 `FaultSpec` 概念字段（Phase 1 再冻结正式 schema）：

- `fault_id`、`type`、`seed`；
- `trigger`: `before_reset | after_reset | before_action | on_phase`；
- `parameters`；
- `duration` 或 `until_phase`；
- `expected_observable`；
- `cleanup/reset_policy`。

四类异常的最小实现：

| 异常 | Mock | Gazebo | Isaac（条件式） |
|---|---|---|---|
| `object_pose_offset` | reset 时偏移对象状态 | reset 前设置实体 pose | reset 前设置物体 world pose |
| `grasp_failure` | close 后不进入 HOLDING | 禁止/取消 attach，或覆盖夹爪结果 | 让抓取阶段超时/不建立持有状态 |
| `obstacle/collision_risk` | 风险标记 + 可见 evidence | 生成/移动障碍物并加入规划场景 | 场景中插入障碍物并触发碰撞监视 |
| `placement_target_conflict` | 标记目标被占用/偏移 | 生成占位物或修改目标条件 | 修改目标区场景或目标 pose |

注入必须是幂等的、可由 seed 重放、可清理，并在 trace 中记录“计划触发”和“实际触发”。训练界面不能直接泄漏 fault ground truth。

### 4.5 Episode 记录建议

真实仿真和 Mock 均输出同一种 Episode：

- 元数据：`episode_id`、`case_id`、`adapter_kind`、模拟器/版本、seed、开始/结束时间；
- 故障：`fault_spec_ref`、计划/实际触发事件；
- 时间线：规范化 state snapshot、学员 action、evidence release、阶段变化、Tutor turn；
- 结果：task status、failure reason、最终物体位姿、碰撞/安全事件；
- 溯源：资产、world、软件版本与配置哈希。

Bosch 项目可提供“原始数据—配置—变换后数据”的思路，但不应成为在线记录器实现。

## 5. Tutor 与 Case/Session 深度尽调

### 5.1 LLMTutor 可借鉴和不可借鉴之处

LLMTutor 是活跃的 case-based、Socratic tutor。其配置以 YAML 区分 tutor，持久化 execution/message/feedback，并支持 OpenAI/Ollama。对 SimTrouble 有价值的是：

- Tutor 人设与领域内容分离；
- 会话执行 ID 和逐消息日志；
- 苏格拉底式问题、分级提示和反馈入口；
- 本地模型/云模型的提供方抽象。

但它把大量阶段流程、答案和行为规则放进长 prompt，聊天接口把该 prompt 直接作为 system message，再保存消息。这与 SimTrouble 的安全边界不符：Case ground truth、最优路径、未释放证据和评分规则不得进入 LLM 上下文；LLM 也不能决定权威状态迁移。

因此 LLMTutor 仅作产品/交互参考，不直接搬运 prompt、数据模型或应用代码。

### 5.2 Case 与 Session 的推荐组织

```text
Case（版本化、只读）
├─ public_context
├─ hidden_ground_truth
├─ evidence_catalog + release_rules
├─ expected_reasoning / allowed_checks
├─ scoring_rules + skill_tags
└─ simulation/fault_config

LearnerSession（每次训练、可变）
├─ diagnostic_state
├─ current_hypotheses
├─ released_evidence_ids
├─ append-only trace
├─ hint/history counters
└─ score_evidence / result

TutorTurn（派生记录）
├─ public_state_projection
├─ policy decision
├─ model metadata
└─ validated output
```

Case 不能在一次 Session 内被模型改写；Session 只能经 Application Service / State Machine 命令更新；Tutor 输出仅是建议话术，不能直接写 Session。

### 5.3 LangGraph 的角色边界

LangGraph 的 checkpoint/thread/interrupt 对“问一句—等学员—恢复”有帮助。[Persistence 文档](https://docs.langchain.com/oss/python/langgraph/persistence)；[Interrupt 文档](https://docs.langchain.com/oss/python/langgraph/interrupts)

但本项目已有独立 Diagnostic State Machine。按 Freeze Pack v0.2，Phase 5 使用 LangGraph 时：

- 它只编排 Tutor 的读取、策略选择、生成和输出校验；
- 图 state 只保存 `public_state_projection` 与 Tutor 运行信息；
- CaseSession/数据库仍是权威事实源；
- resume 时节点会从 `interrupt()` 前重新执行，因此中断前不得有非幂等写操作；
- checkpoint 仅接受应用自身生成的数据，依赖锁定补丁版本，不反序列化用户上传对象。

LangGraph 的图应保持最小，只承载 Tutor 的“读取公共投影—选择教学意图—生成—校验/回退”。即使确定性 policy 函数已足够，也通过薄节点接入已冻结的 AI 技术栈，而不把 Case/Session 业务逻辑迁入图中。

### 5.4 Evidence Release 的最佳落点

**Evidence Release 必须放在 Training Core 的 `EvidenceEngine/CaseSessionService`，位于状态迁移之后、Tutor 调用之前。** 它不属于 prompt，也不应暴露成可任意读取隐藏数据的 LLM tool。

推荐序列：

1. 学员请求检查/证据；
2. State Machine 判断当前状态是否允许该动作；
3. Evidence Engine 根据 Case release rule、前置动作、安全约束和成本决定释放内容；
4. 写入 `EvidenceReleased` trace，并更新 Session 的 `released_evidence_ids`；
5. `PublicStateProjector` 只投影公开上下文、已释放证据、学员历史和当前教学目标；
6. Tutor Policy 选 `question | hint | explain | reflect`；
7. LLM 只润色/生成受限消息；输出经 schema 和泄漏检查后记录。

这条边界保证“程序决定事实与进度，模型决定表达方式”。

### 5.5 动态 hint 策略

V0 采用确定性提示阶梯，不需要 RL：

1. `L0`：元认知追问——要求先陈述观察或假设；
2. `L1`：指出应关注的证据类别，不给结论；
3. `L2`：给出具体检查方向或下一步动作；
4. `L3`：给出 bottom-out procedural cue，但在 `REFLECT/FINISH` 前仍不泄漏 ground truth。

升级信号包括重复无效检查、连续错误分支、已有反证但不更新假设、步骤预算接近上限和显式求助；学员正确收敛时不升级。安全风险触发单独的强制提示，优先于教学渐进性。所有升级必须记录 `rule_id` 和理由，以便演示和评分复核。

## 6. 学习分析与能力画像尽调

### 6.1 OATutor 的可迁移思想

OATutor 用知识组件（KC）标注步骤、用 hint pathway 组织逐级帮助、记录学习行为，并可选择低掌握度技能对应的问题。迁移到 SimTrouble 后：

- 每个 Case、诊断动作和 trace event 标注五维 skill tags；
- 每条评分证据包含 `dimension`、`delta`、`rule_id`、`reason`、`event_ref`；
- 单次 Session 先生成可解释明细，再聚合到 learner profile；
- 下一 Case 可按最低维度 + 当前难度带推荐，而不是只看总分。

### 6.2 V0 五维规则证据

| 维度 | 正向证据 | 负向证据 |
|---|---|---|
| Hypothesis | 基于观察提出可检验假设；明确区分多个候选原因 | 无观察即下结论；假设不可验证或频繁跳跃 |
| Evidence | 选择高信息量证据；把证据与假设明确关联 | 重复已知证据；收集与当前假设无关的信息 |
| Efficiency | 以少量必要步骤排除分支并收敛 | 无目的遍历、重复动作、过多提示依赖 |
| Updating | 遇到反证后及时修正概率/排序或撤回假设 | 忽略反证、坚持已被否定结论 |
| Safety | 先做安全检查；遇到碰撞风险停止/隔离 | 在风险未排除时继续动作；跳过必要安全门 |

建议每维输出 `0–100 + confidence + evidence[]`，但最终分段、权重和跨 Session 衰减应在 Phase 1 的 Skill Schema 中冻结。规则版本必须随结果保存，确保同一 trace 可重算。

### 6.3 现在不应引入的算法

- **BKT**：需要已校准的初始掌握、学习、猜测、失误概率；诊断行为不是简单对/错 KC 观测。
- **IRT/AFM/PFA**：需要足够样本量和稳定题目参数，V0 的 8–12 个 Case 不具备统计基础。
- **强化学习/多臂老虎机**：奖励定义和安全边界尚未成熟，且不利于比赛演示中的可解释性。
- **LLM 自评分**：可作为文字反馈补充，但不能成为五维分数的唯一来源。

## 7. 仓库级核查记录

| 项目 | 关键依赖/栈 | 本轮核查结果 |
|---|---|---|
| Isaac Sim | Windows 11 或 Ubuntu；NVIDIA RTX/驱动；Kit/资产 | 阅读 6.0 要求、许可 FAQ、官方 manipulation 示例；未安装，因本机硬件明确不满足 |
| Gazebo Harmonic / ros_gz | Ubuntu 24.04、ROS 2 Jazzy 推荐 | 阅读官方兼容与 bridge 文档；本机无可确认的 Ubuntu 环境，未运行 |
| franka_ros2 | ROS 2 Jazzy、colcon/rosdep；官方推荐 Docker | 浅克隆检查 README、LICENSE/NOTICE、包结构和最新提交；未构建 |
| MTC / moveit2_tutorials | MoveIt 2、ROS 2、C++/colcon | 浅克隆检查许可证、最新提交、pick-place 教程；未构建 |
| panda_ros2_gazebo | Ubuntu 20.04、ROS 2 Foxy、Gazebo Classic 风格、iDynTree | 浅克隆确认停更、demo 损坏和许可证元数据冲突；淘汰 |
| rosbag-fault-injection | Python ≥3.8.10、Docker、ROS 2 Galactic devcontainer、`rosbags==0.9.22` | 浅克隆检查配置/源码；直接运行关键模块触发 `NameError`；发现 `eval/exec`，不复用执行代码 |
| LLMTutor | Node/pnpm、React/TanStack、Drizzle/Postgres、AI SDK、OpenAI/Ollama | 浅克隆检查 tutor YAML、chat route、DB schema、许可证；未安装依赖 |
| LangGraph | Python ≥3.10、langchain-core、checkpoint、Pydantic 等 | 阅读官方 repo、pyproject、persistence/interrupt/security 文档；V0 暂不设为必需依赖 |
| OATutor | React 16、Material UI 4、Firebase/localForage | 浅克隆检查 BKT、skill model、hint 组织和许可证；不运行旧前端 |

## 8. 推荐的复用边界

### 可以作为锁版外部依赖

- Phase 9：Gazebo Harmonic、ROS 2 Jazzy、`ros_gz`、`franka_ros2`、MoveIt 2/MTC；
- Phase 5：按冻结技术栈锁定 LangGraph 的已修复版本，只用于 Tutor 编排；
- 条件式：获得满足要求的 RTX 环境并完成许可复核后，加入 Isaac Adapter。

### 可以小范围迁移或重写

- MTC 官方 pick-place 教程中的 stage 组织；
- Isaac 官方示例中的阶段超时、失败原因和以物体位姿判定成功的规则；
- OATutor 的 skill tag、hint ladder、低掌握度选题思想；
- Bosch 工具的 seed、时间窗和转换前后记录思想。

### 只参考、不复制

- LLMTutor 的产品交互、Tutor YAML 和日志结构；
- `rosbag-fault-injection` 的执行器源码；
- `panda_ros2_gazebo` 的所有实现；
- 任何外部项目的长 prompt、题目内容和 UI 资产。

## 9. Phase 1 的输入清单

Phase 1 应基于本文冻结以下 schema/contract，而不是提前写仿真或 Tutor 实现：

1. Device、Training Module、Case、Learner Session、Skill 五类 schema；
2. Tutor Contract、Simulation Adapter Contract、API Contract；
3. ST-001 的公开上下文、隐藏 ground truth、evidence catalog、allowed checks、fault config、scoring rules；
4. Session Schema 内最小可审计 trace 字段，以及 Tutor 所需 Public State 的边界；
5. 第三方依赖的版本/许可证登记方式。

Episode Recorder 的完整 schema、通用 Fault Injection 执行层和 Auto Case Generation 分别属于冲奖增强线的 Phase 10–12，不提前扩大 Phase 1。Phase 1 只需要让 Case 中已有的 `fault` 和 Simulation Adapter 契约保持未来可扩展。

## 10. 总体判定

外部项目能够显著降低“仿真接入、规划任务、对话编排、学习分析概念验证”的成本，但**没有任何一个项目可以替代 SimTrouble 的五项核心自主资产**：Training Model、Case Schema、Diagnostic State Machine、Tutor Policy、Skill Model。最稳妥的路线是：先用自有 Mock 完成训练闭环；真实仿真以开放、官方、可组合的 Gazebo/ROS 2/Franka/MTC 栈作为首选 Adapter；Isaac 作为具备硬件和许可条件后的增强 Adapter；Tutor 和画像只吸收外部项目的成熟模式，不让其 prompt、旧前端或统计模型主导架构。
