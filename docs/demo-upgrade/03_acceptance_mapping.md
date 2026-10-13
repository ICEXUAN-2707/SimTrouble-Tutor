# Demo Experience D0 — Acceptance Mapping

> Current result reflects code and live HTTP behavior observed on 2026-10-09.
>
> D0 does not mark future D1–D3 work as complete.

## 1. Product acceptance mapping

| Requirement | Current result | Evidence/gap | Earliest task |
|---|---|---|---|
| Ready-to-failed scene | FAIL | static SVG, no visual sequence | D1 |
| pause/replay/skip | FAIL | controls absent | D1 |
| reduced motion | FAIL | no prefers-reduced-motion handling | D1 |
| clear case/mode/task/reset | PARTIAL | case, rule mode and reset exist; visual task state absent | D1 |
| wide Scene + Tutor layout | PARTIAL | current three-column cards | D1 |
| Evidence Lab + Journey | PASS/PARTIAL | both exist; hierarchy/readability need redesign | D1/D2 |
| no root cause before investigation | FAIL | initial HTML prompt contains E02 70 mm value | D1 blocker |
| E01 gripper focus after release | FAIL | only textual Evidence output | D2 |
| E02 annotation from released content | PARTIAL | release is correct; spatial annotation absent | D2 |
| truthful E03 | PASS | released Case fields are used | retain/D2 presentation |
| arbitrary legal Evidence order | PASS | UI/Core do not enforce E01→E02 | retain |
| honest rule Tutor mode | PASS | visible deterministic rule label | retain |
| Hypothesis add/update | PASS | CaseSession-backed | retain |
| diagnosis submission | PARTIAL | real Demo route, but Demo-only judge and no Core transition | retain label; backend future |
| truthful Journey | PASS/PARTIAL | authoritative Trace, but events remain START and names are raw | D2 presentation |
| reset clears state | PASS | new cookie/session; future visual state still needs reset | D1/D2 |
| no fictional Skill score | PASS | none shown | retain |
| three viewports | UNVERIFIED | responsive rules exist, screenshots absent | D1 |

## 2. Security QA mapping

| QA | Behavior | Current result | Evidence |
|---|---|---|---|
| QA-01 | initial load has no hidden cause/E02 | FAIL | /api/state safe; index.html contains E02 70 mm prompt |
| QA-02 | animation shows failed grasp | FAIL | static scene only |
| QA-03 | E01 only after release and gripper focus | PARTIAL | release safe; focus absent |
| QA-04 | pre-E02 Network/source has no E02 value | FAIL | Network JSON safe; page source unsafe |
| QA-05 | E02 annotation driven by authorized response | PARTIAL | response correct; visual annotation absent |
| QA-06 | any legal Evidence order | PASS | E02-first E2E passes |
| QA-07 | diagnosis through existing entry | PASS/PARTIAL | /api/diagnose works; explicitly Demo-only, not formal Core |
| QA-08 | reset clears session/visual/journey | PARTIAL | backend/session clears; future visual controller not present |
| QA-09 | service error is honest | PARTIAL | HTTP errors + toast; no durable error/retry view |
| QA-10 | regression and three viewports | PARTIAL | 60 tests pass; screenshots absent |

## 3. Contract and architecture mapping

| Constraint | Result | Notes |
|---|---|---|
| no Core/Contract/Case change in experience work | PASS in D0 | documentation only |
| one public data source | PASS | DemoRuntime projection |
| no second Session/Case logic | PASS | official CaseSession/EvidenceManager |
| raw Case absent from browser | PASS | server-only load |
| unreleased Evidence absent from /api/state | PASS | only option id/type exposed |
| unreleased E02 absent from all client resources | FAIL | static prompt leak |
| animation separate from Diagnostic State Machine | NOT IMPLEMENTED | D1 must enforce |
| no invented Simulation | PASS | static page says non-physical |
| no invented scores | PASS | no score UI |
| rule Tutor fallback available | PASS | deterministic local rule |

## 4. Milestone exit gates

### D0 exit

- [x] actual repository, branch and Demo location identified;
- [x] Freeze Pack, current Demo Spec, Contracts, ADR and branch policy reviewed;
- [x] ST-001 path traced end to end;
- [x] E01/E02/E03 actual behavior checked;
- [x] frontend-only and backend-blocked work separated;
- [x] D1/D2/D3 files, branches, risks and tests proposed;
- [x] no product code or Contract changed.

### D1 proposed gate

- [ ] E02 answer removed from all initial client resources;
- [ ] visual states are explicitly presentation-only;
- [ ] start/pause/replay/skip/reset work;
- [ ] existing API behavior remains unchanged;
- [ ] reduced motion and keyboard focus work;
- [ ] 1280/768/390 screenshots approved;
- [ ] all tests pass.

### D2 proposed gate

- [ ] E01/E02/E03 visuals use only released content;
- [ ] E02 values appear only after E02 release;
- [ ] no forced Evidence order;
- [ ] Journey matches Core Trace order;
- [ ] reset has no backend or visual residue;
- [ ] errors do not fake success/data;
- [ ] all tests pass.

### D3 proposed gate

- [ ] stable 90–120 second path;
- [ ] clean-checkout startup and complete regression;
- [ ] Network/source leak inspection;
- [ ] invalid request, reset and small-screen checks;
- [ ] final script/screenshots/recording approved;
- [ ] rollback commit recorded;
- [ ] phase integration approval obtained.

## 5. Current regression evidence

Executed:

    .\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'

Observed:

- 60 tests;
- all passed;
- no internet dependency;
- CI discovers the same tests on every PR.

The passing suite does not negate QA-01/QA-04 because the current hidden-field test inspects JSON object keys, not the initial HTML/client resource text.

## Decisions requiring human approval

1. Accept D0 with QA-01 and QA-04 explicitly blocked until D1.
2. Approve D1 as frontend-only visual work over existing public observations.
3. Approve deferring formal Evidence authorization, state transitions and report/Reflection to backend phases.
4. Approve viewport screenshot storage and the Product/QA reviewer.

## Facts that cannot be determined

- Exact approved animation timing and final visual composition.
- Formal rules for when each Evidence ID is allowed by diagnostic stage.
- Formal diagnosis correctness and Reflection response contract.
- Release date and target branch after D3.
