# Phase 1 Acceptance

## 文件验收

- [x] 五类核心 Schema 存在并可解析。
- [x] Tutor 输入/输出 Schema 存在，且禁止字段不在输入定义中。
- [x] learner-facing Case/Evidence 使用独立安全投影，不泄漏内部故障关联或评分元数据。
- [x] Action 与 Training Report 具有可供后续阶段复用的统一契约。
- [x] Simulation Adapter 六个方法、责任边界和错误边界有文档。
- [x] API Contract 包含原冻结的 10 个路由，以及 CCP-001 唯一批准的 Learner Profile 只读路由。
- [x] `ST-001.json` 可通过 Case Schema 校验。

## 语义验收

- [x] 只看 JSON 即可说明 ST-001 的设备、任务、异常、初始观察、证据、Ground Truth、合理检查路径和安全规则字段。
- [x] Case 在不依赖 LLM 的情况下可完整表达。
- [x] Learner-facing/Tutor Contract 不暴露 `ground_truth`、未披露 Evidence 或完整 `optimal_path`。
- [x] Session 能表达当前阶段、证据、假设历史、动作、提示次数、错误分支数和五维分数。
- [x] Learner Profile 能表达跨 Session 的模块进度、五维能力和推荐 Case。
- [x] Case 能承载版本化、可解释的声明式评分规则，但本阶段不计算分数。
- [x] 没有实现 Phase 2+ 逻辑。

## 校验方式

- JSON 语法检查；
- JSON Schema 文档结构和本项目所用关键字检查；
- ST-001 对 Case Schema 校验；
- 枚举、required、`additionalProperties` 边界检查；
- 最终工作区文件和重复规范源复核。
