# Demo Experience D0 — Current State Audit

> Status: D0 COMPLETE — documentation only
>
> Audit date: 2026-10-09
>
> Product baseline: SimTrouble_Demo_Experience_Spec_v1
>
> Code baseline: 75d6b68 on phase/demo-v0.1-integration

## 1. Executive conclusion

The active Demo is part of the current repository. It is not the ignored legacy delivery package:

- repository root: D:/高ice（大学版）/2026-2027 大二/9月人工智能应用创新校赛;
- authoritative Demo: apps/demo/;
- process entry: python -m apps.demo;
- presentation: apps/demo/static/index.html;
- private local runtime: Python standard-library HTTP server on 127.0.0.1;
- authoritative Case/Core: data/cases/ST-001.json and core/;
- current tests: tests/demo/ plus Phase 1–3 tests.

There is no tracked Next.js/React application, no FastAPI application and no tracked demo_app directory. The ignored zjh/ directory is migration input only.

The existing Demo already uses the official CaseSession, EvidenceManager and Core Trace. The minimum experience upgrade should therefore reuse apps/demo/ rather than create another frontend or another Session/Case implementation.

## 2. Git baseline

Initial D0 observations before creating the audit branch:

| Item | Observed value |
|---|---|
| branch | phase/demo-v0.1-integration |
| HEAD | 75d6b68 — Merge PR #10: add ST-001 Demo E2E and startup smoke |
| upstream | origin/phase/demo-v0.1-integration |
| develop | 9df07f3 — Phase 3 integrated |
| remotes | origin fetch/push → https://github.com/ICEXUAN-2707/SimTrouble-Tutor.git |
| uncommitted tracked changes | none |
| untracked input | SimTrouble_Demo_Experience_Spec_v1/ |

D0 documentation is isolated on task/demo-v0.1-experience-d0, created from the latest Demo phase branch. The supplied experience-spec directory remains unmodified and untracked because the D0 instruction authorizes only the four audit documents.

## 3. Actual workspace structure

| Concern | Actual location | State |
|---|---|---|
| static Demo | apps/demo/static/index.html | implemented |
| HTTP transport | apps/demo/server.py | implemented, private Demo routes |
| runtime/read model | apps/demo/runtime.py | implemented, process-local |
| rule Tutor | apps/demo/rule_tutor.py | implemented, deterministic |
| diagnosis judge | apps/demo/st001_judge.py | implemented, explicitly Demo-only |
| Case | data/cases/ST-001.json | authoritative server-side Case |
| Session aggregate | core/case_engine/case_session.py | implemented |
| Evidence release | core/evidence_engine/evidence_manager.py | implemented |
| state machine | core/state_machine/diagnostic_state_machine.py | implemented but not invoked by Demo commands |
| Trace | core/session_trace/trace_recorder.py | implemented and projected by Demo |
| formal frontend/backend | none | not implemented |
| Skill engine | none | not implemented |
| Simulation adapter | contract only | not implemented |
| LangGraph/LLM | none | not implemented |
| legacy delivery | zjh/ | ignored; not source of truth |

The Freeze Pack roadmap still says Phase 3 is waiting to enter develop. Git history and the current README prove this sentence is stale: Phase 3 is already in develop. Current Git evidence takes precedence for this audit.

## 4. Running Demo

The existing acceptance instance was healthy during D0:

- URL: http://127.0.0.1:65268/;
- health: status=ok, case=ST-001, mode=demo-v0.1;
- branch contents: phase/demo-v0.1-integration and the identical D0 branch base;
- startup contract: HOST defaults to 127.0.0.1, PORT defaults to 8000 and is overridable.

The process is a local acceptance aid, not a deployed service. Sessions live only in the process and are lost on restart.

## 5. Implemented product behavior

Implemented now:

- server-created anonymous cookie sessions;
- learner-safe Case public projection;
- E01/E02/E03 release through EvidenceManager;
- Hypothesis add and update through CaseSession;
- deterministic rule Tutor;
- Demo-only ST-001 keyword diagnosis;
- authoritative Core Trace projection;
- reset to a new backend session;
- static responsive browser page;
- request size and text length limits;
- 404/400/413 JSON errors;
- 60 passing tests, including HTTP E2E and subprocess startup smoke.

Not implemented:

- dynamic task_status, gripper_state or allowed_actions;
- Simulation/Mock state;
- Evidence authorization by diagnostic stage or an evidence-release rule;
- automatic or application-driven Diagnostic State Machine transitions;
- formal diagnosis submission in Core;
- FINISH-only TrainingReport/Reflection;
- Tutor Contract DTO and TutorPolicy events;
- Skill Engine or five-dimensional scores;
- persistence, accounts, remote hosting or multiple Cases.

## 6. Security audit

### Safe boundaries already present

- CaseSession.public_case_state excludes fault, initial_state, evidence content, ground_truth, optimal_path and scoring_rules.
- EvidenceManager returns ReleasedEvidence with only id, type and content.
- A fresh /api/state response contains only mode, case, released, session, messages, trace and diagnosis.
- Fresh state contained no offset_mm, actual_mm, expected_mm, object_pose_offset or object_pose_mismatch.
- After E01 only, the response did not contain E02 values.
- E02 returned axis=x, expected_mm=0, actual_mm=70 and offset_mm=70 only after POST /api/evidence with id=E02.
- E03 returned target_available=true and target_conflict=false from the authoritative Case.

### Release blocker

apps/demo/static/index.html currently contains a quick-prompt string that says E02 shows a 70 millimetre X offset. GET / therefore discloses the hidden E02 value before E02 is requested.

This violates the new experience Spec even though /api/state is safe. Existing tests check hidden JSON keys but do not scan the initial HTML/client resource for hidden E02 content.

### Authorization limitation

EvidenceManager validates that an Evidence ID exists and strips internal metadata. It does not authorize by current diagnostic stage. The Demo therefore releases E01/E02/E03 while the Core stage remains START.

POST /api/diagnose can also run without Evidence and returns the Demo-only reference explanation while the Core stage remains START. This is allowed by the existing Demo v0.1 adapter contract but is not a formal state-machine diagnosis or FINISH report.

## 7. What can change directly in the frontend

The following work can be done in apps/demo/static/index.html without new backend fields:

- Graphite/Deep Teal layout and the 60–65% Scene / 35–40% Tutor composition;
- responsive stacking for 1280×720, 768×1024 and 390×844;
- presentation-only READY, EXECUTING, GRASP_ATTEMPT and FAILURE_OBSERVED animation;
- pause, replay, skip and reset of visual animation;
- prefers-reduced-motion behavior;
- visible Mock/Rule Tutor/Demo-only labels;
- keyboard focus, button sizing, non-color-only status and overflow fixes;
- scene highlights driven only by IDs/content already present in state.released;
- E01 gripper focus after E01 is released;
- E02 offset annotation generated only from the released E02 content;
- E03 rendering from its released content;
- readable formatting of the existing authoritative trace;
- clear loading/error/empty states for current routes;
- removal of all preloaded E02 values from HTML, JavaScript, SVG and prompt text.

The animation may illustrate the already-public grasp-failed observation, but it must be labeled visual state and must not mutate or impersonate Session.current_stage.

## 8. What must wait for backend/Core capability

Frontend work must not invent:

- real task_status, gripper_state, object pose streams or simulation progress;
- allowed_actions or state-dependent Evidence authorization;
- Core stage advancement for Observe/Investigate/Diagnose/Reflect;
- a formal diagnosis command and authoritative correctness result;
- a FINISH-only report or ground-truth Reflection;
- Tutor intent/suggested_next_step contract output and TutorPolicy audit events;
- timeout/fallback semantics for a future online Tutor;
- Skill scores, radar charts, learner profiles or recommendations;
- persistent Trace, account identity or restart recovery.

Those items require a later backend/Application/Core Spec. Any change to frozen public Contracts requires a CCP.

## 9. Test baseline

Command:

    .\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'

Result:

- 60 tests run;
- 60 passed;
- existing E2E covers Evidence, Hypothesis, Tutor, Demo-only diagnosis, reset and cookie isolation;
- startup smoke launches a real subprocess and polls /healthz;
- missing gate: initial HTML/client-resource E02 value scan;
- missing gate: viewport screenshots and reduced-motion/keyboard manual verification.

## 10. D0 decision

Gate A is clear: the Demo is in the latest working repository and has a legal integration location. No migration is required.

Gate B is partially triggered: the current public projection is sufficient for D1 visual work but lacks task_status, gripper_state and allowed_actions. D1 must use a clearly labeled presentation-only animation. Formal workflow or authorization improvements must wait.

No product code, Contract, Core or Case file was changed in D0.

## Decisions requiring human approval

1. Approve D1 as a visual-only animation over the existing public grasp-failed observation, with no claim of Simulation or Core-stage progress.
2. Approve removing/rewording the E02 quick prompt so the initial client resource contains no 70 mm value.
3. Confirm that D1 retains the current Demo-only diagnosis and START-stage behavior unchanged; formal workflow work is deferred.
4. Decide whether the supplied SimTrouble_Demo_Experience_Spec_v1 directory should later be imported as governed project documentation; D0 leaves it untracked.
5. Confirm where D1 viewport screenshots should be stored.

## Facts that cannot be determined

- No approved backend Spec currently defines allowed_actions or stage-based Evidence release rules.
- No current implementation schedule exists for Simulation, formal diagnosis/report, Skill or online Tutor.
- Product/UX acceptance of the proposed visual treatment requires human review.
- The long-term storage policy for screenshots and final recordings is not frozen.
