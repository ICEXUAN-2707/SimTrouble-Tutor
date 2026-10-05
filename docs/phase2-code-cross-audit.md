# Phase 2 Code Cross-Audit for Phase 3 Readiness

> Audit date: 2026-10-05  
> Audited baseline: `4f10c6c`  
> Scope: existing contracts, Pydantic models, Training Core, data fixtures and tests  
> Result: **T3-02 CLOSES SESSION INTEGRITY FINDINGS; STATE MACHINE/TRACE REMAIN ORDERED BEHIND THEIR TASK GATES**

## 1. Audit method

The audit traced:

```text
Freeze Pack / approved CCPs
→ JSON Schema and interface contracts
→ Pydantic runtime models
→ Phase 2 domain services
→ ST-001 and module/device data
→ unit/contract tests
→ Phase 3 authority and Trace requirements
```

Checks executed:

- all 29 repository tests: passed;
- `python -m pip check`: no broken requirements;
- branch and working tree: clean before audit;
- runtime mutation probes: executed in memory only, with no file or repository changes;
- forbidden framework import audit: passed through the existing regression suite.

## 2. Confirmed correct behavior

- Case, Module and Device data load through strict Pydantic models.
- Duplicate Case/Module/Evidence identifiers and missing Case references are rejected.
- A new Session starts at `START` with frozen defaults.
- Public Case projection excludes fault, Ground Truth, Optimal Path, scoring rules and Evidence internals.
- Evidence release returns only `id`, `type` and `content`.
- Unknown Evidence does not mutate the Session.
- Repeated Evidence requests do not duplicate `evidence_seen`.
- Learner Action and Hypothesis inputs are defensively copied/normalized.
- Progress calculation counts only `FINISH` Sessions for the selected learner.
- Core does not import FastAPI, SQLAlchemy, LangGraph, LLM, Isaac, ROS or Gazebo packages.

## 3. Findings

### CA-01 — RESOLVED IN T3-02: Session authority is encapsulated

Evidence:

- `CaseSession.session` exposes the mutable `LearnerSession` object directly.
- Pydantic assignment validation is not enabled.
- A caller can assign `current_stage = 'NOT_A_STAGE'`, set negative counters, or append an empty Evidence ID after construction.
- Existing tests directly assign `FINISH` and `OBSERVE` to Session objects when building Progress fixtures.

Closure:

- `CaseSession` keeps one internal mutable `_session` authority;
- its public `session` property returns a fresh defensive deep-copy snapshot and has no setter;
- existing aggregate commands and validated Evidence release update only the internal authority;
- negative tests prove external mutation cannot change authoritative stage, counters, lists or nested values.

This is an internal integrity correction. It does not require a JSON Schema or API change.

### CA-02 — BLOCKER: Trace is not append-only

Evidence:

- `LearnerSession.trace` is a public mutable list.
- `TraceEvent` is mutable.
- Existing events, event order and nested `result` data can be rewritten after append.

Impact:

The current model shape validates initial construction but cannot enforce the frozen append-only audit requirement.

Required closure:

- Trace writes must pass through a single Core recorder/aggregate boundary;
- appended events must be defensively copied;
- callers must receive snapshots that cannot mutate authoritative history;
- tests must attempt event replacement, deletion, reordering and nested payload mutation.

No new public Trace fields may be added without a Contract Change Proposal.

### CA-03 — RESOLVED IN T3-02: Explicit empty Session ID is rejected

`session_id=session_id or uuid` treats an explicit empty string as if no ID were supplied. The frozen Schema requires a non-empty ID, so invalid caller input should not be silently converted into a different identity.

Closure: UUID generation now occurs only when `session_id is None`; an explicit empty value reaches frozen-model validation and is rejected.

### CA-04 — MEDIUM: Trace timestamp can be timezone-naive

`TraceEvent.timestamp` currently accepts a naive Python `datetime` and serializes it without an offset. Phase 3 needs deterministic, timezone-aware audit timestamps.

Required closure:

- inject or wrap an aware UTC clock;
- reject or normalize naive values according to the approved Phase 3 internal contract;
- test serialization and ordering without sleeping or relying on wall-clock timing.

This does not authorize adding a public field.

### CA-05 — LOW: Frozen Case models are only shallowly frozen

`TrainingCase` blocks top-level field assignment, but nested dictionaries such as `initial_state`, fault parameters and Evidence content remain mutable. `CaseSession` currently protects an active Session through deep copies, so the learner isolation tests pass.

This is not a Phase 3 blocker under the current defensive-copy boundary. It remains a Phase 2 technical debt item: either enforce deep immutability later or describe the guarantee precisely as defensive isolation. Phase 3 must not expand this into an unrelated model refactor.

### CA-06 — RESOLVED IN T3-01: Approved CCPs were not fully reflected in the original Freeze Pack summary

Before reconciliation, `SimTrouble_FreezePack_v0.2/02_CONTRACTS.md` showed the pre-CCP empty `scoring_rules` example and original API route list, while the approved authoritative contract files already included versioned scoring rules and `GET /users/{user_id}/profile`.

Closure: the current task branch synchronizes the summary with already approved CCP-001/CCP-002. This is documentation reconciliation only and introduces no route or scoring behavior beyond those approvals.

### CA-07 — RESOLVED FOR PHASE 3: ADR Trace ambitions exceed the frozen Session Schema

ADR-013 describes richer event metadata such as event ID, sequence, actor and causation IDs. The frozen `TraceEvent` Schema has exactly seven fields and rejects additional properties.

DG-03 now requires Phase 3 to use exactly the frozen seven fields. Rich ADR metadata is deferred and still requires a formal CCP before any implementation.

## 4. Readiness conclusion

Phase 2 functional behavior remains stable and regression-tested. T3-02 now provides the authoritative Session boundary required before State Machine work; append-only Trace safeguards remain deliberately unimplemented until T3-04.

DG-01 through DG-04, CA-06 and CA-07 are now resolved in the Phase 3 Spec.

Phase 3 continues in the frozen task order:

1. T3-02 has closed CA-01 and CA-03;
2. after T3-02 integration, T3-03 may implement only the frozen linear transition table;
3. T3-04 closes CA-02 and CA-04 using the frozen seven-field in-memory Trace;
4. every task keeps the full Phase 1/2 regression suite green.

No Skill, Tutor, API, UI, Simulation or persistence implementation is authorized by this audit.
