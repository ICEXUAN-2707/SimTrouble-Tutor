# Phase 1 Contract Cross-Audit

> Audit date: 2026-10-04  
> Authority: `SimTrouble_FreezePack_v0.2/`  
> Result: **PASS after approved CCP-001 and CCP-002; Phase 2 core is ready.**

## 1. Audit method

The review traced each frozen requirement through:

```text
Freeze Pack requirement
→ specs/phase1
→ contracts/schema or interface contract
→ ST-001 data
→ learner/Tutor exposure boundary
→ contract test
→ downstream phase consumer
```

No frontend, backend, Core, Tutor, LLM or simulation implementation was created.

## 2. Traceability matrix

| Frozen requirement | Contract evidence | Downstream consumer | Result |
|---|---|---|---|
| One industrial robot flexible-handling workstation | `device.schema.json` | Phase 2 module loading; Phase 8 Mock | PASS |
| Two module types: basic operation / exception handling | `training-module.schema.json` | `TrainingModuleLoader`, Learning Page | PASS after adding minimal `content_sections` |
| Case is executable without LLM | `case.schema.json`, `ST-001.json` | `CaseLoader`, `CaseSession` | PASS |
| Four frozen fault types | `case.schema.json#/$defs/faultType` | Phase 8/10 simulation | PASS |
| Ground Truth stays server-side | authoritative Case vs `case-public.schema.json` | Case API, Tutor | PASS |
| Hidden Evidence is not sent before release | Evidence catalog vs `evidence-public.schema.json` | `EvidenceManager`, Tutor | PASS after projection fix |
| Evidence internal metadata stays hidden | `evidence-public.schema.json` excludes `related_faults` and `information_value` | Learner UI, Tutor | PASS after leakage fix |
| Learner can choose an Evidence check | `CasePublicState.evidence_options` exposes only `id/type` | Diagnostic Workspace | PASS |
| Session records stage/evidence/hypothesis/actions/hints/wrong branches/scores | `learner-session.schema.json` | `CaseSession`, Phase 3 Trace | PASS |
| Nine diagnostic stages | Session stage enum | Phase 3 State Machine | PASS; transition rules correctly deferred to Phase 3 |
| Five skill dimensions and rule scoring | `skill.schema.json`; versioned declarative `Case.scoring_rules` | Phase 4 Skill Engine | PASS after approved CCP-002; concrete weights remain Phase 4 content |
| Tutor input excludes hidden truth | `tutor-context.schema.json`, `tutor-contract.md` | Phase 5 LangGraph/Tutor | PASS |
| Tutor output has only three fields | `tutor-response.schema.json` | Phase 5 Tutor | PASS |
| Simulation is replaceable | `simulation-adapter-contract.md` | Phase 8/9 Adapter | PASS at interface level; platform data details intentionally deferred |
| Ten API routes only | `api-contract.md` and tests | Backend/Application layer | PASS |
| Five frozen pages | public Case, module content, Session, Tutor, Training Report and Learner Profile contracts | Phase 6 UI | PASS after approved CCP-001 |
| Training Report shows truth/path/skills/reflection/next case | `training-report.schema.json` | Report Page | PASS after response contract fix |
| Phase 2 loaders/session/evidence/progress | schemas + interface contracts | Training Core | PASS; ProgressManager uses `learner-profile.schema.json` |

## 3. Defects found and corrected

### F-01 — Evidence metadata leakage

Before audit, Tutor Context reused the server-side Evidence definition. That would expose `related_faults`—including the actual fault family—and `information_value` to the Tutor and potentially the learner.

Correction:

- Added `evidence-public.schema.json` containing only `id`, `type`, `content`.
- Tutor Context and API Contract now use the released projection.
- Added negative leakage tests.

### F-02 — Arbitrary server initial state crossed the public boundary

Before audit, `CasePublicState` copied unrestricted `initial_state`, so a future Case could accidentally expose hidden fault fields.

Correction:

- Removed `initial_state` from the public projection.
- Retained `initial_observation` for Scenario Brief.
- Added safe `evidence_options` metadata containing only `id/type`.

### F-03 — Action had no reusable structure

Before audit, API action, Session actions and Tutor action history were unrelated free-form objects.

Correction:

- Added a platform-neutral `LearnerAction` envelope with `action_type` and `parameters`.
- Reused it in Session, Tutor Context and API Contract.
- Did not invent allowed action names or simulator parameters.

### F-04 — Training Report route had no response contract

The frozen API included `/sessions/{id}/report`, but no schema could guarantee the frozen Report Page fields.

Correction:

- Added `training-report.schema.json` with Ground Truth, learner path, recommended path, five scores, Tutor reflection and next Case.
- Report remains available only after `FINISH`.

### F-05 — Learning Page had no module content carrier

The Training Module schema identified modules and Case IDs but could not carry workstation introduction, SOP or basic knowledge.

Correction:

- Added minimal generic `content_sections` (`section_id`, `title`, `body`).
- Did not define RAG, rich media, knowledge retrieval or content authoring workflows.

## 4. Approved contract changes

### G-01 — Learner progress/profile and Dashboard retrieval

Frozen requirements demand Dashboard fields for current training progress, five-dimensional ability and recommended Case. Phase 2 also names `ProgressManager`. However:

- no Learner Progress/Profile Schema exists;
- the ten frozen routes contain no user/profile/progress endpoint;
- `GET /sessions/{id}/report` can describe only one known Session and cannot discover a learner's cross-session state.

CCP-001 Option A was approved on 2026-10-04. The contract now contains `LearnerProfile` and `GET /users/{user_id}/profile`. This is the sole approved extension to the original ten-route API.

### G-02 — `scoring_rules` representation

The Case Contract requires `scoring_rules`, and Phase 4 requires explainable rule scoring, but the field is currently an unconstrained object and ST-001 contains `{}`. A Skill Engine cannot reliably interpret it.

CCP-002 Option A was approved on 2026-10-04. `scoring_rules` now has a versioned declarative rule-list structure. Phase 2 preserves but does not evaluate the list; actual weights are authored in Phase 4.

## 5. Deferred items that do not block Phase 2 core

- Diagnostic transition table and illegal-transition behavior: Phase 3 Spec.
- Beginner/Intermediate/Advanced thresholds and hint escalation: Phase 5 Spec.
- Pose format, ROS/Isaac/Gazebo transport and Mock visual state: Phase 8/9 Specs.
- Fault parameters beyond the current Case payload: Phase 10 Spec.
- HTTP error envelope, authentication, pagination and idempotency: Backend API implementation Spec.
- Case/schema versioning and data migration: required before multi-version release, not required for the first in-memory Phase 2 core.

## 6. Repository status

The supplied remote `https://github.com/ICEXUAN-2707/SimTrouble-Tutor.git` is reachable, but `git ls-remote` returned no refs. The local workspace is not a Git repository. No remote write was attempted.

Before product code starts, the team should initialize the repository, install the v0.2 governance files, create `develop`, configure protection/review rules, and commit the Contract Freeze as the first auditable baseline.

## 7. Gate conclusion

- Phase 2 tasks `TrainingModuleLoader`, `CaseLoader`, `CaseSession`, `EvidenceManager` and `ProgressManager` can be implemented against the current contracts.
- Phase 4 may use the approved embedded-rule representation, but must define and review concrete scoring content in its own Spec.
- Phase 2 must not modify schemas opportunistically; any new gap returns to a Contract Change Proposal.
