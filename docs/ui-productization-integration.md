# SimTrouble UI 审核与整合计划

## 审核结论

`apps/training_web` 已通过静态审查、生产构建、前端模拟契约测试、真实后端端到端测试和多视口检查。前端继续使用既有 `/api/v0.4` 契约，没有要求修改训练 API、学习状态机或报告结构。

本轮已修复：

- 修复 Windows 中文路径下测试截图路径被错误编码的问题。
- 清理中英文替换后遗留的异常空格，并移除隐藏兼容区中的英文文案。
- 补齐真实证据字段的中文映射，包括夹持状态、方向、期望位置、实际位置和目标点状态。
- 将报告中的 `mm` 和案例代号规范化显示为“毫米”和“当前案例”。
- 移除 `sourceText` 修改页头 DOM、追加“小字提示”的副作用。
- 补上故障标注缺失的警示色变量，删除已无对应 DOM 的旧视图立方体样式和锁定圆点装饰。
- 修复报告渲染器中的空行噪声和测试中的旧文案断言。
- 增加页面质量断言：无可见英文、无重复 DOM 标识、可见表单控件均有可访问名称。

## 执行分支

本次整合没有覆盖原始脏工作区，而是以与远端同步的 `task/product-v0.4-llm-optimization` 为基线建立：

```text
task/product-v0.4-ui-productization
```

整合在独立 worktree 中执行；通过全部门禁后提交并推送。

## 合并白名单

以下内容已复制到目标分支的 `apps/training_web`：

```text
index.html
package.json
src/main.ts
src/styles.css
src/report-renderer.ts
src/ui-copy.ts
src/workspace-controller.ts
src/fonts.css
public/fonts/**
e2e/ui-fixture-flow.mjs
e2e/smoke.mjs
e2e/smoke-ci.mjs
e2e/learning-flow.mjs
e2e/diagnosis-report-flow.mjs
e2e/tutor-scenarios.mjs
```

其中 `public/fonts/**` 必须连同字体许可证一起迁移。字体文件约 2.4 MB，使用 `unicode-range` 按需加载，可换取离线和不同系统下更稳定的中文显示。

以下文件已经与目标基线逐字节一致，不需要覆盖：

```text
package-lock.json
src/learning-types.ts
```

`vite.config.ts` 原始版本与来源一致；本分支在此基础上新增了 Three.js 独立分包配置。

## 不应合并的内容

```text
node_modules/
dist/
qa/*.png
HANDOFF.md
BASELINE_HANDOFF.md
DEVELOPMENT.md
VALIDATION.md
CHANGED_FILES.txt
SPEC.md
```

前三项是依赖、构建产物和测试截图。其余文件是网页版开发过程材料，不属于运行代码；如需留档，应单独放到 `docs/archive/ui-v1/`，不要混入前端应用根目录。

## 推荐提交顺序

1. `feat(web): 引入中文产品化工作台布局`
   - 页面结构、控制器、文案映射、样式和字体资源。
2. `test(web): 覆盖中文界面与多视口完整流程`
   - 模拟契约测试、真实后端端到端测试和质量断言。
3. `docs(web): 记录 UI 整合边界与验证结果`
   - 仅保留面向维护者的最终文档。

## 合并门禁

在目标分支根目录执行：

```powershell
python -B -m pytest -q
Set-Location apps/training_web
npm.cmd ci
npm.cmd audit --audit-level=high
npm.cmd run build
$env:SIMTROUBLE_CHROMIUM='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
npm.cmd run test:ui
```

随后分别启动真实后端与前端，再执行：

```powershell
$env:SIMTROUBLE_BROWSER_CHANNEL='msedge'
npm.cmd run test:e2e:ci
```

合并必须满足：Python 测试全绿、生产构建成功、依赖无高危漏洞、模拟契约测试成功、真实端到端测试成功、所有目标视口无横向溢出、报告页无可见英文。

## 剩余风险与后续任务

- Three.js 已从业务入口拆成独立缓存块；业务入口由约 585 KB 降至 26.44 KB，但 HTML 仍会预加载 Three.js。真正的延迟加载方案见 [首屏模块拆分计划](frontend-performance-plan.md)。
- 前端只规范化经过验证的公开术语。未来接入新案例或新 LLM Provider 时，后端 Guard 应继续强制中文输出并增加真实响应测试，不能依赖前端猜测翻译。
- 当前字体资源覆盖范围较全。若部署带宽成为约束，可基于正式案例字库重新子集化，但必须保留常用汉字和许可证。
- UI 已写入独立产品化分支，原始工作区和 LLM 优化基线分支均保持不变。
