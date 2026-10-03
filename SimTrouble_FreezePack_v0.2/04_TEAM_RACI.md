# 三人分工与 RACI

## 1. 角色

### A — Tech Lead / Architecture & Core
负责：
- 技术架构
- Contract
- Core Domain
- Backend 主链路
- State Machine
- Session Trace
- Skill Engine
- Integration
- 技术 Release Gate

### B — Application / AI / Simulation Engineer
负责：
- Frontend
- Tutor Agent
- Knowledge Module
- Mock Simulation
- Simulation Adapter
- Isaac / Gazebo 实验
- Demo 技术整合

### C — Product / QA / Pitch Lead
负责：
- 项目背景与价值
- 政策与竞品证据
- 用户故事
- Case 内容审核
- Product QA
- Demo Script
- PPT
- 答辩题库

## 2. RACI

| 工作项 | A | B | C |
|---|---|---|---|
| 总体架构 | A/R | C | I |
| Contract | A/R | C | I |
| Case Schema | A/R | C | C |
| Session Schema | A/R | C | I |
| Skill Model | A/R | C | C |
| Training Engine | A/R | C | I |
| Case Engine | A/R | C | I |
| State Machine | A/R | C | I |
| Session Trace | A/R | C | I |
| Backend API | A/R | C | I |
| Frontend | C | A/R | C |
| Tutor Agent | C | A/R | C |
| Knowledge Module | C | A/R | C |
| Mock Simulation | C | A/R | C |
| Isaac/Gazebo 调研 | C | A/R | I |
| Case 内容合理性 | C | C | A/R |
| 产品 QA | C | C | A/R |
| Demo Script | C | C | A/R |
| PPT | I | C | A/R |
| 答辩题库 | C | C | A/R |
| Release 技术验收 | A/R | R | C |
| Release 产品验收 | C | C | A/R |

A = Accountable
R = Responsible
C = Consulted
I = Informed

## 3. A 的重点
必须亲自掌握：
- Pydantic Models
- Case Engine
- Diagnostic State Machine
- Session Trace
- Skill Engine
- Integration Layer

## 4. B 的重点
优先：
- Frontend Shell
- Diagnostic Workspace
- Tutor Prototype
- Mock Simulation
- API Client
- Simulation Adapter

后续：
- Isaac / Gazebo
- Fault Injection
- RAG

## 5. C 的职责

从第一天维护：
```text
pitch/
├── background.md
├── policy-evidence.md
├── competitor-analysis.md
├── innovation.md
├── demo-script.md
├── qa-bank.md
└── screenshots/
```

## 6. 同步机制

### A + B
每 2–3 天 15–20 分钟：
- Contract
- API
- 当前 Phase
- 集成阻塞

### A + B + C
每周一次：
- 跑当前版本
- 看 Roadmap
- 检查 Demo
- 更新 PPT 证据
