# Codex 开发规则

每个任务必须基于：
```text
/specs/<phase>/
├── goal.md
├── context.md
├── contract.md
├── acceptance.md
└── out_of_scope.md
```

开发前必须先输出：
- 对任务的理解
- 涉及模块
- 不会修改的模块
- 预计新增/修改文件
- 测试计划

禁止：
- 修改冻结 Schema
- 改 API
- 换技术栈
- 引入大型依赖
- 重构无关模块
- 在 Core 中引入 LLM
- 在 Core 中引入 Isaac/Gazebo
- 把 Ground Truth 传给 Tutor
- 用 LLM 直接评分
- 跳过测试

每轮交付必须输出：
- changed files
- implementation summary
- tests
- remaining risks
- contract impact
- next suggested step

外部项目复用前必须检查：
- LICENSE
- 版本
- 最近维护
- 依赖
- 可直接复用范围
