# D1 测试结果

日期：2026-10-10
分支：`task/demo-v0.1-experience-d1`

## 1. 自动化测试

### D1 Demo 定向测试

命令：

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.demo.test_demo_http_e2e -v
```

结果：**4/4 通过**，耗时 2.578 秒。

覆盖：

- ST-001 公开流程、真实 Core Trace 与会话重置；
- Cookie 会话隔离与服务端生成标识；
- E02 在授权释放前的客户端防泄漏；
- D1 视觉控制存在性与禁止新增阶段接口。

### 完整 CI 同构回归

命令：

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

结果：**62/62 通过**，耗时 4.533 秒。

基线为 60 项。本轮净增 2 项：

1. `test_e02_value_is_absent_until_authorized_release`
2. `test_d1_visual_controls_stay_on_the_existing_demo_surface`

原有 60 项无删减、无跳过、全部继续通过。

## 2. 静态与启动检查

| 检查 | 实际结果 |
|---|---|
| 内嵌 JavaScript 语法编译 | 通过：`inline script syntax: ok` |
| 受保护 E02 片段静态扫描 | 通过：`protected leak scan: clean` |
| `git diff --check` | 通过，无空白错误 |
| 本地健康检查 | 通过：`{"status":"ok","case":"ST-001","mode":"demo-v0.1"}` |
| 依赖检查 | 未新增 package、构建链或大型仿真/前端框架 |

## 3. 验收矩阵

| 验收项 | 状态 | 证据 |
|---|---|---|
| 原 60 项回归测试 | 通过 | 完整测试 62/62，其中原 60 项全通过 |
| D1 防泄漏测试 | 通过 | 初始、E01/E03 后均无受保护片段；E02 后可合法读取 |
| ST-001 基本流程 | 通过 | HTTP E2E 覆盖取证、假设、Tutor、诊断、重置 |
| 动画不修改 Core 状态 | 通过（结构门禁） | 控制器仅修改 DOM；页面无阶段变更 API；Core 阶段测试仍通过 |
| E01/E02/E03 真实响应驱动 | 通过 | 渲染只读取 `state.released[*].content` |
| Journey 只使用真实 Trace | 通过 | 只迭代 `state.trace`，无本地事件数组或伪写入 |
| 加载/错误/重试 | 通过（代码与自动化静态门禁） | busy 锁、内联 error、原请求 retry |
| 键盘/焦点/reduced-motion/小屏 CSS | 通过（代码门禁） | 原生控件、`:focus-visible`、媒体查询与横向溢出约束 |
| 三视口截图和人工交互 | **本轮跳过** | 用户明确指示跳过；未生成、未伪造截图 |
| 授权文件范围 | 通过 | 仅前端、Demo 测试和 D1 文档进入提交 |

## 4. 截图与人工浏览器验收说明

原计划使用浏览器自动化完成三视口验收，但 Windows 沙箱辅助进程持续报 `helper_unknown_error: setup refresh had errors`。切换到系统 Edge 截图时进程未稳定产出文件。用户随后明确要求跳过浏览器截图验收。

因此：

- `docs/demo-upgrade/screenshots/` 未提交虚假或空白截图；
- 不宣称 1280×720、768×1024、390×844 已人工验收；
- PR 审查时仍可补做这三档视口、Tab 顺序、焦点、动画控制和横向溢出检查。

## 5. 总体判定

代码、隐私边界、HTTP 行为和完整回归均通过。由于三视口截图与人工交互被明确跳过，D1 达到“可提交审查”的代码状态，但若严格按原始 D1 全部验收条款判断，应标记为：**自动化通过，人工浏览器验收待补/经用户本轮豁免**。
