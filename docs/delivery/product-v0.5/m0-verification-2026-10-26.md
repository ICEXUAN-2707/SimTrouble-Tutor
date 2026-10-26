# M0 集成验证进度（2026-10-26）

本轮依据根工作区 `docs/m0-acceptance-matrix.md` 的最新安排执行：
`M0 → M2 → M1 → 部署验收`。这是开发集成基线，尚未达到发布条件。

## 基线与改动

- v0.4 验证基线：`151690e`，含第 4 步解锁修复。
- v0.5 验证基线：`f66eb92`，含账号归属、认证过期清理及第 4 步修复。
- 独立分支：`task/product-v0.5-m0-verification`。
- 独立工作区：`.tmp/m0-verification`。根工作区原有改动保留。
- 使用工作区独立的 `var/auth.db`，不使用根工作区的账号数据库。

修复身份分支的浏览器验收脚本：补上第 4 步测试函数导入，为新增回归注册登录，
打开证据面板后再等待卡片可见，用直接子元素选择器替换不存在的 `Locator.children()`，
等待退出引发的页面重载后再登录，并明确检查刷新后的身份恢复。
认证过期专项入口支持 `SIMTROUBLE_BROWSER_CHANNEL=msedge`，默认仍使用 Playwright Chromium。

CI 为 M0 任务分支启用 push 检查，并将高危依赖审计加入门禁。
没有新增依赖，没有修改公开 API、冻结 Schema、Core 状态规则或评分。

## 本地验证

| 检查 | 结果 |
| --- | --- |
| v0.4 全量 unittest | 131 项通过 |
| v0.4 TypeScript 与生产构建 | 通过 |
| v0.4 前端模拟契约浏览器测试 | 通过；含四种视口与故障恢复 |
| v0.4 真实 API 浏览器 E2E | 通过；含第 4 步、报告、回退、三种报告视口 |
| v0.4 npm audit | 0 漏洞 |
| v0.5 全量 unittest | 156 项通过；含跨用户归属、认证、CSRF、过期及 v0.4 回归 |
| v0.5 TypeScript 与生产构建 | 通过 |
| v0.5 npm ci / npm audit | 通过；0 漏洞 |
| v0.5 认证过期专项浏览器测试 | 通过；真实服务撤销认证后清空学习状态 |
| v0.5 完整浏览器 E2E | 通过；含注册/退出/登录/刷新恢复、认证撤销清理、第 4 步与三视口完整报告 |
| Git diff 空白检查 | 通过 |

浏览器为 Windows 本机 Edge 无头模式，API 监听 `127.0.0.1:8001`，Vite 开发服务
监听 `127.0.0.1:5174`。本轮不将开发服务的 E2E 作为正式生产构建服务验收。
Tutor 使用规则回退；成功、超时、畸形输出及泄漏响应的浏览器场景使用受控响应，
不能据此声称真实在线 Provider 调用通过。

复现身份分支验收：在仓库根目录启动 API，另开终端启动 Web，再执行：

```powershell
# API：可使用主工作区 .venv 的 Python；从当前工作区启动以加载当前代码。
python -B -m apps.training_api

# Web 终端
Set-Location apps/training_web
npm.cmd ci
npm.cmd run build
npm.cmd audit --audit-level=high
npm.cmd run dev

# 测试终端，在 apps/training_web 下执行
$env:SIMTROUBLE_BROWSER_CHANNEL = 'msedge'
npm.cmd run test:auth-expiry
npm.cmd run test:e2e:ci
```

## 尚未完成的门禁

1. 远端 CI：Git fetch 成功，但 GitHub Actions REST 查询返回 HTTP 403；本机没有 `gh`。
   不将无法读取的远端检查标为通过。
2. 身份修复分支需要按现有 PR 审核流程合入 v0.5 Phase。
3. v0.4 与 v0.5 进入 develop 时使用 merge 保留共享历史，不能使用旧报告中的 rebase 建议。
4. M2：先冻结小型 SQLite 存储约定，再保存用户拥有的训练记录和已完成报告；
   不默认增加未完成会话续训、数据库服务、事件溯源或消息队列。
5. M1：启动器、配置预检、真实凭据 Provider smoke、桌面/平板/手机和键盘人工验收。
6. 部署：HTTPS、备份与恢复、部署与回滚。

训练会话、Tutor 对话和报告目前仍在内存中，服务重启后不会恢复。
Three.js 构建块仍超过 500 KB，延迟加载按现有性能计划另行处理。
