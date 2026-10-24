# Current Architecture

> Status: implemented
> Authority: explanatory; Contracts and Phase Specs remain normative
> Applies to: Product v0.5 identity candidate stacked on Product v0.4 T4A/T4B

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
  ├── auth/
  │     ├── models.py       strict Product v0.5 public identity models
  │     └── repository.py   versioned SQLite accounts and auth sessions
  ├── evaluation/
  │     ├── evaluator.py    qualitative post-submission findings
  │     ├── scoring.py      versioned deterministic five-dimension scoring
  │     ├── report.py       TrainingReportV04 builder
  │     └── repository.py   process-local create-once reports
  └── tutor/
        ├── context.py      learner-safe TutorRequest projection
        ├── policy.py       deterministic pedagogical decision
        ├── deepseek.py     optional DeepSeek Responses adapter
        ├── providers/      provider registry and OpenAI-compatible adapters
        ├── settings.py     environment-only configuration with safe fallback
        ├── guard.py        Case-aware hidden-answer and Evidence output guard
        ├── validation.py   contract, policy and action checks
        ├── telemetry.py    bounded latency/mode/retry/fallback metrics
        ├── service.py      per-Session serialization and orchestration
        └── fallback.py     deterministic offline response

apps/training_web
  ├── src/main.ts           CAD playback and API-backed learner workflow
  ├── src/workspace-controller.ts  four-step responsive workspace navigation
  ├── src/report-renderer.ts       authoritative Report presentation
  ├── src/styles.css        localized responsive product workspace
  └── e2e/                  workflow, Tutor, Report and multi-viewport browser tests

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

The Tutor backend can call DeepSeek Responses or an approved OpenAI-compatible
provider selected by the server-side registry, but defaults to a deterministic
rule fallback. The LLM phrases a program-selected teaching decision and cannot
mutate Session state or calculate final scores. Provider configuration errors,
missing credentials and unsafe output fail closed to the same rule Tutor.
Conversation storage and authoritative training Sessions remain process-local.

Tutor frontend binding, approved request/delivery/fallback Trace events,
per-Session serialization and public-safe delivery metrics are implemented.
Diagnosis is accepted once after UPDATE; qualitative evaluation remains
separate from versioned program scoring, and the resulting report contains all
five dimensions. ST-001 Safety is explicitly `not_assessed`. The localized web
workspace now integrates Evidence, Hypothesis, Tutor, Diagnosis and Report with
the deterministic CAD scene. Sessions and reports are still process-local.
Product v0.5 adds versioned SQLite storage for accounts, revocable
authentication sessions and failed-login state only. New `/api/v0.5` training
Sessions are bound to the authenticated User ID; every Session, Tutor,
Diagnosis and Report operation checks that owner before domain work. CSRF
proof is required for authenticated writes. The legacy v0.4 anonymous surface
cannot access an account-owned Session.

Training Sessions, Reports and Tutor conversations are still process-local;
account persistence does not imply durable learning history. Physical
simulation, multi-Case flow and the one-click launcher are not implemented.
A real-provider smoke remains a credential-gated release check and is never
run in CI.

## Test structure

- `tests/contracts/`: frozen schema and interface parity;
- `tests/training_core/`: Phase 2 behavior and isolation;
- `tests/state_machine/`: approved and denied transition topology;
- `tests/session_trace/`: Trace vocabulary, timestamps, atomicity and leakage;
- `tests/phase3_integration/`: explicit ST-001 Core path.
- `tests/demo/`: ST-001 HTTP end-to-end path and real subprocess startup smoke.
- `tests/v0_4/`: Scene, Session, Tutor, provider-failure, Diagnosis/Report behavior and contract parity.
- `tests/v0_5/`: identity schemas, SQLite storage, CSRF, expiry, rate limiting and cross-user ownership.
- `apps/training_web/e2e/`: deterministic CAD playback, learner workflow, Tutor, Diagnosis/Report, recovery and responsive browser coverage.
