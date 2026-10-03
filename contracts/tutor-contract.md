# Tutor Contract v0

## 责任

Tutor 只负责解释、苏格拉底式追问、提示和训练结束后的反思表达。Tutor 不拥有业务真值、状态迁移权或最终评分权。

## 唯一允许输入

输入必须通过 [`schemas/tutor-context.schema.json`](schemas/tutor-context.schema.json) 校验：

- Training Module
- Case Public State
- Evidence Seen
- Learner Action History
- Current Hypothesis
- Current Skill Profile
- Allowed Tutor Actions

## 禁止输入

- `ground_truth`
- 完整 `optimal_path`
- 未披露 Evidence
- Case `fault`
- `scoring_rules`
- Evidence 的 `related_faults` 与 `information_value`

禁止将服务端 [`schemas/case.schema.json`](schemas/case.schema.json) 对象或服务端 Evidence 整体传给 Tutor。必须先构造 [`schemas/case-public.schema.json`](schemas/case-public.schema.json) 与 [`schemas/evidence-public.schema.json`](schemas/evidence-public.schema.json) 投影。

## 唯一允许输出

输出必须通过 [`schemas/tutor-response.schema.json`](schemas/tutor-response.schema.json) 校验，且只包含：

```json
{
  "intent": "question|hint|explain|reflect",
  "message": "string",
  "suggested_next_step": null
}
```

`suggested_next_step` 是教学建议，不是可直接执行的状态迁移或仿真命令。Tutor 输出之后仍由 Core Domain 决定状态和记录 Trace。

## Phase 1 边界

本文件只冻结数据边界。LangGraph、LLM provider、prompt、fallback 和提示策略在 Phase 5 实现。
