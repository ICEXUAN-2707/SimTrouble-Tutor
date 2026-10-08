# Phase 3 Out of Scope

- 新增、删除或重命名诊断阶段；
- 任何状态回环、回退、跳转、自转换或从 `FINISH` 出发的迁移；
- Evidence、Hypothesis、Action、Diagnosis、Reflection 等未冻结业务 guard 或自动状态推进；
- 修改 JSON Schema、API Contract、Tutor Contract 或 Simulation Adapter Contract；
- Skill 评分、`scoring_rules` 解释、能力聚合或推荐算法；
- Tutor Policy、LangGraph、LLM API、Prompt、RAG 或知识模块；
- FastAPI 路由、认证、HTTP 错误映射或前端/UI；
- Mock、Isaac、Gazebo、ROS、Fault Injection 或 Episode Recorder；
- 扩展 ST-001 或新增 8–12 Case；
- 自动 Case 推荐或跨 Session Progress 逻辑；
- SQLAlchemy/SQLite、数据库迁移、持久化仓库或重启恢复；
- `decision-record.md` 白名单之外的 Phase 3 Trace action type；
- 为未来 Phase 预建通用事件总线、消息队列、微服务或可插拔框架；
- 无关重构或大型依赖。

如果实现需要以上任一项，停止当前任务，返回对应 Phase Spec 或 Contract Change Proposal。
