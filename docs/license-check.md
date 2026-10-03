# SimTrouble Tutor 第三方许可证核查

> 状态：Phase 0 许可证尽调  
> 核查基准日：2026-10-03  
> 目的：给 Phase 1–9 的复用设定边界，不构成法律意见。

## 1. 结论

- V0 的 Training Core、Case、状态机、Tutor Policy、Skill Model 均应自研，避免把外部项目的 copyleft 文件、题目内容、prompt 或不明来源资产带入核心。
- Gazebo/ROS 2/Franka/MTC 路线的主要代码许可证为 Apache-2.0/BSD-3-Clause，适合以**外部依赖 + 独立 Adapter**方式使用，但仍必须保留许可证、版权和 NOTICE，并记录修改。
- LangGraph 为 MIT；按 Freeze Pack v0.2 在 Phase 5 作为 Tutor 编排依赖，届时必须锁定包含安全修复的版本。
- LLMTutor 为 MPL-2.0。允许与其他代码组合，但修改或分发其 covered files 会产生文件级源码提供义务；本项目没有必要承担这层耦合，因此只参考设计，不复制文件或 prompt。
- OATutor 的软件为 MIT、教学内容为 CC BY 4.0；二者不能混为一个许可证。只借鉴建模思想，不复制数学题、图片、文案或旧前端。
- Isaac Sim 的 GitHub 源码为 Apache-2.0，但运行时 Kit、扩展、资产及第三方交付条件另受 NVIDIA 条款约束。不能以“仓库是 Apache-2.0”推导整个可交付产品均可自由再分发。
- `panda_ros2_gazebo` 无根 LICENSE 且元数据互相冲突，按**权利不明、不得复制/修改复用**处理。
- 发布前必须生成 `THIRD_PARTY_NOTICES`、依赖清单/SBOM、资产溯源表和锁文件；没有许可证或来源证明的代码、模型、prompt、图片、USD/world/URDF 资产不得入库。

## 2. 核查矩阵

| 组件 | 代码/内容许可证 | 核查证据 | 允许的使用方式 | 必须履行 | 本项目决定 |
|---|---|---|---|---|---|
| [NVIDIA Isaac Sim GitHub](https://github.com/isaac-sim/IsaacSim) | GitHub 源码 Apache-2.0；Kit、扩展、资产和服务条件另行适用 | [官方 License FAQ](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/common/license-faq.html) | 可按 Apache 条件使用对应源码；运行/分发要逐项确认 NVIDIA EULA、资产许可和 AI Enterprise 条件 | Apache LICENSE/NOTICE；修改说明；交付形态与资产逐项复核 | V0 不依赖；后续只做隔离 Adapter，发布前二次法务核查 |
| [Gazebo](https://github.com/gazebosim/gz-sim) / `ros_gz` | 主要为 Apache-2.0，各仓库/包逐项确认 | 官方仓库 LICENSE、包清单 | 作为系统依赖或容器依赖；项目自写 world/bridge 配置 | 保留许可证、版权、NOTICE（如有），记录二进制包来源 | Phase 9 首选仿真底座 |
| [`frankarobotics/franka_ros2`](https://github.com/frankarobotics/franka_ros2) | Apache-2.0，带 NOTICE | 本轮浅克隆根 `LICENSE`、`NOTICE`；README 亦声明全部包 Apache-2.0 | 外部依赖；在 Adapter 层调用；必要时维护小型补丁 | 分发时附 Apache-2.0 和 NOTICE；修改文件需显著说明；不得暗示商标背书 | 可用，锁 commit/release；不复制进 Training Core |
| [`moveit_task_constructor`](https://github.com/moveit/moveit_task_constructor) | BSD-3-Clause | 根 `LICENSE.txt` | 外部依赖；可有限移植官方示例 | 保留版权、条件和免责声明；不得用贡献者名义背书 | 可用，优先依赖而非 vendoring |
| [`moveit2_tutorials`](https://github.com/moveit/moveit2_tutorials) | BSD-3-Clause | 根 `LICENSE.txt` | 可复制少量示例作为独立 smoke test | 在源码/二进制分发中保留版权与免责声明 | 只迁移必要片段并在文件头标注来源/commit |
| [`panda_ros2_gazebo`](https://github.com/nicholaspalomo/panda_ros2_gazebo) | **不确定**：无根 LICENSE；`package.xml` 为 BSD；`setup.py` 为 Apache | 本轮浅克隆文件核查 | 只可阅读和独立重写通用思想 | 无法靠猜测解决许可；需权利人澄清/补许可证后再评估 | **禁止复制、修改或 vendoring** |
| [`boschresearch/rosbag-fault-injection`](https://github.com/boschresearch/rosbag-fault-injection) | Apache-2.0 | 根 `LICENSE.md` | 可作为独立工具或在履约后修改；本项目不需要复制 | 附许可证/NOTICE（如有），标记修改；留意依赖的独立许可证 | 只参考配置模式，自研最小在线故障层 |
| [`SwissLearningAnalytics/LLMTutor`](https://github.com/SwissLearningAnalytics/LLMTutor) | MPL-2.0 | 根 [`LICENSE`](https://github.com/SwissLearningAnalytics/LLMTutor/blob/main/LICENSE) 和 package metadata | 可与更大作品组合；未修改文件可原样使用；修改 covered file 需按 MPL 提供相应源码 | 保留 notices；分发 covered files 时告知源码可得；修改文件仍受 MPL；不得移除声明 | 不复制代码、prompt、schema；只参考交互/架构 |
| [`langchain-ai/langgraph`](https://github.com/langchain-ai/langgraph) | MIT | 仓库 LICENSE / package metadata | 作为 Phase 5 锁版依赖，项目节点代码自研 | 在软件副本/重要部分附版权与 MIT 许可 | 许可证通过；按冻结栈使用，但不承担 Core 状态 |
| [`CAHLR/OATutor`](https://github.com/CAHLR/OATutor) 软件 | MIT | 根 [`LICENSE`](https://raw.githubusercontent.com/CAHLR/OATutor/main/LICENSE) | 可作为依赖或在保留声明后修改 | 保留版权和 MIT 许可 | 不复用旧前端/算法实现，仅借鉴思想 |
| OATutor 题目/课程内容 | CC BY 4.0 | README 的内容许可说明及内容元数据 | 可复制/改编，但必须署名、链接许可证、说明修改 | 精确作者/来源归属，CC BY 4.0 链接，修改说明，不加额外限制 | 与本项目场景无关，**不复制** |

## 3. 各许可证对实施的影响

### 3.1 Apache License 2.0

适用于 Isaac Sim 对应开源源码、Gazebo/ROS 2 的许多组件、`franka_ros2`、Bosch 故障注入工具等。项目若分发源码或包含这些组件的二进制，应：

1. 附带 Apache-2.0 许可证文本；
2. 保留源文件版权、专利、商标和归属声明；
3. 若上游有 NOTICE，将其相关内容随分发保留；
4. 对修改过的文件做显著修改说明；
5. 不将许可证的专利授权误解为商标授权。

优先以包管理器、系统包或容器外部依赖使用，减少 vendoring 和本地改动面。

### 3.2 BSD-3-Clause

适用于 MTC 和 MoveIt 2 tutorials。源码/二进制再分发需保留版权、三项条件和免责声明，且不能以版权方或贡献者名义为本产品背书。示例代码也不是“无版权代码”；若迁移到 smoke test，要在文件头和第三方清单中记录仓库、commit、原许可证、修改内容。

### 3.3 MIT

适用于 LangGraph 与 OATutor 软件。可以商用、修改、分发，但软件副本或实质性部分必须携带版权与许可文本。MIT 宽松不代表其模型输出、数据集、第三方 UI 资产或内容自动同为 MIT，仍需逐项溯源。

### 3.4 MPL-2.0

LLMTutor 的 MPL 是文件级 weak copyleft，不会自动要求整个独立项目开源；但如果把其文件复制进来并修改、再对外分发，相关 covered files 需要继续以 MPL-2.0 提供源代码和相应通知。其长 prompt 也具有版权，不能因为是配置文件就当作公共领域。

本项目没有直接复用 LLMTutor 文件的必要。最清晰的处理是：

- 不复制源码、YAML prompt、数据库 migration、UI 文案；
- 只在设计文档中引用公开事实和链接；
- 自主实现 Tutor Policy、schema、状态机和提示阶梯。

### 3.5 CC BY 4.0

OATutor 的内容许可与软件 MIT 分离。若未来确需用其题目或内容，必须保留创作者署名、作品标题/来源、许可证链接并说明修改；不得暗示原作者认可 SimTrouble。当前内容是数学教育，与工业运维无直接用途，因此完全不引入。

### 3.6 NVIDIA 组合许可

Isaac Sim 的许可必须按“代码、运行时、扩展、资产、交付方式”分层：

- GitHub 上的 Isaac Sim 源码可标为 Apache-2.0；
- Omniverse Kit、预编译扩展、纹理/USD/示例资产可能有各自条款；
- 内部研发与向第三方提供 turn-key/托管服务的权限可能不同；
- 根据官方 FAQ，输出通常不因 Isaac 运行而自动受限制，但这不解除输入资产的原许可；
- 若客户在其自有、合规的 Isaac 环境运行本项目 Adapter，许可风险通常比捆绑整个运行时交付更可控。

因此架构上采用“客户/演示环境自备 Isaac + 我方提供独立 Adapter 和自有 Case 资产”，且在任何公开发布前重新核对当时条款。

## 4. 许可证异常与红线

### 4.1 `panda_ros2_gazebo`

这是本轮最明确的许可证红旗：仓库根目录无 LICENSE，`package.xml` 写 `BSD`，`setup.py` 却写 `Apache License, Version 2.0`。许可证字段本身不是完整授权文本，且二者互相冲突。处理结论：

- 不复制其 Python、launch、URDF、world、Dockerfile 或配置；
- 不从其模型资产派生修改版；
- 可以阅读公开接口后，以官方 Franka/MoveIt/Gazebo 文档进行 clean-room 自主实现；
- 如果将来确有不可替代代码，先要求上游补充清晰 LICENSE 和资产来源。

### 4.2 不明来源机器人资产

URDF、mesh、纹理、USD、场景世界和品牌标识都可能有独立权利。即使控制代码是 Apache/MIT，也不能自动复制其模型文件。每个资产至少记录：

- 文件哈希与原始 URL；
- 作者/组织；
- 许可证及版本；
- 是否允许修改、商用、再分发；
- 归属文本和修改记录。

### 4.3 Prompt、训练题和生成内容

- 外部 prompt 按文本作品处理，不整段复制；
- 外部 Case/题库/答案不因公开可访问就可任意复用；
- AI 生成资产仍需保存生成来源、提示词、模型/日期和人工修改记录；
- 任何用户或学校提供的真实设备数据需另行确认保密、个人信息和商业秘密权限。

## 5. 依赖与安全合规

许可证通过不代表依赖安全。外部组件引入前还要：

- 锁定版本/commit 和哈希，不跟随浮动 `main`；
- 保存直接和传递依赖的 SBOM；
- 检查上游 Security Advisories/CVE；
- 将 LangGraph checkpoint、pickle/反序列化和数据库访问视为受信边界；
- 禁止使用 Bosch 示例中对不可信配置执行 `eval/exec` 的方式；
- 容器镜像记录 base image digest，不只记录 tag；
- 许可证扫描不能替代人工检查资产、内容和 NOTICE。

## 6. 入库和发布流程

### 6.1 引入第三方前

1. 在依赖登记表填写：名称、用途、版本/commit、来源、许可证、是否修改、是否分发；
2. 保存 LICENSE/NOTICE 原文或可靠链接；
3. 确认代码、内容、模型资产是否使用不同许可证；
4. 完成安全公告和维护状态检查；
5. 由模块负责人批准“依赖 / 小范围迁移 / 只参考”分类。

### 6.2 修改第三方文件时

- 只在 `third_party/` 或明确隔离的 adapter/examples 区域进行；
- 保留原文件头；
- 添加 `Modified by SimTrouble, YYYY-MM-DD` 和修改摘要；
- 记录 upstream commit，尽量以 patch 维护，避免失去更新路径；
- MPL covered file 与自有文件物理分离。

### 6.3 对外演示或发布前

至少生成：

- `THIRD_PARTY_NOTICES.md`；
- 软件依赖 SBOM；
- 资产/数据溯源表；
- OSS 源码提供说明（如存在 MPL covered files）；
- 容器及模型版本清单；
- 一次人工抽查报告。

## 7. 当前允许/禁止清单

### 允许

- 以官方包/容器依赖形式使用 Apache-2.0、BSD-3-Clause、MIT 项目；
- 按要求保留许可后，小范围迁移官方 MTC/Isaac 示例的通用任务模式；
- 独立重写公开的架构思想、接口模式和算法概念；
- 在文档中引用项目名称、事实和官方链接。

### 禁止

- 将“公开仓库”等同于“可自由复制”；
- 复制 `panda_ros2_gazebo` 的代码或资产；
- 未履行 MPL-2.0 就复制/修改/分发 LLMTutor 文件；
- 将 OATutor 的 CC BY 内容误标为 MIT；
- 把 Isaac GitHub 的 Apache-2.0 扩张解释为全部运行时/资产/服务均可任意再分发；
- 将第三方 prompt、Case、图片、mesh、USD/URDF/world 直接放入自有目录而不记录来源；
- 使用无版本锁定、无 NOTICE、无 SBOM 的外部组件参加正式发布。

## 8. Phase 0 许可裁定

| 候选 | 裁定 |
|---|---|
| Gazebo/ROS 2/Franka/MTC | **通过，限外部依赖与隔离 Adapter；履行 Apache/BSD** |
| Isaac Sim | **条件通过，仅作后续 Adapter；硬件与组合许可复核是进入门** |
| LangGraph | **许可证通过；Phase 5 按冻结技术栈引入并锁补丁版** |
| LLMTutor | **仅参考，不复制** |
| OATutor | **仅参考建模思想，不复制内容/旧前端** |
| rosbag-fault-injection | **仅参考，自研执行层** |
| panda_ros2_gazebo | **不通过，禁止代码/资产复用** |

本裁定服务于当前比赛原型。若交付形态从校内演示变为 SaaS、商业软件、预装设备或向客户分发容器，必须重新审查全部许可证、商标、资产与服务条款。
