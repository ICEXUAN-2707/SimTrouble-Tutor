# T3-02 — Session Integrity Hardening

> Status: COMPLETED AND INTEGRATED — PR #1 merged as `62377f4`
> Branch: `task/phase3-session-integrity`
> Parent: `phase/3-diagnostic-state-machine`

## Objective

Close CA-01 and CA-03 before State Machine work:

- keep one authoritative mutable `LearnerSession` inside `CaseSession`;
- prevent callers from changing that authority through the exposed Session object;
- preserve Phase 2 Evidence, Hypothesis, Action and Progress behavior;
- reject an explicitly empty Session ID.

## Design boundary

- `CaseSession` stores the authority in a private `_session` attribute.
- The public `session` property returns a fresh defensive deep copy.
- The property has no setter.
- Existing aggregate commands mutate only `_session`.
- Evidence membership is updated through a `CaseSession` aggregate method after `EvidenceManager` validates the ID against the authoritative Case.
- UUID generation occurs only when `session_id is None`; any supplied value is validated as supplied.

This task does not freeze the future State Machine class or its method signatures. No public stage mutation method is added in T3-02.

## Files

Expected modifications:

- `core/case_engine/case_session.py`;
- `core/evidence_engine/evidence_manager.py`;
- `tests/training_core/test_training_core.py`;
- this task Spec.

No other product module is authorized.

## Acceptance

- External mutation of a Session snapshot cannot change authoritative stage, counters, lists, Actions or nested Action parameters.
- Assigning to `case_session.session` is rejected.
- Existing `record_action` and `submit_hypothesis` behavior is unchanged.
- Evidence release and de-duplication still update the authoritative Session.
- Unknown Evidence still leaves authoritative domain state unchanged.
- `session_id=None` generates a non-empty UUID.
- `session_id=''` raises frozen-model validation instead of generating another identity.
- ProgressManager accepts Session snapshots exactly as before.
- All Phase 1/2 tests pass.

## Out of scope

- legal transition rules or a stage mutation method;
- Trace creation, Trace immutability or clock handling;
- changes to JSON Schema/API;
- SQLAlchemy/SQLite;
- Tutor, Skill, frontend or Simulation;
- deep immutability refactor of TrainingCase nested dictionaries.

## Contract impact

No public field or serialized shape changes. This task strengthens the internal authority boundary required by the existing Contract.

## Integration evidence

- strict PR review found no runtime defect;
- isolated clean-worktree environment: 32/32 tests passed;
- adversarial mutation probe, dependency check and compile check passed;
- the project owner explicitly accepted the task-specific EvidenceManager authorization and the isolated test gate in place of a missing remote Check Run;
- post-merge Phase branch regression: 32/32 tests passed.
