# Phase 1 Out of Scope

本阶段明确禁止：

- 前端或页面实现；
- FastAPI、SQLAlchemy、数据库或业务 API 实现；
- TrainingModuleLoader、CaseLoader、CaseSession、EvidenceManager、ProgressManager；
- Diagnostic State Machine 实现；
- Session Trace 持久化实现；
- Skill 评分算法、权重或自动选题；
- LangGraph graph、LLM API、Prompt、RAG；
- Mock Simulation 或 Web Simulation 实现；
- Isaac Sim、Gazebo、ROS 2 安装或 Adapter 实现；
- Fault Injection、Episode Recorder、Auto Case Generation；
- 批量创建 Case；
- Kubernetes、Redis、PostgreSQL、MQ、微服务；
- 修改 Freeze Pack v0.2 的冻结需求、技术栈或分支策略。

发现未冻结的产品歧义时，停止扩展，不以代码或 Schema 偷渡默认决定。
