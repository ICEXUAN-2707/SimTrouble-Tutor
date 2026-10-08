# Phase 3 Decision Record — DG-01 to DG-04

> Decision date: 2026-10-05
> Status: APPROVED BY FROZEN-BASELINE INTERPRETATION
> Rule: absence of explicit authorization means the behavior is excluded from Phase 3 V0.

## Authority order

1. `SimTrouble_FreezePack_v0.2/`;
2. approved CCP-001/CCP-002 and `contracts/`;
3. current `specs/phase3/`;
4. ADRs only where they do not expand or contradict the above.

## DG-01 — Legal transition topology

### Decision

The complete Phase 3 V0 transition table is:

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

All other pairs are illegal, including:

- self-transitions;
- skipped stages;
- backward transitions;
- diagnostic loops;
- transitions out of `FINISH`.

### Basis

The Freeze Pack Diagnostic State Contract contains only the above directed sequence. ADR examples mention possible loops but also state that a concrete table must be frozen; no such loop table was approved. Adding loops would therefore invent behavior.

### Change rule

Any loop or rollback requires an explicit Contract/Spec change before code changes.

## DG-02 — Transition prerequisites and completion semantics

### Decision

Phase 3 V0 transition eligibility has exactly two conditions:

1. the Session's authoritative current stage equals the transition source;
2. the requested target is the single legal target listed in DG-01.

No additional Evidence count, Hypothesis content, Action result, Diagnosis payload or Reflection payload prerequisite is implemented because the frozen Session Contract does not define those transition guards.

Transitions are explicit Core commands. Evidence requests, Hypothesis updates and Action recording do not automatically advance stage.

`FINISH` is reached only through an explicit `REFLECT → FINISH` transition and is terminal. Ground Truth remains unavailable before `FINISH`.

### Basis

The frozen stage graph defines order but no business guard table. Inventing guards or automatic transitions would change training behavior without a Contract.

### Change rule

Command-specific guards or automatic advancement require a later approved Spec/CCP.

## DG-03 — Trace event semantics

### Common field semantics

- `timestamp`: timezone-aware UTC event time supplied by an injectable clock;
- `stage`: authoritative current stage immediately after the event; for rejected operations it remains the unchanged current stage;
- `action_type`: one of the Phase 3 controlled values below;
- `evidence_id`: populated only for Evidence events, otherwise `null`;
- `current_hypothesis`: authoritative Hypothesis snapshot immediately after the event;
- `tutor_hint`: always `null` in Phase 3;
- `result`: public-safe structured outcome; it must not contain Ground Truth, Optimal Path, hidden Evidence or scoring rules.

### Controlled `action_type` values

Phase 3 may emit only:

- `SessionStarted`;
- `StateTransitioned`;
- `StateTransitionRejected`;
- `ActionPerformed`;
- `EvidenceRequested`;
- `EvidenceReleased`;
- `EvidenceDenied`;
- `HypothesisAdded`;
- `HypothesisUpdated`;
- `HypothesisRejected`;
- `SessionFinished`.

Tutor, Skill, Simulation, Fault and Diagnosis payload events are excluded because their producing components/commands are not implemented in the current phase.

### Required `result` shapes

- `SessionStarted`: `{"status": "started"}`;
- `StateTransitioned`: `{"status": "accepted", "from_stage": "...", "to_stage": "..."}`;
- `StateTransitionRejected`: `{"status": "rejected", "from_stage": "...", "requested_stage": "...", "reason": "illegal_transition"}`;
- `ActionPerformed`: `{"status": "recorded"}`;
- `EvidenceRequested`: `{"status": "requested"}`;
- `EvidenceReleased`: `{"status": "released"}`;
- `EvidenceDenied`: `{"status": "denied", "reason": "evidence_not_found"}`;
- `HypothesisAdded` / `HypothesisUpdated`: `{"status": "recorded"}`;
- `HypothesisRejected`: `{"status": "rejected", "reason": "empty_hypothesis"}`;
- `SessionFinished`: `{"status": "finished"}`.

### Emission rules

- creating a Session appends exactly one `SessionStarted` at stage `START`;
- recording a valid Learner Action appends exactly one `ActionPerformed`;
- every Evidence request appends `EvidenceRequested`, then appends exactly one of `EvidenceReleased` or `EvidenceDenied`;
- a non-empty first Hypothesis appends `HypothesisAdded`;
- a later non-empty Hypothesis appends `HypothesisUpdated`;
- an empty Hypothesis appends only `HypothesisRejected`;
- a legal transition appends `StateTransitioned`;
- an illegal transition appends only `StateTransitionRejected`;
- a legal `REFLECT → FINISH` appends `StateTransitioned` followed by `SessionFinished`.

No event above implicitly changes stage. Only the explicit legal transition operation changes `current_stage`.

### Atomicity

- a successful transition updates stage and appends `StateTransitioned` as one aggregate operation;
- `REFLECT → FINISH` also appends `SessionFinished` after the successful transition;
- an illegal transition leaves all domain fields unchanged and appends only `StateTransitionRejected`;
- a successful Evidence command updates `evidence_seen` and appends its two events as one aggregate operation; a denied request appends only its request/denial events;
- a successful Hypothesis or Action command updates its existing Phase 2 field and appends its outcome event as one aggregate operation;
- existing Trace events are never updated, deleted or reordered;
- failed Evidence/Hypothesis commands preserve domain state except for their required denial/rejection Trace event.

### Basis

The seven public fields come from the frozen Session Schema. Event names are limited to ADR-006/ADR-013 concepts that can be expressed without adding fields. Rich ADR metadata remains deferred.

## DG-04 — Trace storage boundary

### Decision

Phase 3 V0 stores Trace only in the authoritative in-memory `LearnerSession.trace`.

Included:

- append-only aggregate behavior;
- defensive snapshots;
- serialization through the frozen Learner Session model;
- deterministic unit and integration tests.

Excluded:

- SQLAlchemy;
- SQLite files/tables;
- repository interfaces;
- migrations;
- restart recovery;
- multi-process consistency.

### Basis

The frozen Session Schema already contains Trace. No persistence repository Contract or database schema exists for Phase 3, and adding one would introduce unfrozen behavior and a new dependency.

### Change rule

Persistent storage must be introduced by a dedicated Backend/Persistence Spec before implementation.

## Implementation authorization

These decisions authorize only Phase 3 Session integrity, State Machine, in-memory Trace and their tests. They do not authorize API, frontend, Tutor, Skill, Simulation, Case expansion or database work.
