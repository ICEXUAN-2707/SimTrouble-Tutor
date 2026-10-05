# Phase 3 Task Plan

> Planning only. Every task branch starts from the latest `phase/3-diagnostic-state-machine` and merges back one at a time after its own checks pass.

## Audit basis

- Freeze Pack v0.2 and approved CCP-001/CCP-002;
- Phase 1 Contract schemas and interface contracts;
- completed Phase 2 Training Core;
- `docs/phase2-code-cross-audit.md`;
- Phase 3 Decision Gates DG-01 through DG-04.

No task below may infer an unresolved product behavior from an implementation convenience.

## T3-00 — Governance and Spec planning

- Branch: `task/phase3-spec-planning`
- Status: COMPLETED and integrated into the Phase branch.
- Scope: project README, task-driven branch policy, Phase 3 five-file Spec, documentation index and initial task plan.
- Product code: none.
- Evidence: 29 regression tests passed before and after integration.

## T3-01 — Close decisions and reconcile the approved baseline

- Branch: `task/phase3-transition-trace-decisions`
- Status: COMPLETED; ready for integration into the Phase branch.
- Scope:
  - record explicit DG-01, DG-02, DG-03 and DG-04 decisions;
  - publish the complete executable transition table and prerequisites;
  - define Trace semantics within the frozen seven-field shape;
  - synchronize `02_CONTRACTS.md` with already approved CCP-001/CCP-002 without inventing new behavior;
  - retain the code cross-audit and final implementation plan.
- Product code: none.
- Exit:
  - DG-01 through DG-04 are closed in `decision-record.md`;
  - no contradiction remains between the Phase 3 Spec and approved Contract;
  - CA-06 is reconciled and CA-07 is resolved in favor of the frozen seven-field Trace;
  - 29 regression tests pass.

## T3-02 — Session integrity hardening

- Branch: `task/phase3-session-integrity`
- Status: IMPLEMENTED; 32 tests pass; ready for PR review and integration.
- Depends on: T3-01 merged into the Phase branch.
- Scope:
  - close CA-01 by preventing exposed references from mutating authoritative Session state;
  - make Diagnostic State Machine the only stage-write boundary;
  - close CA-03 so UUID generation occurs only for an omitted Session ID;
  - adapt existing Evidence/Action/Hypothesis code to the encapsulated Session aggregate;
  - preserve the frozen Learner Session fields and serialized shape.
- Excludes:
  - legal transition behavior;
  - Trace event generation/persistence;
  - API, database, Tutor, Skill and Simulation work.
- Required tests:
  - external mutation attempts cannot alter authoritative state;
  - illegal stage/counter/list mutation cannot enter the aggregate;
  - explicit empty Session ID fails;
  - all Phase 1/2 tests remain green.

## T3-03 — Diagnostic State Machine core

- Planned branch: `task/phase3-state-machine`
- Depends on: T3-01 and T3-02 merged.
- Scope:
  - implement only the DG-01 transition table;
  - enforce the DG-02 topology-only conditions;
  - add a Core-internal rejection error without defining HTTP status codes;
  - test every allowed edge and representative denied edges.
- Excludes:
  - Trace persistence;
  - API/Tutor/UI;
  - any automatic transition or business guard.
- Exit:
  - valid transitions are deterministic;
  - invalid requests cause no domain-state mutation beyond the required rejection Trace;
  - no caller can bypass the State Machine to advance stage;
  - Phase 1/2 and T3-02 regressions pass.

## T3-04 — Append-only Session Trace

- Planned branch: `task/phase3-session-trace`
- Depends on: T3-01 through T3-03 merged.
- Scope:
  - close CA-02 with a single append boundary and immutable external snapshots;
  - close CA-04 with an injectable timezone-aware UTC clock;
  - implement only the DG-03 field semantics, action vocabulary and result shapes;
  - use the frozen `TraceEvent` field set;
  - keep Trace only inside the in-memory authoritative Session as required by DG-04.
- Required tests:
  - deterministic timestamp and ordering;
  - append, read and failure paths;
  - attempts to replace, delete, reorder or mutate an existing event do not alter authoritative Trace;
  - no Ground Truth, Optimal Path, hidden Evidence or scoring key leakage;
  - the in-memory DG-04 boundary has no database/repository dependency.

## T3-05 — CaseSession command integration

- Planned branch: `task/phase3-case-session-integration`
- Depends on: T3-02 through T3-04 merged.
- Scope:
  - add the approved DG-03 Trace events around existing Evidence, Hypothesis and Action commands;
  - keep stage transitions explicit and separate from those commands;
  - preserve Phase 2 public projections and data isolation;
  - add an ST-001 Session path integration test using only approved transitions.
- Excludes:
  - FastAPI route implementation or HTTP errors;
  - Diagnosis payload/domain implementation not present in the frozen Session model;
  - Tutor, Skill scoring, Mock/real Simulation;
  - new Case content.
- Exit:
  - one approved `START → FINISH` path passes;
  - every integrated denied command is atomic and auditable according to DG-03;
  - existing Phase 1/2 behavior remains compatible.

## T3-06 — Phase 3 integration gate

- Planned branch: `task/phase3-integration-gate`
- Depends on: T3-01 through T3-05 merged.
- Scope:
  - full acceptance coverage audit;
  - complete regression and boundary/import audit;
  - Contract/Out-of-Scope review;
  - update Phase 3 status documentation;
  - defect fixes limited to approved Phase 3 behavior.
- Exit:
  - every applicable item in `acceptance.md` has test evidence;
  - no Decision Gate or code-integrity gate remains open;
  - all tests pass from a clean checkout;
  - Phase branch is ready for PR to `develop`.

## Integration order

```text
T3-00 completed
  ↓
T3-01 decisions + baseline reconciliation
  ↓
T3-02 Session integrity
  ↓
T3-03 State Machine
  ↓
T3-04 Trace
  ↓
T3-05 command integration
  ↓
T3-06 integration gate
  ↓
phase/3-diagnostic-state-machine → develop
```

After every task merge into the Phase branch:

1. run the task's focused tests;
2. run all previously integrated Phase 3 tests;
3. run all Phase 1/2 regression tests;
4. verify Contract and Out-of-Scope boundaries;
5. stop integration on any failure, contract drift or unresolved decision.

No Phase 4+ task may be scheduled on the Phase 3 branch.
