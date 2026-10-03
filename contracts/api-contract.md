# API Contract v0

## 原则

- 本阶段只冻结 Freeze Pack v0.2 已列出的路由集合，不实现 FastAPI。
- learner-facing API 不得返回服务端完整 Case。
- `GET /cases/{case_id}` 返回 `case-public.schema.json` 投影，排除 `fault`、initial hidden state、Evidence 内容/内部元数据、`ground_truth`、`optimal_path` 和 `scoring_rules`。
- Evidence 只能通过 Session evidence 命令按 Core 规则披露。
- learner-facing Evidence 使用 `evidence-public.schema.json`，不得包含服务端的 `related_faults` 或 `information_value`。
- Ground Truth 只允许在 Session 已进入 `FINISH` 后的 Report 中出现。

## 冻结路由

| Method | Path | 最小输入 | 输出契约 |
|---|---|---|---|
| GET | `/modules` | 无 | `TrainingModule[]` |
| GET | `/modules/{id}` | module id | `TrainingModule` |
| GET | `/cases/{case_id}` | case id | `CasePublicState` |
| POST | `/sessions` | `user_id`, `case_id` | `LearnerSession` |
| GET | `/sessions/{session_id}` | session id | `LearnerSession` |
| POST | `/sessions/{id}/evidence` | `evidence_id` | 已授权披露的 `ReleasedEvidence` + 更新后 Session |
| POST | `/sessions/{id}/hypothesis` | `hypothesis` | 更新后 Session |
| POST | `/sessions/{id}/action` | `LearnerAction` | action result + 更新后 Session |
| POST | `/sessions/{id}/diagnosis` | `diagnosis` | 更新后 Session |
| GET | `/sessions/{id}/report` | session id | 仅 `FINISH` Session 的 `TrainingReport` |
| GET | `/users/{user_id}/profile` | user id | 跨 Session 的 `LearnerProfile`，供 Dashboard 与 ProgressManager 使用 |

## Schema 映射

- `TrainingModule` → [`schemas/training-module.schema.json`](schemas/training-module.schema.json)
- `CasePublicState` → [`schemas/case-public.schema.json`](schemas/case-public.schema.json)
- `LearnerSession` → [`schemas/learner-session.schema.json`](schemas/learner-session.schema.json)
- `LearnerAction` → [`schemas/action.schema.json`](schemas/action.schema.json)
- `ReleasedEvidence` → [`schemas/evidence-public.schema.json`](schemas/evidence-public.schema.json)
- `TrainingReport` → [`schemas/training-report.schema.json`](schemas/training-report.schema.json)
- `LearnerProfile` → [`schemas/learner-profile.schema.json`](schemas/learner-profile.schema.json)

## 未冻结项

HTTP status code 细表、错误响应 envelope、分页、认证、数据库 ID、幂等键和 OpenAPI 生成方式不在 Freeze Pack v0.2 中，本阶段不擅自决定。它们必须在 Backend API 的后续 Spec 中冻结。
