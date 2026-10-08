# Git Branch Policy v0.2

> 任务驱动分支修订：2026-10-05。该修订只改变协作流，不改变产品 Contract 或技术边界。

## 1. 总体模型

```text
task/phaseX-*
    ↓
phase/X-*
    ↓
develop
    ↓
integration/v0.x
    ↓
release/v0.x
    ↓
main
    ↓
tag v0.x.x
```

规则：

- 每个开发 Phase 从 `develop` 创建一个 `phase/X-*` 集成分支；
- 每个具体任务从对应的 `phase/X-*` 创建一个 `task/phaseX-*` 分支；
- 一个任务分支只对应一个已冻结任务，完成自身测试后 PR 回 Phase 分支；
- 任务逐一合入 Phase 分支，每次合入后执行相关回归；
- Phase 分支完成全量阶段集成测试和验收后，才能 PR 到 `develop`；
- 任务分支不得直接进入 `develop`、`integration/*`、`release/*` 或 `main`。

### 1.1 初版 Demo 预发布例外（2026-10-08 批准）

在 Phase 4–8 完成前，允许建立一次范围受限的初版 Demo 预发布线：

```text
task/demo-v0.1-*
    ↓
phase/demo-v0.1-integration
    ↓
develop
```

该例外只允许：

- 整理仓库与架构文档；
- 迁移 ST-001 静态演示外壳并复用官方 Core；
- 使用规则 Tutor、内存会话和 Demo-only 诊断判定；
- 添加 ST-001 HTTP E2E 与启动烟测。

该例外不代表 Phase 4–8 已完成，不得实现 Skill、LangGraph/LLM、正式 Next.js/FastAPI、Mock/真实仿真、持久化或扩展 Case。预发布能力必须在独立 `specs/demo-v0.1/` 中冻结。

## 2. 分支职责

### `main`

- 当前稳定、可展示版本；
- 禁止直接 push；
- 只接受 `release/* → main`；
- 必须经过人工 Demo Checklist；
- 必须打 tag。

### `develop`

- 已通过各 Phase Gate 的最新开发基线；
- 只接收已完成 Phase 的 PR；
- 保持基本可运行；
- 不直接承载日常任务开发。

### `phase/X-*`

示例：

```text
phase/3-diagnostic-state-machine
phase/4-skill-engine
```

规则：

- 从 `develop` 创建；
- 只集成该 Phase 已在 `/specs/phaseX/` 冻结的任务；
- 每次合入任务后执行该任务测试和受影响回归测试；
- 全部任务完成后执行完整 Phase Acceptance；
- 不得夹带后续 Phase、未批准 Contract 变更或无关重构；
- Phase 验收通过后 PR → `develop`，合并完成后关闭该 Phase 分支。

### `task/phaseX-*`

示例：

```text
task/phase3-spec-planning
task/phase3-state-machine
task/phase3-trace
```

规则：

- 从对应的 `phase/X-*` 创建；
- 一个分支只对应任务计划中的一个任务和一组明确验收标准；
- 开发前必须确认 Spec 与 Decision Gate 状态；
- 单元测试与边界测试通过后 PR → 对应 Phase 分支；
- 合并后删除；
- 发现冻结 Contract 冲突时停止编码，转 Contract Change Proposal。

### `integration/v0.x`

用途：

- 前后端联调；
- Tutor + Core 联调；
- Case 流程测试；
- E2E；
- Mock Simulation 联调。

规则：

- 不允许新增功能；
- 只允许修集成问题；
- 阶段性创建、用完删除。

集成缺陷使用 `fix/*` 分支修复，并同步回 `develop` 与当前 `integration/v0.x`。

### `release/v0.x`

允许：bug fix、UI fix、文案、Demo 修正、小型性能优化。

禁止：新功能、大改 Schema、技术栈切换、架构重构。

```text
release/v0.1 → main → tag v0.1.0
```

## 3. 首次完整发布流程

```text
task/phaseX-* → phase/X-* → develop
                         ↓
                 Phase 1–8 完成
                         ↓
                 integration/v0.1
                         ↓
                   全量集成测试
                         ↓
                    release/v0.1
                         ↓
              Demo / QA / PPT 联合验收
                         ↓
                       main
                         ↓
                      v0.1.0
```

## 4. PR 规则

所有 PR 必须写：

1. 对应哪个 Spec / Phase / Task；
2. 修改哪些文件；
3. 未修改哪些 Out of Scope；
4. 如何测试及结果；
5. 是否影响 Contract；
6. 是否新增依赖；
7. 验收标准是否通过；
8. 是否存在未关闭 Decision Gate。

## 5. Review 机制

- A 写 Core，B Review；
- B 写 Application / AI，A Review；
- Contract / Schema / API 必须 A Review；
- Product / UX / Case 内容由 C 验收。

## 6. CI 与集成测试

### `task/phaseX-* → phase/X-*`

- task unit tests；
- schema/contract validation；
- 受影响回归测试；
- scope 与依赖审计。

### `phase/X-* → develop`

- 全量 unit tests；
- Phase acceptance tests；
- Phase 集成测试；
- Contract 与 Out of Scope 审计。

### `develop → integration/v0.x`

- unit tests；
- API tests；
- integration tests；
- case flow tests。

### `integration/v0.x → release/v0.x`

- E2E；
- frontend build；
- backend startup；
- 8–12 Case smoke tests；
- Agent fallback test。

### `release/v0.x → main`

人工执行：Demo Checklist、Product QA、答辩脚本验证、截图/录屏确认。

## 7. Contract 冲突

若代码实现需要改 Contract：

1. 停止编码；
2. 提交 Contract Change Proposal；
3. A 审核；
4. 更新 `/contracts`；
5. 双方确认；
6. 再改代码。

**Contract 冲突先于 Code 冲突解决。**
