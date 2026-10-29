# SimTrouble Tutor

## v0.5 当前可运行产品

当前产品入口为 **Product v0.5**：ST-001 三维训练工作台、注册登录与用户隔离、
证据/假设/诊断/五维报告、受约束 LLM Tutor、已完成训练 SQLite 存储及 Windows 启动器。
下方 V0 的多案例目标和目标技术边界是路线图，不代表当前全部实现。

- 本地启动：按下文安装依赖后运行 `START_SIMTROUBLE.cmd`，访问 `http://127.0.0.1:5174`。
- 验证：176 项 Python 测试、生产构建和真实 API 浏览器流程通过；
  2026-10-29 真实 DeepSeek 单次调用通过（非规则回退），凭据不随代码分发。
- [v0.5 发布说明](docs/releases/v0.5.md) · [服务器部署与回滚](deploy/README.md) ·
  [备份恢复演练记录](docs/delivery/product-v0.5/release-preparation-2026-10-28.md)。
- 本次是源码发布到 main；服务器安装、外网 HTTPS 验收和加密异机备份仍待实施。
- 训练中会话及 Tutor 对话在内存中；重启不能续训。只支持单 API worker，
  无历史记录列表界面；已完成报告可由原用户通过原 Session ID 读取。

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

当前实际实现包含 Phase 1–3 的契约与 Core、隔离的初版 Demo、Product v0.4 学习闭环，以及已合入 develop 的 v0.5 身份与训练记录能力：

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
  ├─ apps/training_api（FastAPI Scene / Session / Tutor / Diagnosis / Report API）
  ├─ apps/training_api/tutor（Policy / Provider Registry / Output Guard / Rule fallback）
  ├─ apps/training_api/evaluation（Evaluator / Skill Engine / Report Builder）
  └─ contracts/v0.4（Tutor / Diagnosis / Evaluator / Report）
       ↑
Product v0.5（M0/M1/M2 已合入 develop）
  ├─ apps/training_api/auth（SQLite Account / Auth Session / CSRF）
  ├─ /api/v0.5（认证训练 Session 与所有权校验）
  └─ apps/training_web（登录 / 注册 / 退出）
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
- Product v0.4 T2C：DeepSeek Responses 与 OpenAI-compatible Provider Registry、配置容错和 Case-aware Output Guard 已实现。
- Product v0.4 T3：一次性 Diagnosis、定性 Evaluator、确定性五维评分和 Report 后端已实现。
- Product v0.4 T4A/T4B：CAD、Evidence、Hypothesis、Tutor、Diagnosis、Report 已整合到中文响应式工作台；生产 Preview 浏览器 smoke、全量 Python 回归、依赖审计和真实 DeepSeek smoke 已通过。
- Product v0.5 M0/M2：认证边界与用户已完成训练记录已按 v0.4 → v0.5 顺序合入 develop（PR #28–#30）。
- Product v0.5 M1：Windows 本地启动器已实现并完成本地验收；Tutor 默认规则回退，启用密钥后可调用 LLM，2026-10-29 真实 DeepSeek smoke 通过。

| 能力 | 当前事实 |
|---|---|
| ST-001 Case、Evidence、Hypothesis、Action | 已实现 |
| Diagnostic State Machine | 已实现 |
| Append-only Session Trace | 已实现 |
| ST-001 浏览器演示 | 已复用官方 Core，并由 HTTP E2E 与启动烟测覆盖 |
| ST-001 CAD 动画 | 已由 Scene JSON 驱动并通过 Product 浏览器烟测 |
| Product Session API | 已实现 Session、Evidence、Hypothesis、Diagnosis、Report 和公开安全投影 |
| 五维 Skill 评分 | T3 已实现；ST-001 Safety 因无可观测机会标记为 `not_assessed` |
| LLM Tutor | T2B/T2C 已实现；真实 DeepSeek smoke 通过；其他 Provider 具备适配器，不代表已逐一实测 |
| Mock / 真实物理仿真 | 确定性 Three.js 动画已实现；物理仿真不在当前 MVP |
| 数据库与账号体系 | v0.5 保存账号、认证会话和已完成训练记录；进行中的训练仍在内存中 |

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
.\.venv\Scripts\python.exe -m pip install -r requirements-release.txt
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -v
Set-Location apps\training_web
npm.cmd ci
npm.cmd run build
npm.cmd audit
```

## 运行初版 Demo

```powershell
.\.venv\Scripts\python.exe -B -m apps.demo
```

默认仅监听 `http://127.0.0.1:8000`。该 Demo 使用进程内匿名会话、确定性规则 Tutor 和 ST-001 专用判定；它不会推进正式诊断阶段，也不提供五维评分、在线 LLM、物理仿真或持久化。

## 运行 Product v0.5 本地版

首次使用前，在仓库根目录创建本地 Python 环境并安装仓库与前端依赖：

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-release.txt
Set-Location apps\training_web
npm.cmd ci
Set-Location ..\..
~~~

复制 `.env.example` 到 Git 忽略的 `.env.local`。默认配置关闭在线 Tutor，规则 Tutor 无需密钥即可使用。
要启用 Provider，可在 `.env.local` 配置开关、Provider 和对应密钥。当前终端的环境变量优先于文件配置。
启动前可用只读预检检查依赖、配置和端口：

~~~powershell
.\.venv\Scripts\python.exe -B tools\start_product.py --check-only
~~~

双击仓库根目录的 `START_SIMTROUBLE.cmd`，或在 PowerShell 运行：

~~~powershell
.\.venv\Scripts\python.exe -B tools\start_product.py
~~~

启动器会开启 API 和 Web 服务并打开页面。按 Ctrl+C 只会停止本次启动的服务。
固定端口被占用时先关闭对应进程再重试。启动摘要会显示 Provider 状态，但不显示密钥。

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

打开 `http://127.0.0.1:5174`，先注册本地账号，再进入训练工作台。默认认证数据库为仓库根目录下被 Git 忽略的 `var/auth.db`；可用 `SIMTROUBLE_AUTH_DB_PATH` 指向其他位置。HTTPS 部署必须设置 `SIMTROUBLE_COOKIE_SECURE=true`。

M2 复用同一 SQLite 文件：登录用户完成训练时自动保存公开证据/假设快照及报告，
启动时自动执行增量建表。重启后可用原账号和训练 Session ID 通过已有接口读取记录。
本轮只做存储，不新增历史列表页面；刷新页面仍按原有行为创建新训练，未完成训练不恢复。
范围与验收见 [M2 最小存储计划](specs/product/product-v0.5/M2_STORAGE.md)。

不配置在线 Provider 时，Tutor API 会使用确定性规则回退。真实 Provider 调用仅从后端环境变量读取密钥。DeepSeek 示例：

~~~powershell
$env:SIMTROUBLE_LLM_ENABLED = "true"
$env:SIMTROUBLE_LLM_PROVIDER = "deepseek"
$env:DEEPSEEK_API_KEY = "替换成自己的Key"
$env:SIMTROUBLE_LLM_MODEL = "deepseek-flash"
~~~

### Product v0.4 浏览器验收

首次使用时在仓库根目录准备 Python 和 Web 依赖，并建立仅本机使用的配置文件：

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location apps\training_web
npm.cmd ci
Set-Location ..\..
Copy-Item .env.example .env.local
~~~

按需编辑 `.env.local` 启用 Tutor Provider。默认关闭时使用规则回退。先预检：

~~~powershell
.\.venv\Scripts\python.exe -B tools\start_product_v04_acceptance.py --check-only
~~~

双击 `START_PRODUCT_V04_ACCEPTANCE.cmd`，或运行该 Python 启动器。验收服务先执行
TypeScript 检查和生产构建，再启动 FastAPI 与 Vite Preview；浏览器访问
`http://127.0.0.1:5174`。按 Ctrl+C 只关闭本启动器创建的服务。日志写入被 Git
忽略的 `var/acceptance/logs/`，并会遮盖密钥字段。

CI 浏览器 smoke 可在无真实 Provider 凭据时运行；它会对生产 Preview 执行登录、训练、报告、
Tutor 模拟响应与回退场景：

~~~powershell
.\.venv\Scripts\python.exe -B tools\start_product_v04_acceptance.py --ci-smoke --no-browser
~~~

真实 DeepSeek smoke 是单独的显式动作，从本地 `.env.local` 读取配置，不会自动调用：

~~~powershell
.\.venv\Scripts\python.exe -B tools\deepseek_tutor_smoke.py
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
