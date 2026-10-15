# Current Architecture

> Status: implemented
> Authority: explanatory; Contracts and Phase Specs remain normative
> Applies to: Product v0.4 after the T3 diagnosis/report backend

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

apps/training_api
  ├── main.py               FastAPI Scene / Session / Tutor / Diagnosis / Report routes
  ├── session_service.py    authoritative Session application commands
  ├── session_projector.py  learner-safe SessionView projection
  ├── evaluation/
  │     ├── evaluator.py    qualitative post-submission findings
  │     ├── scoring.py      versioned deterministic five-dimension scoring
  │     ├── report.py       TrainingReportV04 builder
  │     └── repository.py   process-local create-once reports
  └── tutor/
        ├── context.py      learner-safe TutorRequest projection
        ├── policy.py       deterministic pedagogical decision
        ├── deepseek.py     optional DeepSeek Responses adapter
        ├── validation.py   contract, policy, action and leak checks
        ├── telemetry.py    bounded latency/mode/retry/fallback metrics
        ├── service.py      per-Session serialization and orchestration
        └── fallback.py     deterministic offline response

apps/training_web
  ├── src/main.ts           Three.js CAD scene and deterministic playback
  ├── src/styles.css        responsive CAD workspace
  └── e2e/                  desktop and mobile browser smoke

contracts/v0.4
  └── Tutor, Diagnosis, Evaluator and Training Report schemas
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

The standard-library Demo remains a rollback adapter, not the Product v0.4
application. Product v0.4 now has FastAPI Scene, Session, Evidence, Hypothesis,
Tutor, Diagnosis and Report routes plus a deterministic Three.js CAD scene.

The Tutor backend can call DeepSeek, but defaults to a deterministic rule
fallback. The LLM phrases a program-selected teaching decision and cannot
mutate Session state or calculate final scores. Conversation storage and
Sessions remain process-local.

Tutor frontend binding, approved request/delivery/fallback Trace events,
per-Session serialization and public-safe delivery metrics are implemented.
Diagnosis is accepted once after UPDATE; qualitative evaluation remains
separate from versioned program scoring, and the resulting report contains all
five dimensions. ST-001 Safety is explicitly `not_assessed`. Sessions and
reports are still process-local. Frontend Diagnosis/Report integration,
persistence, authentication, physical simulation and multi-Case flow are not
implemented yet. A real-provider smoke remains a credential-gated release
check and is never run in CI.

## Test structure

- `tests/contracts/`: frozen schema and interface parity;
- `tests/training_core/`: Phase 2 behavior and isolation;
- `tests/state_machine/`: approved and denied transition topology;
- `tests/session_trace/`: Trace vocabulary, timestamps, atomicity and leakage;
- `tests/phase3_integration/`: explicit ST-001 Core path.
- `tests/demo/`: ST-001 HTTP end-to-end path and real subprocess startup smoke.
- `tests/v0_4/`: Scene, Session, Tutor, provider-failure, Diagnosis/Report behavior and contract parity.
- `apps/training_web/e2e/`: deterministic CAD playback and responsive browser smoke.
