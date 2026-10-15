# Demo Experience D0 — Interface Map

> Status: observed implementation, not a new Contract

## 1. End-to-end ST-001 path

    data/cases/ST-001.json
        ↓ CaseLoader.load
    TrainingCase (server-side, hidden fields included)
        ↓ CaseSession
    public_case_state + defensive Session snapshots
        ↓ DemoRuntime
    EvidenceManager / submit_hypothesis / record_action
        ↓ Demo public projection
    DemoRequestHandler JSON routes
        ↓ fetch
    apps/demo/static/index.html

The browser never reads ST-001.json. The DemoRuntime loads it server-side and projects explicit learner-facing fields.

## 2. Source and authority map

| Step | Source | Function/class | Input | Output | Authority |
|---|---|---|---|---|---|
| load Case | core/case_engine/case_loader.py | CaseLoader.load | Case path | validated TrainingCase | server only |
| create Session | core/case_engine/case_session.py | CaseSession.__init__ | user_id, TrainingCase | START Session + SessionStarted | Core |
| public Case | core/case_engine/case_session.py | public_case_state | authoritative Case | CasePublicState | Core projection |
| release Evidence | core/evidence_engine/evidence_manager.py | EvidenceManager.request | CaseSession, evidence ID | ReleasedEvidence | Core existence check and metadata stripping |
| hypothesis | core/case_engine/case_session.py | submit_hypothesis | text | updated Session snapshot/Trace | Core |
| generic action | core/case_engine/case_session.py | record_action | LearnerAction | ActionPerformed Trace | Core |
| trace append | core/session_trace/trace_recorder.py | record_* | candidate Session | seven-field TraceEvent | Core |
| runtime session | apps/demo/runtime.py | DemoRuntime | cookie token | process-local DemoSession | Demo adapter |
| HTTP | apps/demo/server.py | DemoRequestHandler | local HTTP | JSON/public HTML | Demo transport |
| Tutor | apps/demo/rule_tutor.py | reply_to | learner text, released IDs, hypothesis | string | Demo-only rule |
| diagnosis | apps/demo/st001_judge.py | judge_diagnosis | text, released IDs | Demo-only result | not formal Core diagnosis |
| page | apps/demo/static/index.html | render/run | public JSON | DOM | presentation only |

## 3. HTTP surface actually implemented

| Method | Route | Request | Success response | Notes |
|---|---|---|---|---|
| GET | / | none | static index.html | currently contains the E02 70 mm leak |
| GET | /healthz | none | status, case, mode | no Session required |
| GET | /api/state | cookie optional | full Demo public projection | creates server cookie if absent |
| POST | /api/reset | object | fresh public projection | creates a new cookie/session |
| POST | /api/evidence | id | updated public projection | any existing ST-001 Evidence is currently accepted |
| POST | /api/hypothesis | text | updated public projection | add/update decided by CaseSession |
| POST | /api/chat | text | updated public projection | deterministic rule response |
| POST | /api/diagnose | text | updated public projection | locks Demo wrapper; Core stage remains START |

This surface is the private Demo adapter defined in specs/demo-v0.1/contract.md. It is not the frozen future FastAPI surface in contracts/api-contract.md.

## 4. Public projection

DemoRuntime._public_state currently emits:

| Top-level field | Contents | Source |
|---|---|---|
| mode | Demo/Rule/ST-001 label | Demo adapter |
| case | case_id, device_type, scenario, difficulty, task, initial_observation, evidence_options, safety_rules | CaseSession.public_case_state |
| released | only ReleasedEvidence already requested | EvidenceManager |
| session | case_id, current_stage, evidence_seen, current_hypothesis, hypothesis_history | defensive Core snapshot |
| messages | learner/Tutor text | Demo wrapper |
| trace | authoritative Core Trace events | defensive Core snapshot |
| diagnosis | null or Demo-only judge result | Demo wrapper |

Fields not present:

- task_status;
- gripper_state as a public dynamic state;
- allowed_actions;
- simulation time/pose stream;
- formal report;
- Tutor intent or suggested_next_step;
- Skill output.

## 5. Evidence map

### E01

Authoritative Case content after legal ID request:

- type: gripper_state;
- command: close;
- state: closed;
- holding_object: false.

Internal information_value and related_faults are stripped. Before E01 release, only id/type appear as an Evidence option.

### E02

Authoritative released content:

- type: object_pose;
- axis: x;
- expected_mm: 0;
- actual_mm: 70;
- offset_mm: 70.

The fresh /api/state response does not contain these values. POST /api/evidence with E02 returns them. The current initial HTML nevertheless leaks the same 70 mm value through a quick-prompt string and must be fixed before release.

### E03

Authoritative released content:

- type: target_pose;
- target_available: true;
- target_conflict: false.

The UI must render these exact returned fields and must not invent additional target checks.

## 6. Trace and Journey mapping

Current Core events available to the Demo:

- SessionStarted;
- StateTransitioned / StateTransitionRejected;
- ActionPerformed;
- EvidenceRequested / EvidenceReleased / EvidenceDenied;
- HypothesisAdded / HypothesisUpdated / HypothesisRejected;
- SessionFinished.

The Demo currently generates SessionStarted, Evidence events, Hypothesis events and generic ActionPerformed events. It does not call transition_to, so all normal Demo events remain at START. Tutor and diagnosis are represented only as generic ActionPerformed; there is no TutorResponded or DiagnosisSubmitted event in the frozen Phase 3 implementation.

The frontend may present this as the current-session Core Trace. It must not label the UI animation states as Core stages or manufacture missing event types.

## 7. Tutor boundary

Current rule Tutor receives:

- learner message;
- released Evidence IDs;
- current hypothesis.

It does not receive the raw Case, ground_truth, optimal_path, fault, scoring rules or unreleased Evidence content. Server-side rules mention the E02 result only after E02 is in the released-ID set.

The current return value is a plain string, not tutor-response.schema.json. Formal Tutor Contract integration must wait for its implementation phase.

## 8. Diagnosis and Reflection boundary

The Demo judge:

- uses deterministic keyword matching;
- is explicitly labeled ST-001 Demo-only;
- records a generic diagnose LearnerAction;
- does not transition the state machine;
- can be invoked with no Evidence;
- reveals the reference explanation after submission;
- prevents further Demo commands until reset.

It is not the frozen POST /sessions/{id}/diagnosis application service and does not produce a FINISH-only TrainingReport.

## 9. Error and reset behavior

- invalid/missing text → HTTP 400;
- body over 8192 bytes → HTTP 413;
- unknown route → HTTP 404;
- unknown Evidence ID → HTTP 400 plus EvidenceRequested/EvidenceDenied in Core Trace;
- command after diagnosis → HTTP 400;
- frontend currently catches JSON errors and shows a temporary toast;
- reset creates a new backend token and resets released Evidence, messages, hypothesis, trace and diagnosis;
- future visual animation state must also reset locally.

## 10. Security boundary summary

| Surface before E02 request | Result |
|---|---|
| /api/state | safe: no E02 content/private Case fields |
| E01 response | safe: no E02 content |
| E03 response | safe with respect to E02 |
| initial HTML/client resource | unsafe: contains 70 mm prompt |
| raw ST-001.json | server-side only; must remain unreachable |

No frontend-only change may start loading ST-001.json or embedding server-side rule text.
