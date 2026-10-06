# T3-03 — Diagnostic State Machine Core

> Status: COMPLETED AND INTEGRATED — PR #2 merged as `240229f`; 39 post-merge tests passed
> Branch: `task/phase3-state-machine`
> Parent: `phase/3-diagnostic-state-machine` at integrated T3-02 commit `62377f4`

## Objective

Implement the smallest deterministic Core state-transition authority permitted by DG-01 and DG-02, while preserving the T3-02 Session boundary and all Phase 1/2 behavior.

T3-03 implements topology and rejection only. It does not implement Trace events; the final DG-03 audit behavior remains assigned to T3-04 and T3-05.

## Frozen transition table

The complete accepted table is:

| From | To |
|---|---|
| `START` | `OBSERVE` |
| `OBSERVE` | `INVESTIGATE` |
| `INVESTIGATE` | `HYPOTHESIZE` |
| `HYPOTHESIZE` | `TEST` |
| `TEST` | `UPDATE` |
| `UPDATE` | `DIAGNOSE` |
| `DIAGNOSE` | `REFLECT` |
| `REFLECT` | `FINISH` |

Every other pair is rejected, including all self-transitions, skips, backward transitions, loops and transitions out of `FINISH`.

## Command and authority boundary

- `CaseSession.transition_to(target_stage: DiagnosticStage) -> None` is the aggregate command available to callers.
- The command delegates the authoritative internal `LearnerSession` to `DiagnosticStateMachine.transition(...)`.
- `DiagnosticStateMachine` checks the single legal successor before changing `current_stage`.
- Success changes only `current_stage` in T3-03.
- Rejection raises `InvalidStateTransitionError`, an internal `TrainingCoreError` subtype.
- Rejection changes no Session field, including `trace`.
- Evidence, Hypothesis and Action commands never call `transition_to` automatically.

No mutable authoritative Session reference is exposed. No HTTP error mapping or public error envelope is defined.

## Staged Trace boundary

DG-03 requires final Phase 3 rejection and transition events, but the Trace recorder and clock do not exist until T3-04. Therefore:

- T3-03 rejected transitions leave the complete Session unchanged and raise the internal error;
- T3-03 successful transitions change only the authoritative stage;
- T3-03 does not mark final acceptance items that require `StateTransitioned`, `StateTransitionRejected` or `SessionFinished`;
- T3-04/T3-05 must add the frozen events without changing this transition table or adding guards.

This is ordered implementation work, not a change to DG-03 final behavior.

## Authorized product files

Expected additions:

- `core/state_machine/__init__.py`;
- `core/state_machine/diagnostic_state_machine.py`;
- `tests/state_machine/__init__.py`;
- `tests/state_machine/test_diagnostic_state_machine.py`.

Expected modifications:

- `core/case_engine/case_session.py`;
- `core/errors.py`.

No other product module is authorized for T3-03.

The user separately authorized `.github/workflows/contracts-and-core.yml` to run CI for every pull request. This governance change does not alter product behavior or the T3-03 product-file boundary.

## Test matrix

1. Accept each of the eight frozen edges.
2. Reject all other 73 pairs in the nine-stage Cartesian product.
3. For every rejection, compare the complete pre/post Session serialization and require equality.
4. Execute one explicit aggregate path from `START` through `FINISH`.
5. Confirm `FINISH` is terminal.
6. Confirm Evidence, Hypothesis and Action commands do not advance stage.
7. Confirm mutating a public Session snapshot still cannot change authoritative stage.
8. Confirm Trace remains unchanged in T3-03 success and rejection paths.
9. Run all Phase 1 Contract, Phase 2 Training Core and T3-02 regression tests.
10. Run dependency and forbidden-import audits.

## Out of scope

- all Trace event creation, clock injection and append-only enforcement;
- business guards based on Evidence, Hypothesis, Action, Diagnosis or Reflection data;
- automatic advancement, rollback, retry loops or recovery transitions;
- changes to stage enums, JSON Schema, API or serialized public shapes;
- Tutor, Skill, frontend, Simulation or persistence;
- new dependencies or generalized workflow frameworks.

## Exit gate

T3-03 may be proposed for integration only when:

- the eight allowed and 73 denied pairs pass deterministically;
- rejected commands are fully atomic at the pre-Trace boundary;
- the aggregate exposes no direct authoritative stage setter;
- all existing 32 tests and all new state-machine tests pass;
- no final Trace acceptance checkbox is claimed prematurely;
- Contract, dependency and Out-of-Scope audits pass.

## Contract impact

No public Contract change. T3-03 supplies only the internal Core transition authority already required by the frozen Phase 3 Contract.

## Implementation evidence

- all eight approved edges change only `current_stage`;
- all 73 unapproved stage pairs are rejected without any Session mutation;
- one explicit ST-001 aggregate path reaches `FINISH`, which remains terminal;
- Evidence, Hypothesis and Action commands do not advance stage;
- public Session snapshots cannot bypass the State Machine;
- Trace remains unchanged on successful and rejected T3-03 commands;
- 7/7 focused state-machine tests and 39/39 full regression tests pass;
- dependency, compile, forbidden-import and stage-write-boundary audits pass.
