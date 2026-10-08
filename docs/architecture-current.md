# Current Architecture

> Status: implemented
> Authority: explanatory; Contracts and Phase Specs remain normative
> Applies to: `develop` after Phase 3

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
```

## Authority boundaries

- `CaseSession` owns the authoritative mutable Learner Session and returns defensive snapshots.
- `DiagnosticStateMachine` is the only post-construction writer of `current_stage`.
- `SessionTraceRecorder` is the only append boundary for authoritative Trace.
- `EvidenceManager` validates requested Evidence against the immutable Case before asking the aggregate to commit release or denial events.
- public Case projection excludes fault, Ground Truth, Optimal Path, hidden Evidence metadata and scoring rules.

## Current runtime limitations

The repository does not yet contain a supported application server or formal frontend. It has no Skill engine, Tutor Agent, LLM, Simulation Adapter, persistence, authentication or multi-Case Demo. The local `zjh/` delivery package is an untracked migration input, not a second project or source of truth.

## Test structure

- `tests/contracts/`: frozen schema and interface parity;
- `tests/training_core/`: Phase 2 behavior and isolation;
- `tests/state_machine/`: approved and denied transition topology;
- `tests/session_trace/`: Trace vocabulary, timestamps, atomicity and leakage;
- `tests/phase3_integration/`: explicit ST-001 Core path.
