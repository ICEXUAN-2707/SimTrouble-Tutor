# SimTrouble Tutor — Freeze Pack v0.2

本资料包用于正式开发前的需求、架构、协作与分支治理冻结。

> 原则：先冻结 Contract，再并行开发；先在 develop 集成，再进入 integration；通过系统测试后进入 release；main 永远保持稳定可展示。

## 当前项目定位

SimTrouble Tutor 是一个面向智能设备操作与运维人员的仿真实训 AI 平台。

V0 首个场景：
- 工业机器人柔性搬运工作站
- 基础操作训练
- 异常处置训练
- AI Tutor 带教
- Diagnostic Trace
- 5 维能力画像

长期可迁移到：
- AGV
- 智能仓储
- 其他智能设备

但 V0 不扩展场景。

## 三人角色

### A — Tech Lead / Architecture & Core
负责：
- 总体技术架构
- Contract
- Core Domain
- Backend 主链路
- State Machine
- Session Trace
- Skill Engine
- 集成与技术 Release Gate

### B — Application / AI / Simulation Engineer
负责：
- Frontend
- Tutor Agent
- Knowledge Module
- Mock Simulation
- Simulation Adapter 实现
- Isaac / Gazebo 技术实验

### C — Product / QA / Pitch Lead
负责：
- 产品研究
- Case 内容审核
- Product QA
- Demo
- PPT
- 答辩题库
- 政策/竞品/价值证据

## 推荐阅读顺序

1. `01_TECH_ARCHITECTURE.md`
2. `02_CONTRACTS.md`
3. `03_GIT_BRANCH_POLICY.md`
4. `04_TEAM_RACI.md`
5. `05_DEVELOPMENT_ROADMAP.md`
6. `06_REVIEW_AND_RELEASE_GATE.md`
7. `07_CODEX_RULES.md`
8. `08_CODEOWNERS_TEMPLATE`
