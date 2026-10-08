# Current Architecture

> Status: implemented
> Authority: explanatory; Contracts and Phase Specs remain normative
> Applies to: Demo v0.1 integration line after D1

## Implemented modules

```text
contracts/ + data/
        │ validation
        ▼
core/models
        │
        ├── core/case_engine
        │     ├── CaseLoader
        │     └── CaseSession (authoritative aggregate)
        ├── core/evidence_engine
        │     └── EvidenceManager
        ├── core/state_machine
        │     └── DiagnosticStateMachine
        ├── core/session_trace
        │     ├── UTC clock boundary
        │     └── SessionTraceRecorder
        └── core/training_engine
              ├── TrainingModuleLoader
              └── ProgressManager

apps/demo
  ├── static/index.html     presentation only
  ├── server.py            local HTTP transport
  ├── runtime.py           in-memory orchestration / public projection
  ├── rule_tutor.py        deterministic Demo-only Tutor
  └── st001_judge.py       deterministic ST-001 Demo-only judge
             │
             └──────────── imports official core/ only
```

## Authority boundaries

- `CaseSession` owns the authoritative mutable Learner Session and returns defensive snapshots.
- `DiagnosticStateMachine` is the only post-construction writer of `current_stage`.
- `SessionTraceRecorder` is the only append boundary for authoritative Trace.
- `EvidenceManager` validates requested Evidence against the immutable Case before asking the aggregate to commit release or denial events.
- public Case projection excludes fault, Ground Truth, Optimal Path, hidden Evidence metadata and scoring rules.

## Initial Demo adapter

`apps/demo/` is a replaceable local adapter, not a second domain layer. It exposes one ST-001 browser flow, creates anonymous cookie sessions and projects the existing Core Trace. It does not copy Case data, keep a parallel event fact list or mutate Session fields directly.

## Current runtime limitations

The standard-library Demo server is a pre-release local adapter, not the planned FastAPI/Next.js application. The repository has no Skill engine, LangGraph/LLM Tutor, Simulation Adapter, persistence, authentication or multi-Case Demo. The local `zjh/` delivery package is an untracked migration input, not a second project or source of truth.

## Test structure

- `tests/contracts/`: frozen schema and interface parity;
- `tests/training_core/`: Phase 2 behavior and isolation;
- `tests/state_machine/`: approved and denied transition topology;
- `tests/session_trace/`: Trace vocabulary, timestamps, atomicity and leakage;
- `tests/phase3_integration/`: explicit ST-001 Core path.
