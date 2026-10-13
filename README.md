# SimTrouble Tutor

SimTrouble Tutor 是面向智能设备操作与运维人员的仿真实训 AI Tutor。V0 聚焦工业机器人柔性搬运工作站，通过可控异常、诊断状态机、全过程 Trace、受约束的 AI 带教和可解释的五维能力评价，帮助学员形成基于证据的故障诊断能力。

## V0 产品范围

- 1 个工业机器人柔性搬运工作站；
- 2 类训练模块：基础操作、异常处置；
- 4 类异常：物体位姿偏移、抓取失败、障碍碰撞风险、放置目标冲突；
- 8–12 个稳定 Case，先以 `ST-001` 建立端到端基线；
- Diagnostic Trace 与 Hypothesis、Evidence、Efficiency、Updating、Safety 五维能力画像；
- Mock-first：可参赛主链路不依赖真实仿真或 LLM 可用性。

V0 不扩展到 AGV、智能仓储、多设备平台、真实设备控制、多 Agent、模型微调或预测性维护。

## 目标技术边界

```text
Presentation        Next.js / React / TypeScript
Application         FastAPI / Training Flow / API
Core Domain         Training / Case / State Machine / Trace / Skill
AI & Knowledge      Tutor Policy / LangGraph / optional LLM
Simulation          Mock Adapter / later Gazebo or Isaac Adapter
```

- Core Domain 是训练流程、状态迁移、证据释放和评分的权威；
- Tutor/LLM 不读取 Ground Truth、未释放 Evidence 或完整 Optimal Path；
- Tutor、前端和仿真器不能直接修改 Session State；
- Skill Engine 使用可解释规则，LLM 不直接决定最终分数；
- Core 不依赖具体仿真 SDK，真实仿真只能通过冻结的 Adapter 边界接入。

当前实际实现包含 Phase 1–3 的契约与 Core、隔离的初版 Demo，以及 Product v0.4 的 CAD、Session 和受约束 Tutor 后端基础：

```text
contracts / data
       ↓
Training Core
  ├─ Case / Session / Evidence
  ├─ Diagnostic State Machine
  └─ Append-only Session Trace
       ↑
apps/demo（静态页面 / HTTP / 内存编排 / Demo-only 规则）
       ↑
Product v0.4
  ├─ apps/training_web（Vite / TypeScript / Three.js CAD 工作区）
  ├─ apps/training_api（FastAPI Scene / Session / Tutor API）
  ├─ apps/training_api/tutor（Policy / DeepSeek Adapter / Rule fallback）
  └─ contracts/v0.4（Tutor / Diagnosis / Evaluator / Report）
```

当前架构与目标架构分别见 [Current Architecture](docs/architecture-current.md) 和 [Target Architecture](docs/architecture-target.md)。

## 当前状态

- Phase 0：外部项目技术尽调已完成；
- Phase 1：Contract Freeze 已完成，CCP-001/CCP-002 已批准；
- Phase 2：Training Core 已实现并通过回归测试；
- Phase 3：Diagnostic State Machine + 内存 Append-only Trace 已实现、通过 57 项回归并合入 `develop`；
- Demo v0.1：模块化壳层、ST-001 HTTP E2E 与启动烟测已实现；不代表 Phase 4–8 完成。
- Product v0.4 T1：CAD 场景、Case 驱动动画、Scene API 与 Session API 已实现。
- Product v0.4 T2A：Tutor Context、确定性 Policy、DeepSeek Adapter、输出校验和规则回退已实现。
- Product v0.4 T2B：Tutor 前端、同会话串行、公开安全 Trace、运行指标与泄漏回退已实现；真实 Key smoke 是发布前人工检查。
- Product v0.4 T3：Diagnosis、Evaluator、五维评分和 Report 尚未实现。

| 能力 | 当前事实 |
|---|---|
| ST-001 Case、Evidence、Hypothesis、Action | 已实现 |
| Diagnostic State Machine | 已实现 |
| Append-only Session Trace | 已实现 |
| ST-001 浏览器演示 | 已复用官方 Core，并由 HTTP E2E 与启动烟测覆盖 |
| ST-001 CAD 动画 | 已由 Scene JSON 驱动并通过 Product 浏览器烟测 |
| Product Session API | 已实现 Session、Evidence、Hypothesis 和公开安全投影 |
| 五维 Skill 评分 | 未实现 |
| LLM Tutor | T2B 代码闭环已实现；真实 Key smoke 需在发布前人工执行 |
| Mock / 真实物理仿真 | 确定性 Three.js 动画已实现；物理仿真不在当前 MVP |
| 数据库与账号体系 | 未实现 |

当前权威基线与阶段规格：

- [Freeze Pack v0.2](SimTrouble_FreezePack_v0.2/00_README.md)
- [Phase specs](specs/)
- [Contracts](contracts/)
- [Architecture decisions](docs/architecture-decisions.md)
- [External reuse analysis](docs/reuse-analysis.md)
- [Demo v0.1 Spec](specs/demo-v0.1/)

发生冲突时按 `Freeze Pack → 当前 Phase Spec → Contracts → 研究/产品材料` 的顺序处理；需要改变冻结 Contract 时，必须先提交并批准 Contract Change Proposal。

## 仓库结构

```text
core/                         训练核心领域实现
apps/demo/                    初版 ST-001 Demo 的可替换适配层
contracts/                    JSON Schema 与接口契约
data/                         冻结的设备、模块和 Case 数据
specs/                        各 Phase 的目标、上下文、契约和验收
tests/                        契约与核心回归测试
docs/                         尽调、ADR、审计与产品资料
SimTrouble_FreezePack_v0.2/   冻结的项目治理与技术边界
```

本仓库不保存第二份源码树；外部交付包和本机参考副本只能作为迁移输入，不能直接提交。

## 本地验证

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
```

## 运行初版 Demo

```powershell
.\.venv\Scripts\python.exe -B -m apps.demo
```

默认仅监听 `http://127.0.0.1:8000`。该 Demo 使用进程内匿名会话、确定性规则 Tutor 和 ST-001 专用判定；它不会推进正式诊断阶段，也不提供五维评分、在线 LLM、物理仿真或持久化。

## 运行 Product v0.4

在仓库根目录启动 API：

~~~powershell
.\.venv\Scripts\python.exe -B -m apps.training_api
~~~

另开终端启动 CAD 前端：

~~~powershell
Set-Location apps\training_web
npm.cmd ci
npm.cmd run dev
~~~

打开 `http://127.0.0.1:5174`。不配置 DeepSeek 时，Tutor API 会使用确定性规则回退。真实 DeepSeek 调用仅从环境变量读取密钥：

~~~powershell
$env:SIMTROUBLE_LLM_ENABLED = "true"
$env:DEEPSEEK_API_KEY = "替换成自己的Key"
$env:DEEPSEEK_MODEL = "deepseek-flash"
~~~

详细学习材料见 [LLM Tutor + DeepSeek 零基础教学手册](docs/guides/llm-tutor-deepseek-beginner-guide.md)。

## Git 协作

开发采用任务驱动的阶段分支：

```text
task/phaseX-* → phase/X-* → develop → integration/v0.x → release/v0.x → main
```

任务分支只实现一个已冻结任务；逐一合入 Phase 分支并运行测试。Phase 完整验收通过后才能进入 `develop`。`main` 只保存通过发布门的稳定、可展示版本。详见 [Git Branch Policy](SimTrouble_FreezePack_v0.2/03_GIT_BRANCH_POLICY.md)。

## 许可证

仓库尚未声明项目级开源许可证。未经许可，不应将本仓库代码视为可自由复制或再分发的软件。第三方依赖和参考项目的许可结论见 [license-check.md](docs/license-check.md)。
