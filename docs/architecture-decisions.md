# SimTrouble Tutor Phase 0 架构决策记录

> 状态：已形成 Phase 0 决策，供 Phase 1 契约冻结使用  
> 决策日期：2026-10-03  
> 上位约束：`SimTrouble_FreezePack_v0.2/`（当前唯一冻结基线）  
> 若本文与 Freeze Pack v0.2 冲突，以 Freeze Pack v0.2 为准并立即修订本文。

## 0. 项目理解与不变量

SimTrouble Tutor V0 是“工业机器人柔性搬运工作站”的仿真驱动运维培训闭环。它通过可控异常训练学员沿 `Evidence → Hypothesis → Check → Update → Diagnose` 形成诊断推理，并根据全过程生成 Hypothesis、Evidence、Efficiency、Updating、Safety 五维能力画像。

核心创新不是 pick-and-place 动作本身，而是把异常组织成**可重复、可观察、可带教、可评价**的训练 Case，并让受程序约束的 Tutor 动态引导。以下五项必须由本项目自主掌握：

1. Training Model；
2. Case Schema；
3. Diagnostic State Machine；
4. Tutor Policy；
5. Skill Model。

不变量：

- V0 只做 1 个工作站、2 个训练模块、8–12 个稳定 Case；
- 真实仿真不可阻塞训练闭环，Mock 是正式 Adapter，不是临时假数据脚本；
- LLM 看不到 ground truth、完整 optimal path 和未释放 evidence；
- 程序控制状态迁移、证据释放、评分和安全门，LLM 只输出受限教学表达；
- 每个重要动作和状态变化进入 append-only trace；
- Training Core 不 import `isaacsim`、ROS 或 Gazebo 专属包。

## ADR-001：V0 采用 Mock-first，真实仿真是可替换 Adapter

**状态：接受。**

### 背景

比赛需要稳定展示 3–5 分钟训练闭环。仿真环境安装、GPU、机器人模型、规划器和碰撞配置均可能引入与培训创新无关的高风险。

### 决策

- Phase 1–8 的可交付主路径为 `MockSimulationAdapter`；
- Training Core 只依赖冻结的 Simulation Port；
- Phase 9 再接真实 Adapter，失败时产品仍能用 Mock 完整演示；
- Mock 和真实 Adapter 必须通过同一 contract tests，输出同一种 normalized state、result 和 Episode。

### 后果

优点是可重复、可测试、可演示；代价是 Phase 1 必须认真定义真实可映射的 contract，不能为了 Mock 方便而制造真实平台无法提供的魔法字段。

## ADR-002：真实仿真首选 Gazebo/ROS 2 官方栈，Isaac 为条件式备选

**状态：接受。**

### 决策

优先级定义为：

1. **V0 运行主路径：Mock**；
2. **首选真实 Adapter：Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic + 官方 `franka_ros2` + MoveIt 2/MTC**；
3. **条件式增强 Adapter：Isaac Sim 6.x**，前提是有满足官方要求的 RTX 工作站、通过 license gate，并完成最小场景烟测。

### 理由

- 当前工作机只有 Intel Iris Xe，无 NVIDIA RTX，Isaac Sim 6.0 明确不可行；
- Gazebo/Jazzy/Harmonic 是官方推荐组合，主要许可证宽松；
- `franka_ros2` 和 MTC 活跃，能提供官方机器人集成和分阶段 pick-place；
- Isaac 的官方 pick-place/失败语义成熟，适合作为 Adapter 设计参照，但不是 V0 成败依赖。

### 环境门

真实 Gazebo 工作开始前必须在目标 Ubuntu 主机完成一次版本锁定的 smoke test：启动 world、生成机器人和物体、读取物体 pose/TF/关节状态、执行一次 MTC pick-and-place、得到可判定 action result、干净 reset。未通过前不得把真实仿真写入比赛关键路径。

Isaac 工作开始前必须证明 GPU/驱动/VRAM/磁盘满足官方要求，并核对 Kit/资产/交付许可。

## ADR-003：拒绝复用旧社区 Panda 一体化 demo

**状态：接受。**

### 决策

不复制、不 fork、不 vendoring `nicholaspalomo/panda_ros2_gazebo`。

### 理由

- 最后提交为 2021-10-23；
- 依赖 Ubuntu 20.04、ROS 2 Foxy 和旧 Gazebo 生态；
- README 明示 `picknplace`、`pickninsert` 已损坏；
- 根目录无 LICENSE，`package.xml` 与 `setup.py` 的许可证声明冲突。

### 替代

用官方 `franka_ros2`、Gazebo、MoveIt/MTC 文档组合；本项目独立实现 Adapter、world、Case 映射和判断逻辑。

## ADR-004：Simulation Port 保持最小且平台中立

**状态：接受；Phase 1 冻结字段。**

### Port 方法

```text
reset_scenario(case_id)
get_state()
perform_action(action)
get_evidence(evidence_id)
inject_fault(fault_config)
get_result()
```

### 规范状态

Phase 1 应至少能表达：

```text
object_pose     position + quaternion + frame + timestamp
target_pose     position + quaternion + frame
gripper_state   OPEN | CLOSING | CLOSED | HOLDING | UNKNOWN
task_status     IDLE | RUNNING | SUCCEEDED | FAILED | TIMEOUT | ABORTED
collision_risk  NONE | WARNING | COLLISION | UNKNOWN
sim_time        monotonic simulation time
```

以上是架构方向，不是最终 JSON Schema。特别规定：

- `target_pose` 来源是 Case/任务语义，不强求仿真器提供同名 topic；
- `task_status` 必须由 Adapter 聚合 action result、阶段超时、碰撞和最终物体位姿；
- 抓取成功不能仅以夹爪闭合判断；
- 放置成功必须以释放后的物体 pose 落入容差区判断；
- 所有 pose 明确 frame、单位和时间戳。

## ADR-005：故障注入和 Episode Recorder 自研、平台内聚

**状态：接受。**

### 决策

- 通用 `FaultSpec` 属于 Case/Training Core contract；
- 具体注入动作属于 Simulation Adapter；
- State Monitor 将平台信号归一化；
- Episode Recorder 记录输入、注入、状态快照和结果；
- 不直接复用 Bosch rosbag 工具，不在 V0 引入通用 fault framework。

本 ADR 只冻结未来边界：真实仿真 Adapter 在 Phase 9，通用 Fault Injection 在 Phase 10，Episode Recorder 在 Phase 11，Auto Case Generation 在 Phase 12。可参赛 V0 的 8–12 个 Case 仍由 Mock 按 Case `fault` 字段确定性呈现，不提前建设上述增强子系统。

### 必备语义

- 可重放 seed；
- 明确 trigger、duration/until、expected observable；
- 注入幂等，reset 后无残留；
- trace 同时记录计划触发与实际触发；
- 对 Tutor 和学员隐藏 fault ground truth；
- Adapter 失败与“训练 Case 中设计的设备故障”分开编码。

### 四类异常映射

| Case fault | Adapter 行为 |
|---|---|
| `object_pose_offset` | reset 前/后按 spec 移动物体，保留可观察位姿证据 |
| `grasp_failure` | 让 close 不产生 HOLDING/attach，或在命名阶段使抓取超时 |
| `obstacle_collision_risk` | 插入/移动障碍，规划场景和碰撞监视器可观察 |
| `placement_target_conflict` | 目标区被占用或目标约束冲突，使检查可发现但不直接暴露结论 |

## ADR-006：Diagnostic State Machine 是唯一权威流程状态机

**状态：接受。**

权威状态序列：

```text
START → OBSERVE → INVESTIGATE → HYPOTHESIZE → TEST
      → UPDATE → DIAGNOSE → REFLECT → FINISH
```

所有入口动作先经程序校验，产生显式 transition event。Tutor、LLM、前端和仿真器均无权绕过状态机写入下一个状态。

允许从 TEST 返回 INVESTIGATE/HYPOTHESIZE、从 UPDATE 返回 TEST 等受规则约束的循环；具体 transition table 在 Phase 1 冻结。非法跳转返回结构化拒绝并进入 trace，而不是静默忽略。

## ADR-007：Evidence Release 属于 Training Core，位于 Tutor 前置边界

**状态：接受。**

### 决策

Evidence Release 在 `EvidenceEngine/CaseSessionService` 完成，LLM 不拥有 unrestricted evidence tool。

```text
Learner action
  → State Machine authorization
  → Evidence release rule / cost / safety check
  → append EvidenceReleased
  → update Session
  → build PublicStateProjection
  → Tutor Policy
  → optional LLM generation
  → output validation + trace
```

### 安全边界

Public projection 只含：公开 Case context、已释放 evidence、学员自己的假设/动作、当前允许的教学目标和必要能力摘要。明确排除：ground truth、完整 optimal path、未释放 evidence、评分密钥、未来状态答案。

## ADR-008：Tutor 采用确定性 Policy + 可选 LLM 表达层

**状态：接受。**

### 输入与输出

Tutor 输入应是 PublicStateProjection，不是原始 Case。输出严格为：

```json
{
  "intent": "question | hint | explain | reflect",
  "message": "...",
  "suggested_next_step": "..."
}
```

### Policy 顺序

1. 安全规则；
2. 状态机允许的教学动作；
3. Evidence/Hypothesis 缺口；
4. learner level 和提示升级计数；
5. 输出 intent 与内容约束；
6. LLM 生成或模板回退；
7. schema、长度、泄漏和禁用指令校验。

LLM 超时、无 key、输出不合规或疑似泄漏时，必须使用确定性模板，训练仍可继续。

## ADR-009：Phase 5 使用 LangGraph，但不让它承担产品状态

**状态：接受。**

### 决策

按 Freeze Pack v0.2 的冻结技术栈，Phase 5 使用 LangGraph 编排 Tutor。图保持为薄层：调用项目自有 Tutor Policy、可选 LLM Port、输出校验和模板回退；Case/Session 规则不迁入 LangGraph。

### 约束

- 图 state 是 CaseSession 的只读公共投影，不是第二事实源；
- 所有副作用放在可幂等、可重试的边界；
- `interrupt()` 前不做不可重复写入；
- 使用应用自身的 `thread_id`，不信任客户端随意指定的 checkpoint；
- 锁定包含安全修复的版本，禁用不可信对象反序列化。

## ADR-010：动态提示采用可解释阶梯，不用自适应黑盒

**状态：接受。**

### 提示层级

- L0：元认知问题；
- L1：指向证据类别；
- L2：给出具体检查方向；
- L3：bottom-out procedural cue；
- Safety override：任何层级下均可强制停止/检查安全风险。

### 升级规则

由重复无效检查、错误分支数、反证后未更新、步骤预算、已请求提示次数等离散信号决定。每次决策写入 `TutorPolicyApplied(rule_id, inputs, level, reason)`。学员正确收敛不升级；完成诊断后进入反思，才允许解释 ground truth。

## ADR-011：Skill Model 使用事件证据和版本化规则评分

**状态：接受。**

五维为 Hypothesis、Evidence、Efficiency、Updating、Safety。状态机、Evidence Engine 和 Tutor 只产生行为事件；独立 Skill Evaluator 把事件转成：

```text
dimension + delta/score + confidence + rule_id + reason + event_ref
```

Session 结束后聚合为五维结果，再更新 learner profile。所有结果保存 `scoring_rule_version`，使历史 trace 可重算。

V0 不使用 BKT、IRT、AFM/PFA、RL 或 LLM 单独打分。原因是 Case 数和样本量不足、行为不是单一对错观测、比赛需要可解释和可复现。

## ADR-012：Case 内容与 Learner Session 严格分离

**状态：接受。**

### Case（版本化、不可变）

包含公开上下文、隐藏 ground truth、evidence catalog/release rules、expected reasoning、allowed checks、fault config、scoring rules、skill tags、版本和来源。

### Session（每次训练、可变）

包含 learner、case_version、当前 diagnostic state、hypotheses、released evidence IDs、动作/提示计数、append-only trace、结果和评分证据。

修改 Case 必须生成新版本，既有 Session 始终指向启动时的 Case version，避免复盘结果漂移。

## ADR-013：Trace 是审计事实流，视图均可重建

**状态：接受。**

至少记录：

- `SessionStarted`
- `StateTransitioned`
- `ActionPerformed`
- `EvidenceRequested` / `EvidenceReleased` / `EvidenceDenied`
- `HypothesisAdded` / `HypothesisUpdated` / `HypothesisRejected`
- `FaultPlanned` / `FaultInjected`
- `SimulationStateObserved`
- `TutorPolicyApplied` / `TutorResponded`
- `DiagnosisSubmitted`
- `SkillEvidenceEmitted`
- `SessionFinished`

事件包含 `event_id`、session/case version、单调序号、时间、actor、payload schema version、causation/correlation ID。UI 对话、诊断轨迹、评分和演示回放从该流派生，避免多套互相矛盾的日志。

## ADR-014：LLM 与外部输入均不可信

**状态：接受。**

- Tutor 输出先过 JSON/schema、intent 白名单、长度、ground-truth/hidden-evidence 泄漏检查；
- `suggested_next_step` 只是建议，不能作为命令执行；
- Case 内容中的自由文本视为数据，防止 prompt injection；
- 不把 secrets、数据库对象、完整隐藏 Case 传给模型；
- 记录 provider/model/prompt-policy version、latency 和回退原因，但不记录密钥；
- 评分只由程序规则产生；
- 仿真动作必须映射到明确 action enum 和参数约束。

## ADR-015：许可证与供应链是架构门，不是发布末尾补项

**状态：接受。**

- 外部依赖记录 repo、version/commit、hash、license、NOTICE、用途和修改；
- 软件、内容、机器人模型/mesh/纹理/world/USD 分别记录许可；
- 优先 external dependency，不随意 vendoring；
- `panda_ros2_gazebo` 禁止复用；LLMTutor/OATutor/Bosch 仅按 `license-check.md` 的范围使用；
- 发布前生成 SBOM、`THIRD_PARTY_NOTICES` 和资产溯源表。

## ADR-016：Phase 1 只冻结契约，不提前实现 Phase 2+

**状态：接受。**

下一阶段产出仅包括：

1. Device、Training Module、Case、Learner Session、Skill schemas；
2. ST-001 完整 Case；
3. Tutor Contract；
4. Simulation Adapter Contract；
5. API Contract 草案；
6. 与上述契约直接相关的示例和 schema validation tests。

Diagnostic State Machine 的完整实现与事件流在 Phase 3，Skill 算法在 Phase 4，LangGraph/LLM 在 Phase 5，真实仿真在 Phase 9，Fault Injection、Episode Recorder、Auto Case Generation 在 Phase 10–12；Phase 1 不抢跑。

禁止在 Phase 1 顺手安装 Isaac/Gazebo、接 LLM、做前端、写真实 Adapter 或扩展新业务范围。

## ADR-017：实现技术栈遵循 Freeze Pack v0.2，不在 Phase 0 换栈

**状态：接受。**

- Core/Backend：Python、FastAPI、Pydantic、SQLAlchemy、SQLite、Pytest；
- Frontend：Next.js、React、TypeScript；
- AI：LangGraph + LLM API，BM25/Embedding 仅作为后续可选能力；
- Simulation：V0 Mock/Web Simulation，V1/冲奖线才接 Isaac 或 Gazebo；
- Infra：GitHub、GitHub Actions、`.env`，Docker 可选。

V0 不引入 Kubernetes、Redis、PostgreSQL、消息队列或微服务拆分。真实 Gazebo Adapter 内部允许使用 ROS 2 作为仿真通信机制，但 Core/API 只看四个冻结的规范字段；“使用 ROS 2 实现 Adapter”不等于把 ROS 2 类型或更多传感器接口扩散进 V0 Contract。

## 1. 目标逻辑架构

```text
┌────────────────────────── UI / API ──────────────────────────┐
│ Case briefing │ Training workspace │ Trace │ Skill profile   │
└──────────────────────────────┬───────────────────────────────┘
                               │ commands / queries
┌──────────────────────── Training Core ────────────────────────┐
│ CaseCatalog ── CaseSessionService ── DiagnosticStateMachine   │
│                      │                 │                       │
│                EvidenceEngine     TraceStore                  │
│                      │                 │                       │
│                PublicStateProjector   SkillEvaluator          │
│                      │                         │               │
│                TutorPolicy → LLM Port     LearnerProfile      │
└──────────────────────┬────────────────────────────────────────┘
                       │ Simulation Port
        ┌──────────────┼──────────────────────┐
        │              │                      │
 MockSimulation   GazeboRosAdapter      IsaacAdapter
        │              │                      │
        └──── normalized state/result/Episode ┘
```

依赖方向始终向内：平台 Adapter 依赖 Training Core 定义的 port/schema；Training Core 不依赖任何具体仿真 SDK。Tutor 和 Skill 是消费者，不越权修改 Case 真相或状态。

## 2. 关键运行序列

### 2.1 开始 Case

```text
API → SessionService: start(case_id, learner_id)
SessionService → CaseCatalog: load immutable case_version
SessionService → SimulationPort: reset_scenario(case_id)
SessionService → SimulationPort: inject_fault(fault_config)
SessionService → TraceStore: SessionStarted/FaultPlanned/Injected
SessionService → UI: public context + allowed actions
```

### 2.2 获取证据与 Tutor 响应

```text
Learner → SessionService: request_evidence(evidence_id)
StateMachine → EvidenceEngine: authorize current-state request
EvidenceEngine → SimulationPort: get_evidence(evidence_id) [if dynamic]
EvidenceEngine → TraceStore: EvidenceReleased or EvidenceDenied
Projector → TutorPolicy: public projection only
TutorPolicy → LLM Port: constrained intent/context [optional]
Validator → TraceStore/UI: TutorResponded or template fallback
```

### 2.3 完成与评分

```text
Learner → StateMachine: submit diagnosis
StateMachine → TraceStore: Diagnose/Reflect/Finish transitions
SkillEvaluator ← trace + versioned scoring rules
SkillEvaluator → LearnerProfile: five-dimensional update
EpisodeRecorder → artifact: replayable normalized episode
UI ← diagnosis explanation + evidence-backed skill report
```

## 3. 非目标与禁止耦合

明确不做：

- 不让 LLM 自动发现真实设备根因或控制机器人；
- 不把全部 Case/答案向量化后交给普通 RAG 决定教学流程；
- 不把 Gazebo/Isaac/ROS 类型直接暴露到 Case schema 或前端；
- 不为 V0 建多 Agent、知识图谱、模型微调、RL/VLA、预测性维护；
- 不为“以后可能”提前接 MES/ERP、真实私有设备或多品牌设备；
- 不以漂亮仿真替代 Case、trace、Tutor Policy 和 Skill Model 的完整性。

## 4. 风险登记与缓解

| 风险 | 触发信号 | 缓解/退出条件 |
|---|---|---|
| 真实仿真环境拖慢主线 | 两个工作日仍不能稳定 reset + 一次 pick-place | 立即回 Mock 主线；真实 Adapter 降为加分项 |
| Gazebo 机器人型号/版本错配 | FR3/Panda 模型、MoveIt config、controller 名称不一致 | 先做锁版 smoke test；Adapter 配置化 frame/joint/group，不污染 core |
| Isaac 硬件/许可不可用 | 无合规 RTX 主机或无法确认交付条款 | 不实现 Isaac Adapter，仅保留接口和调研结论 |
| LLM 泄漏答案 | 输出包含 hidden evidence/ground truth | 公共投影、禁词/实体检查、模板回退、全量 trace |
| 双状态机漂移 | LangGraph state 与 Session state 不一致 | Session 唯一事实源；图只读投影；必要时不用 LangGraph |
| 评分不可解释 | 只有总分或 LLM 主观结论 | 每分关联 rule_id/event_ref；版本化规则；支持离线重算 |
| 第三方许可污染 | 代码/资产无来源或 license 冲突 | 入库 gate；不明即不用；NOTICE/SBOM/资产表 |
| Demo 偶发失败 | 随机故障、非幂等 reset、云 LLM 不稳定 | 固定 seed、确定性 Case、模板 Tutor、Mock fallback |

## 5. Phase 0 完成判据

- [x] 完整读取并对齐工作区冻结文件；
- [x] 形成项目理解，未扩大 V0 范围；
- [x] 核查 Isaac、Gazebo/ROS 2/Franka/MTC、社区 Panda demo；
- [x] 核查故障注入、Tutor/Session、LangGraph、OATutor；
- [x] 区分直接依赖、修改/重写和只参考；
- [x] 核查主要 LICENSE、维护日期、运行前提与已知问题；
- [x] 明确 Evidence Release、Tutor/LLM、安全和评分边界；
- [x] 形成 `reuse-analysis.md`、`license-check.md`、`architecture-decisions.md`；
- [x] 未创建产品代码、前端、后端、LLM 调用或仿真安装。

## 6. Phase 1 开始前的最终 Gate

只有在团队认可以下三点后进入 Phase 1：

1. V0 以 Mock 完成比赛闭环，真实 Gazebo 是隔离加分项；
2. Diagnostic State Machine、Evidence Engine 和 Skill Evaluator 是程序权威，LLM 只是受限表达层；
3. 外部项目不替代五项自主核心资产，复用严格遵守 `reuse-analysis.md` 与 `license-check.md` 的边界。
