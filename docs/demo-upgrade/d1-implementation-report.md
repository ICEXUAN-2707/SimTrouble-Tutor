# D1 实现报告

日期：2026-10-10
分支：`task/demo-v0.1-experience-d1`
目标分支：`phase/demo-v0.1-integration`

## 1. 结论

D1 已在授权的前端、Demo 测试和文档范围内实现。Training Core、Contracts、Case、Demo Runtime、HTTP Server、正式状态机、Tutor 与评分算法均未修改，也未引入新的前端框架或仿真依赖。

代码和自动化测试已完成；三视口浏览器截图与人工交互验收按用户在本轮的明确指示跳过。因此本报告不宣称截图验收完成，D1 的代码交付可进入 PR 审查，但完整人工验收项仍标记为豁免/待补。

## 2. 开发前检查

- PR #11 已合并，合并提交为 `0b652e60e6318611eee727d91318fa3260d77e5d`。
- 已同步 `phase/demo-v0.1-integration` 并创建任务分支。
- D0 四份审计文档已作为 D1 约束基准。
- 开发前 60 项基线测试全部通过。
- 工作区中的 `DemoTask.txt` 和 `SimTrouble_Demo_Experience_Spec_v1/` 是用户输入资料，保持未跟踪且未纳入提交。

## 3. 实际修改

### `apps/demo/static/index.html`

- 将界面重构为 Graphite / Deep Teal 的工业实训工作台。
- 建立宽幅机器人工作站、右侧规则 Tutor、下方 Evidence Lab 与 Diagnostic Journey。
- 明示 ST-001、本地 Demo、视觉演绎、规则 Tutor、Demo-only 和 Core 当前阶段。
- 增加与 Core 完全分离的本地视觉状态：
  `READY → EXECUTING → GRASP_ATTEMPT → FAILURE_OBSERVED`。
- 支持开始/暂停、重播、跳过动画和视觉重置。
- E01、E02、E03 的可视效果只读取 `/api/evidence` 成功响应中的公开字段。
- E02 的实际位置与偏移量在 E02 释放后动态写入 DOM；静态 HTML/JS 不包含受保护答案。
- Journey 只迭代现有 `state.trace`。对于 Core 仅记录为 `ActionPerformed` 的事件，明确提示“未公开更细的操作分类”，不推测行为。
- 增加加载锁、内联错误提示和原请求重试入口。
- 增加键盘焦点样式、语义化按钮/表单、非颜色状态文本、响应式断点和 `prefers-reduced-motion`。
- 明示场景为“预设状态演绎、非物理仿真、非真实机器人遥测”。

### `tests/demo/test_demo_http_e2e.py`

- 新增 E02 防泄漏测试：初始 HTML、初始公开状态，以及仅查询 E01/E03 后的客户端数据均不得包含受保护数值或真因；查询 E02 后仍验证合法公开值。
- 新增 D1 前端边界测试：锁定四个视觉状态、四类控制、重试入口、reduced-motion 支持，并确认页面未引入阶段变更 API。

## 4. D1 条款映射

| 条款 | 实现 |
|---|---|
| D1.1 信息泄漏 | 先独立修复并通过定向测试，再开始视觉改造 |
| D1.2 界面改造 | 工业工作台、Tutor、Evidence Lab、Journey 和模式标识 |
| D1.3 视觉动画 | 四状态本地控制器；不调用 Core 阶段接口 |
| D1.4 Evidence 联动 | E01/E02/E03 均由真实 released response 驱动 |
| D1.5 Journey | 仅渲染 Core Trace；不生成前端伪事件 |
| D1.6 体验与质量 | 响应式、键盘原生控件、可见焦点、文本状态、reduced-motion 已实现；截图/人工浏览器验收本轮跳过 |

## 5. 明确未实现

- 未实现真实机器人通信、运动学、碰撞或物理仿真。
- 未实现在线 LLM Tutor、正式五维评分、正式状态推进或持久化学习档案。
- 未增加新的 Case、Evidence、API 路由或 Trace 字段。
- 未把视觉动画写入 Core Session、Evidence、Trace 或诊断结果。
- 未进行 D2 开发。

## 6. 风险与后续验收

- 浏览器自动化首先受到 Windows 沙箱辅助进程初始化故障阻断；随后用户明确要求跳过截图验收。因此 1280×720、768×1024、390×844 的截图和人工键盘走查没有作为本轮通过项。
- 响应式与无障碍能力已有代码门禁，但仍建议在合并前由审查者完成一次真实浏览器人工检查。
- 当前 Demo 仍是单文件前端。对于 v0.1 范围这避免了新增构建链；若未来页面继续扩大，再在获批的 D2/spec 中讨论拆分，D1 不提前工程化。
