# Phase 1 Contract Scope

## 权威输入

1. `SimTrouble_FreezePack_v0.2/01_TECH_ARCHITECTURE.md`
2. `SimTrouble_FreezePack_v0.2/02_CONTRACTS.md`
3. `SimTrouble_FreezePack_v0.2/05_DEVELOPMENT_ROADMAP.md`
4. `SimTrouble_FreezePack_v0.2/06_REVIEW_AND_RELEASE_GATE.md`
5. `SimTrouble_FreezePack_v0.2/07_CODEX_RULES.md`

## 交付位置

```text
contracts/
├── schemas/
│   ├── device.schema.json
│   ├── training-module.schema.json
│   ├── case.schema.json
│   ├── case-public.schema.json
│   ├── action.schema.json
│   ├── evidence-public.schema.json
│   ├── learner-session.schema.json
│   ├── learner-profile.schema.json
│   ├── skill.schema.json
│   ├── tutor-context.schema.json
│   ├── tutor-response.schema.json
│   └── training-report.schema.json
├── api-contract.md
├── simulation-adapter-contract.md
└── tutor-contract.md

data/cases/ST-001.json
```

## 强约束

- 所有 JSON Schema 使用同一规范版本并禁止未声明的顶层字段。
- `ground_truth` 和完整 `optimal_path` 仅存在于服务端 Case，不属于 learner-facing Case 或 Tutor Context。
- `case-public.schema.json` 只是服务端 Case 的安全投影视图，不新增领域实体。
- `evidence-public.schema.json` 只表示已经由 Core 授权披露的 Evidence，排除内部关联故障和信息价值。
- 未披露 Evidence 不进入 Tutor Context。
- Tutor 输出只允许 `intent`、`message`、`suggested_next_step`。
- Core 只依赖 Simulation Adapter 六个方法，不依赖 Isaac、ROS 或 Gazebo 类型。
- API 路由集合不得超出 Freeze Pack v0.2。
- 经 2026-10-04 批准的 CCP-001 增加唯一扩展路由 `GET /users/{user_id}/profile`，用于实现冻结的 Dashboard/ProgressManager 需求。
- Skill 只冻结五个维度和数值容器，不实现评分算法。
- ST-001 严格使用 Object Pose Offset / Object Pose Mismatch 场景。

## 非决策项

本阶段不冻结数据库表、前端 view model、LLM provider、LangGraph graph、仿真 transport、具体评分权重、跨 Session 聚合算法、自动选题算法或 Episode 格式。
