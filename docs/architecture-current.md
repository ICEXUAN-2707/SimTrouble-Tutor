# Current Architecture

> Status: implemented
> Authority: explanatory; Contracts and Phase Specs remain normative
> Applies to: Product v0.4 after the bounded Tutor backend foundation

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
  ├── main.py               FastAPI Scene / Session / Tutor routes
  ├── session_service.py    authoritative Session application commands
  ├── session_projector.py  learner-safe SessionView projection
  └── tutor/
        ├── context.py      learner-safe TutorRequest projection
        ├── policy.py       deterministic pedagogical decision
        ├── deepseek.py     optional DeepSeek Responses adapter
        ├── validation.py   contract, policy, action and leak checks
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
application. Product v0.4 now has FastAPI Scene, Session, Evidence, Hypothesis
and Tutor routes plus a deterministic Three.js CAD scene.

The Tutor backend can call DeepSeek, but defaults to a deterministic rule
fallback. The LLM phrases a program-selected teaching decision and cannot
mutate Session state or calculate final scores. Conversation storage and
Sessions remain process-local.

Tutor frontend binding, Tutor Trace events, Diagnosis, Evaluator, Skill Engine,
Training Report runtime, persistence, authentication, physical simulation and
multi-Case application flow are not implemented yet.

## Test structure

- `tests/contracts/`: frozen schema and interface parity;
- `tests/training_core/`: Phase 2 behavior and isolation;
- `tests/state_machine/`: approved and denied transition topology;
- `tests/session_trace/`: Trace vocabulary, timestamps, atomicity and leakage;
- `tests/phase3_integration/`: explicit ST-001 Core path.
- `tests/demo/`: ST-001 HTTP end-to-end path and real subprocess startup smoke.
- `tests/v0_4/`: Scene, Session, Tutor, provider-failure and Report contract parity.
- `apps/training_web/e2e/`: deterministic CAD playback and responsive browser smoke.
