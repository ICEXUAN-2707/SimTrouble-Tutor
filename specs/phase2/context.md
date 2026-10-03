# Phase 2 Context

## Inputs

- `SimTrouble_FreezePack_v0.2/`
- `specs/phase1/`
- `contracts/`
- `data/cases/ST-001.json`
- `docs/phase1-contract-audit.md`

## Gate status

Ready for implementation planning:

- module loading;
- Case loading;
- Session creation and private/public separation;
- explicit Evidence request by valid `evidence_id`;
- learner Action envelope recording.

Approved:

- persistent/cross-session `ProgressManager` output uses `learner-profile.schema.json`;
- `scoring_rules` is loaded and preserved as a versioned declarative list, but interpretation remains Phase 4.

## Architectural boundary

Phase 2 is pure Training Core. It may use Python and Pydantic as frozen, but it does not create FastAPI routes, SQLAlchemy persistence, UI, LangGraph, LLM, RAG or Simulation Adapter implementations.
