# Target Architecture

> Status: approved direction
> Authority: Freeze Pack and per-phase Specs
> Applies to: incremental V0 evolution

## Modular monolith

```text
Presentation
  initial Demo static UI → later Next.js
            │ public DTO / HTTP
            ▼
Application
  Training flow and public projections
            │ commands / ports
            ▼
Core Domain
  Case · Session · Evidence · State Machine · Trace · Skill
       │ Tutor Port                 │ Simulation Port
       ▼                            ▼
Rule Tutor → LangGraph/LLM     Mock → Gazebo/Isaac
```

The project remains one deployable application for V0. It does not introduce microservices, an event bus, a plugin framework, Redis, PostgreSQL or a message queue.

## Dependency rules

1. Presentation depends on Application, never directly mutates Session.
2. Application orchestrates explicit Core commands but does not duplicate Core state.
3. Core imports no web, LLM, persistence or simulation framework.
4. Tutor and Simulation implementations sit behind the already frozen contracts.
5. Demo-only code stays under `apps/demo/`; it must not become a second Core.
6. Persistence requires a dedicated future Spec; Phase 3 remains in-memory.

## Replaceable Demo seams

| Initial Demo | Later replacement | Core impact |
|---|---|---|
| static HTML | Next.js / React | none |
| standard-library HTTP adapter | FastAPI adapter | none |
| rule-based Tutor | LangGraph + optional LLM | none |
| process-local sessions | approved SQLite persistence | dedicated future boundary |
| ST-001 deterministic judge | approved diagnosis/Skill rules | dedicated later phase |

The initial Demo may use these temporary adapters only when its UI and release notes label them as Demo-only and do not claim unimplemented V0 capabilities.
