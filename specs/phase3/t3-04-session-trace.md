# T3-04 — Append-only Session Trace

> Status: IMPLEMENTED AND LOCALLY VERIFIED — pending CI and Phase-branch integration
> Branch: `task/phase3-session-trace`
> Parent: `phase/3-diagnostic-state-machine` at integrated T3-03 commit `240229f`
> Review gate: B review is explicitly deferred by the project owner for this task; CI and isolated verification remain mandatory.

## Objective

Close CA-02 and CA-04 by adding the single authoritative in-memory Trace append boundary, deterministic timezone-aware UTC timestamps and the DG-03 Session/transition events without changing the frozen seven-field `TraceEvent` shape.

## Event scope

T3-04 emits only:

- `SessionStarted` with `{"status": "started"}`;
- `StateTransitioned` with `{"status": "accepted", "from_stage": "...", "to_stage": "..."}`;
- `StateTransitionRejected` with `{"status": "rejected", "from_stage": "...", "requested_stage": "...", "reason": "illegal_transition"}`;
- `SessionFinished` with `{"status": "finished"}`.

Evidence, Hypothesis and Action events remain assigned to T3-05.

## Frozen field semantics

- `timestamp`: supplied by an injected clock, timezone-aware and normalized to UTC;
- `stage`: authoritative post-event stage; unchanged current stage for rejection;
- `action_type`: one of the four T3-04 values above;
- `evidence_id`: always `null` in T3-04;
- `current_hypothesis`: authoritative value at event creation;
- `tutor_hint`: always `null` in Phase 3;
- `result`: exactly the approved public-safe shape above.

No event may contain Ground Truth, Optimal Path, hidden Evidence or scoring rules.

## Clock contract

- production default: `datetime.now(timezone.utc)`;
- injection shape: zero-argument callable returning `datetime`;
- timezone-naive values are rejected before authoritative state is committed;
- timezone-aware non-UTC values are normalized to UTC;
- tests use deterministic clocks and never sleep;
- no ordering or monotonicity rule beyond actual event emission order is invented.

## Append and authority boundary

- `SessionTraceRecorder` is the only code allowed to append authoritative Trace events.
- Recorder methods construct controlled `TraceEvent` objects internally; callers cannot supply arbitrary action types or result shapes.
- Appended events are deep-copied into the Session.
- `CaseSession.session` remains the only external read boundary and returns a deep snapshot.
- Trace is stored only in the in-memory authoritative `LearnerSession.trace`.

## Atomic transition integration

`CaseSession.transition_to(...)` operates on a deep candidate Session:

1. copy the authoritative Session;
2. apply the T3-03 State Machine to the candidate;
3. append the required validated event or events to the candidate;
4. replace the authoritative Session only after every operation succeeds.

Legal transition:

- update candidate stage;
- append one `StateTransitioned`;
- for `REFLECT → FINISH`, append `SessionFinished` immediately after it;
- commit the candidate atomically.

Illegal transition:

- keep candidate domain fields unchanged;
- append exactly one `StateTransitionRejected`;
- commit only that Trace addition;
- re-raise `InvalidStateTransitionError`.

If clock or event validation fails, the authoritative Session remains unchanged.

## Authorized files

Expected additions:

- `core/session_trace/__init__.py`;
- `core/session_trace/clock.py`;
- `core/session_trace/trace_recorder.py`;
- `tests/session_trace/__init__.py`;
- `tests/session_trace/test_session_trace.py`.

Expected modifications:

- `core/case_engine/case_session.py`;
- `tests/state_machine/test_diagnostic_state_machine.py`;
- `tests/training_core/test_training_core.py`;
- Phase 3 acceptance and task-status documents.

No other product module is authorized. In particular, T3-04 does not modify JSON Schema, API contracts, `core/models/contracts.py`, EvidenceManager or dependency declarations.

## Required tests

1. A new Session appends exactly one valid `SessionStarted` at `START`.
2. All eight legal transitions append one `StateTransitioned` with exact fields and result.
3. `REFLECT → FINISH` appends `StateTransitioned` followed by `SessionFinished`.
4. All 73 illegal pairs append only one `StateTransitionRejected` through the aggregate while preserving every non-Trace field.
5. Trace order matches command order.
6. Mutating, deleting, replacing or reordering snapshot events does not affect authoritative Trace.
7. Mutating nested snapshot `result` data does not affect authoritative Trace.
8. Deterministic clocks produce exact UTC timestamps without sleeping.
9. A naive or failing clock leaves authoritative Session unchanged.
10. No Trace result leaks hidden Case data.
11. No SQLAlchemy, SQLite or repository dependency exists.
12. All existing 39 tests remain compatible after their expected Trace assertions are updated.

## Out of scope

- Evidence, Hypothesis and Action Trace events;
- Tutor hints or Tutor/LLM calls;
- Skill scoring or Progress changes;
- databases, repositories, migrations or restart recovery;
- public Schema/API changes or extra Trace fields;
- event IDs, sequence numbers, actors or causation metadata;
- automatic transitions, business guards, rollback edges or loops;
- generic event buses or new dependencies.

## Exit gate

T3-04 may be proposed for integration only when focused Trace tests, all existing regressions, dependency checks, forbidden-import scans and GitHub CI pass. Trace-dependent T3-05 command-event acceptance remains open.

## Contract impact

No public Contract shape change. This task implements the already frozen in-memory Trace semantics from DG-03 and DG-04.
