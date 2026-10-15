# Demo v0.1 Context

## Approved baseline

- Phase 1 Contracts are frozen.
- Phase 2 Training Core is implemented.
- Phase 3 State Machine and in-memory append-only Trace are integrated into `develop`.
- The user-provided `zjh/SimTrouble_Tutor_源码与演示/` package contains a useful static ST-001 presentation prototype but also contains an outdated duplicate of the repository.

The local package is migration input only. The Demo task may extract and refactor its presentation assets and rules, but it must import the official repository `core/` and `data/`.

## Approved early-Demo scope

- ST-001 only;
- static HTML/CSS/JavaScript presentation;
- Python standard-library HTTP adapter;
- process-local anonymous sessions;
- deterministic rule Tutor;
- Demo-only ST-001 diagnosis judge;
- no online dependency.

This is a pre-release demonstration slice, not completion of Phase 4–8.

## Design intent

Temporary capabilities are isolated under `apps/demo/`. Core remains reusable and framework-free. Later Next.js, FastAPI, LangGraph/LLM, persistence and Simulation work replace adapters rather than rewrite CaseSession, Evidence, State Machine or Trace.
