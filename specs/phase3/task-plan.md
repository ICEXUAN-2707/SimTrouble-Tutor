# Phase 3 Task Plan

> Planning only. Every task branch starts from `phase/3-diagnostic-state-machine` and merges back one at a time after its own checks pass.

## T3-00 — Governance and Spec planning

- Branch: `task/phase3-spec-planning`
- Scope: project README, task-driven branch policy, Phase 3 five-file Spec, documentation index, this task plan.
- Product code: none.
- Exit: documents cross-checked against Freeze Pack; regression tests stay green; PR ready for Phase branch.

## T3-01 — Close transition and Trace decisions

- Planned branch: `task/phase3-transition-trace-decisions`
- Depends on: Contract Owner answers DG-01, DG-02, DG-03 and DG-04.
- Scope: record approved choices in Phase 3 Contract/Acceptance; create a Contract Change Proposal only if an existing public contract must change.
- Product code: none.
- Exit: complete executable transition table, prerequisites, Trace semantics and storage boundary exist with no unresolved interpretation.
- Status: BLOCKED pending explicit decisions; no option is recommended or selected by this plan.

## T3-02 — Diagnostic State Machine core

- Planned branch: `task/phase3-state-machine`
- Depends on: T3-01 merged.
- Scope: implement only the approved transition table, prerequisites and Core-internal rejection behavior; unit tests for every allowed and denied edge.
- Excludes: Trace persistence, Phase 2 action auto-transition, API/Tutor/UI.
- Exit: State Machine tests pass; no Session mutation on rejected transition; Phase 1/2 regression remains green.

## T3-03 — Append-only Session Trace

- Planned branch: `task/phase3-session-trace`
- Depends on: T3-01 merged; integrates with the approved T3-02 State Machine boundary.
- Scope: implement approved Trace creation and append behavior using the frozen `TraceEvent` shape.
- Conditional boundary: repository/database work is included only if DG-04 explicitly selects it; otherwise it is prohibited.
- Exit: Trace contract, ordering, immutability, leakage and failure-path tests pass.

## T3-04 — CaseSession integration

- Planned branch: `task/phase3-case-session-integration`
- Depends on: T3-02 and T3-03 merged into the Phase branch.
- Scope: connect State Machine and Trace to the existing Phase 2 Session without changing public Schema/API; add ST-001 path integration tests.
- Exit: one approved `START → FINISH` path passes; all relevant invalid paths preserve Session state; Phase 1/2 regressions pass.

## T3-05 — Phase 3 integration gate

- Planned branch: `task/phase3-integration-gate`
- Depends on: T3-01 through T3-04 merged.
- Scope: acceptance coverage audit, full test run, boundary/import audit, documentation status update; defect fixes limited to Phase 3 scope.
- Exit: every applicable item in `acceptance.md` is checked with evidence; no Decision Gate remains open; Phase branch is ready for PR to `develop`.

## Integration order

```text
T3-00
  ↓
T3-01 (decision gate)
  ↓
T3-02
  ↓
T3-03
  ↓
T3-04
  ↓
T3-05
  ↓
phase/3-diagnostic-state-machine → develop
```

After every task merge into the Phase branch:

1. run the task's focused tests;
2. run all previously integrated Phase 3 tests;
3. run Phase 1/2 regression tests;
4. verify Contract and Out of Scope boundaries;
5. stop integration if any failure or unapproved decision is found.

No Phase 4+ task may be scheduled on the Phase 3 branch.
