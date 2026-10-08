# T3-05 — CaseSession Command Integration

> Status: COMPLETED AND INTEGRATED — PR #4 merged as `2e3554d`
> Branch: `task/phase3-case-session-integration`
> Parent: `phase/3-diagnostic-state-machine` at integrated T3-04 commit `762eb02`

## Objective

Complete the remaining DG-03 command events around the existing Phase 2 Evidence, Hypothesis and Action behaviors, then verify one ST-001 Core path from `START` through `FINISH`.

This task does not add application, HTTP, Tutor, Skill, Simulation or persistence behavior.

## Frozen command behavior

### Learner Action

- a valid existing `record_action` command deep-copies the Action into the authoritative Session;
- it appends exactly one `ActionPerformed` event with `{"status": "recorded"}`;
- it never advances the diagnostic stage.

### Evidence

- every `EvidenceManager.request` appends `EvidenceRequested`;
- a known Evidence ID updates `evidence_seen` idempotently and then appends `EvidenceReleased`;
- an unknown Evidence ID leaves non-Trace state unchanged, appends `EvidenceDenied`, then raises the existing `EvidenceNotFoundError`;
- all Evidence events populate `evidence_id`;
- released content continues to exclude internal metadata.

### Hypothesis

- the first non-empty value updates the existing fields and appends `HypothesisAdded`;
- later non-empty values update the existing fields and append `HypothesisUpdated`;
- an empty value leaves non-Trace state unchanged, appends `HypothesisRejected`, then raises the existing `ValueError`;
- Hypothesis events do not copy learner text into `result`; `current_hypothesis` is the approved snapshot field.

## Atomicity

Each command operates on a deep candidate Session and replaces the authoritative Session only after all field changes and required Trace events validate successfully.

- a successful Action/Hypothesis command commits its domain mutation and event together;
- a successful Evidence command commits `evidence_seen`, `EvidenceRequested` and `EvidenceReleased` together;
- denied Evidence and rejected Hypothesis commit only their approved Trace events before re-raising the existing domain error;
- clock or Trace validation failure commits neither domain mutation nor partial Trace;
- commands never advance `current_stage`.

## Authorized files

Product modifications are limited to:

- `core/session_trace/trace_recorder.py`;
- `core/case_engine/case_session.py`;
- `core/evidence_engine/evidence_manager.py`.

Test and status modifications are limited to:

- `tests/session_trace/`;
- `tests/training_core/test_training_core.py`;
- `tests/state_machine/test_diagnostic_state_machine.py` only if a Trace expectation requires it;
- `tests/phase3_integration/`;
- Phase 3 task and acceptance documents.

No JSON Schema, API Contract, runtime model, dependency declaration or Case data change is authorized.

## Required tests

1. Action appends exactly one `ActionPerformed` and preserves stage.
2. Known Evidence appends requested/released in order and remains idempotent in `evidence_seen`.
3. Unknown Evidence appends requested/denied, preserves non-Trace state and re-raises the existing error.
4. First and later Hypotheses append added/updated with authoritative snapshots.
5. Empty Hypothesis appends only rejected, preserves non-Trace state and re-raises the existing error.
6. Clock failure leaves Action, Evidence and Hypothesis commands fully unchanged.
7. Command events use exact DG-03 result shapes and do not leak hidden Case data or learner Action parameters.
8. One ST-001 Core path combines explicit transitions and existing commands through `FINISH` with exact event order.
9. All Phase 1–3 regression tests pass.
10. Core remains free of API, database, Tutor, Skill and Simulation dependencies.

## Out of scope

- automatic transitions or new transition guards;
- diagnosis submission payload or diagnosis correctness rules;
- HTTP/API error mapping;
- Demo server, frontend or browser tests;
- Tutor/LLM, Skill scoring or Progress changes;
- Mock/real Simulation;
- repository interfaces, SQLAlchemy, SQLite or restart recovery;
- new events, fields or result shapes outside DG-03.

## Exit gate

T3-05 is ready for Phase integration only after focused command/integration tests, the full regression suite, contract/boundary scans, GitHub CI and an isolated merge test pass.

Local evidence:

- 19 focused command/integration compatibility tests pass;
- 57 full Phase 1–3 regression tests pass;
- command failure-path atomicity and hidden-data scans pass.

## Contract impact

No public shape change. This task implements the already-approved DG-03 behavior using the frozen seven-field Trace model.
