# 技术架构冻结 v0.2

## 1. 分层架构

```text
┌─────────────────────────────────────┐
│  ① Presentation Layer               │
│  Next.js / React / TypeScript       │
├─────────────────────────────────────┤
│  ② Application Layer                │
│  FastAPI / Training Flow / API      │
├─────────────────────────────────────┤
│  ③ Core Domain Layer                │
│  Training Engine                    │
│  Case Engine                        │
│  Diagnostic State Machine           │
│  Session Trace                      │
│  Skill Engine                       │
├─────────────────────────────────────┤
│  ④ AI & Knowledge Layer             │
│  Tutor Agent / LangGraph            │
│  Knowledge / RAG                    │
├─────────────────────────────────────┤
│  ⑤ Simulation Layer                 │
│  Mock Adapter                       │
│  Isaac / Gazebo Adapter             │
└─────────────────────────────────────┘
```

## 2. 架构原则

- Core Domain 不依赖具体仿真器。
- LLM 不拥有 Ground Truth。
- Skill Engine 使用可解释规则，LLM 不直接决定最终分数。
- Simulation 是可替换数据源。
- 任何跨模块变更先改 Contract，再改代码。

## 3. 推荐技术栈

### Core / Backend
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- Pytest

### Frontend
- Next.js
- React
- TypeScript

### AI
- LangGraph
- LLM API
- 后续可选 BM25 / Embedding

### Simulation
- V0: Mock / Web Simulation
- V1: Isaac Sim 或 Gazebo

### Infra
- GitHub
- GitHub Actions
- `.env`
- Docker 可选

V0 不引入：
- Kubernetes
- Redis
- PostgreSQL
- MQ
- 微服务拆分

## 4. 推荐仓库结构

```text
simtrouble-tutor/
├── frontend/
├── backend/
├── core/
│   ├── models/
│   ├── training_engine/
│   ├── case_engine/
│   ├── state_machine/
│   ├── session_trace/
│   ├── evidence_engine/
│   ├── skill_engine/
│   └── tutor_policy/
├── simulation/
│   ├── adapters/
│   └── fault_injection/
├── knowledge/
├── data/
├── contracts/
├── specs/
├── docs/
├── pitch/
└── tests/
```

## 5. 模块 Owner

### A / Tech Lead
Owner:
- `core/`
- `contracts/`
- `specs/`
- `backend/api/`
- `backend/cases/`
- `backend/sessions/`
- `backend/scoring/`

### B / Application & AI
Owner:
- `frontend/`
- `backend/tutor/`
- `knowledge/`
- `simulation/`

### C / Product & Pitch
Owner:
- `pitch/`
- `docs/product/`
- Case 内容审查
- UI/流程验收
