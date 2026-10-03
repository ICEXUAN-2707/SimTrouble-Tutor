# Git Branch Policy v0.2

## 1. 总体模型

```text
feature/*
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

## 2. 分支职责

### `main`
- 当前稳定、可展示版本
- 禁止直接 push
- 只接受 `release/* → main`
- 必须经过人工 Demo Checklist
- 必须打 tag

### `develop`
- 当前最新开发集成版本
- 所有 feature 先进入 develop
- 可继续开发新功能
- 保持基本可运行

### `feature/*`
示例：
```text
feat/case-engine
feat/state-machine
feat/skill-engine
feat/tutor-agent
feat/dashboard
feat/mock-simulation
```

规则：
- 从 develop 拉出
- 一个分支只对应一个 Spec
- 单元测试通过后 PR → develop
- 合并后删除

### `integration/v0.x`
用途：
- 前后端联调
- Tutor + Core 联调
- Case 流程测试
- E2E
- Mock Simulation 联调

规则：
- 不允许新增功能
- 只允许修集成问题
- 阶段性创建、用完删除

Bug 修复：
```text
fix/session-api
fix/tutor-state
```

修复后同步回：
- develop
- integration/v0.x

### `release/v0.x`
允许：
- bug fix
- UI fix
- 文案
- Demo 修正
- 小型性能优化

禁止：
- 新功能
- 大改 Schema
- 技术栈切换
- 架构重构

发布：
```text
release/v0.1 → main
tag v0.1.0
```

## 3. 第一次完整发布流程

```text
feat/*
↓
develop
↓
Phase 1–6 功能完成
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
1. 对应哪个 Spec / Phase
2. 修改哪些文件
3. 未修改哪些 Out of Scope
4. 如何测试
5. 是否影响 Contract
6. 是否新增依赖
7. 验收标准是否通过

## 5. Review 机制

- A 写 Core，B Review
- B 写 Application / AI，A Review
- Contract / Schema / API 必须 A Review
- Product / UX / Case 内容由 C 验收

## 6. CI

### feature → develop
- unit tests
- schema validation
- lint

### develop → integration
- unit tests
- API tests
- integration tests
- case flow tests

### integration → release
- E2E
- frontend build
- backend startup
- 8–12 Case smoke tests
- Agent fallback test

### release → main
人工：
- Demo Checklist
- Product QA
- 答辩脚本验证
- 截图 / 录屏确认

## 7. Contract 冲突

若代码实现需要改 Contract：
1. 停止编码
2. 提交 Contract Change Proposal
3. A 审核
4. 更新 `/contracts`
5. 双方确认
6. 再改代码

**Contract 冲突先于 Code 冲突解决。**
