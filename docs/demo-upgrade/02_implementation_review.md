# Demo Experience D0 — Implementation Review

> Scope: plan only. D1/D2/D3 are not implemented by this document.

## 1. Gap analysis

| Spec area | Current state | Gap | Disposition |
|---|---|---|---|
| wide Scene + Tutor layout | three-column cards | visual hierarchy differs | D1 frontend |
| Evidence Lab + Journey | present as cards/trace | placement/readability differ | D1/D2 |
| animation states | static SVG only | READY→FAILURE animation absent | D1 frontend, visual-only |
| pause/replay/skip | absent | required | D1 frontend |
| reduced motion | absent | required | D1 frontend |
| mode/task/reset labels | partial | Mock/visual-state wording needs precision | D1 frontend |
| initial E02 secrecy | JSON safe | HTML prompt leaks 70 mm | D1 release blocker |
| E01 scene highlight | Evidence text only | no gripper focus | D2 frontend using released ID |
| E02 spatial annotation | raw Evidence text | no controlled visual comparison | D2 frontend using released content |
| E03 truthful display | raw returned fields | needs readable mapping only | D2 frontend |
| Evidence order | unrestricted by UI | no forced order | keep |
| Journey truth | Core Trace | raw event names, all stage START | improve presentation; do not invent stages |
| service errors | temporary toast | weak persistent/retry state | D2 frontend |
| reset | backend state resets | future animation must also reset | D1/D2 frontend |
| Tutor | deterministic rule mode | not formal Tutor DTO | retain; backend future |
| diagnosis | Demo-only wrapper | not formal state/report | retain label; backend future |
| Reflection | Demo reference after submit | not FINISH TrainingReport | do not call formal Reflection |
| Skill | absent | no scores | keep absent |
| viewport QA | responsive CSS exists | no required screenshots | D1 manual QA |

## 2. Recommended minimum implementation

### D1 — visual scene only

Branch:

    task/demo-v0.1-experience-d1

Parent:

    latest phase/demo-v0.1-integration after D0 merge

Allowed product file:

- apps/demo/static/index.html

Allowed tests/evidence:

- tests/demo/test_demo_http_e2e.py;
- docs/demo-upgrade/screenshots/ only if the team approves this storage path.

Implementation:

1. Remove/reword the leaking E02 quick prompt before adding visual work.
2. Recompose the existing page into a wide Scene Canvas, Tutor panel and lower Evidence/Journey area.
3. Implement a namespaced presentation state controller for READY, EXECUTING, GRASP_ATTEMPT and FAILURE_OBSERVED.
4. Keep the controller entirely separate from session.current_stage.
5. Add start/pause/replay/skip and reset behavior.
6. Animate only the public grasp attempt/failure observation.
7. Add reduced-motion and keyboard/focus behavior.
8. Keep all current HTTP routes, Tutor, Evidence, Hypothesis and diagnosis calls unchanged.

Do not modify:

- core/;
- contracts/;
- data/cases/;
- apps/demo/runtime.py;
- apps/demo/server.py;
- rule_tutor.py;
- st001_judge.py;
- requirements.txt.

This is the preferred plan because it satisfies the D1 instruction in the existing framework and adds no second SPA, route or dependency.

### Alternative D1

If maintaining a single HTML file becomes unreviewable, split presentation CSS/JS into static assets only after approving matching static routes in server.py. That alternative touches the HTTP adapter and is not the minimum plan, so it is not approved by D0.

## 3. D2 plan — Evidence and Journey integration

Branch:

    task/demo-v0.1-experience-d2

Expected files:

- apps/demo/static/index.html;
- tests/demo/test_demo_http_e2e.py;
- possibly apps/demo/server.py or runtime.py only for a defect in the already-approved private Demo adapter, not for new Core semantics.

Work that can use existing responses:

- highlight the gripper after released contains E01;
- derive the E02 arrow and delta label from the returned E02 content;
- render E03 from returned target_available/target_conflict;
- improve the readable current-session Trace;
- reset visual state together with POST /api/reset;
- provide honest persistent error/retry messages;
- ensure no forced E01→E02 ordering.

Blocked backend work:

- stage-based Evidence authorization;
- allowed_actions;
- formal diagnosis transitions;
- FINISH-only reflection/report;
- formal Tutor DTO/events;
- Skill results.

D2 must stop rather than alter Core/Contracts if these are made acceptance requirements.

## 4. D3 plan — freeze and release evidence

Branch:

    task/demo-v0.1-experience-d3

Expected outputs:

- acceptance evidence under docs/demo-upgrade/;
- final 90–120 second script aligned with real capability;
- screenshots for 1280×720, 768×1024 and 390×844;
- clean-checkout 60+ test report;
- source/payload hidden-value scan;
- reset, invalid request and rule-mode fallback checks;
- rollback reference to the last accepted phase commit.

D3 is verification/freeze work, not a feature phase.

## 5. Test additions

### D1 automated

- GET / initial HTML must not contain 70 mm, 70毫米, offset_mm, actual_mm, expected_mm or the E02 answer sentence.
- Fresh /api/state must remain free of hidden keys and E02 sensitive values.
- Existing 60 tests must pass.

### D1 manual/browser

- 1280×720, 768×1024 and 390×844 screenshots;
- keyboard-only navigation and visible focus;
- reduced-motion mode;
- pause/replay/skip/reset;
- no horizontal clipping of critical controls.

### D2 automated

- E01 response contains no E02 values;
- E02 values appear only after E02 request;
- E03 matches the authoritative released content;
- arbitrary Evidence order remains supported;
- invalid E99 produces an error and EvidenceDenied trace;
- reset clears released Evidence, messages, hypothesis, diagnosis and old Trace;
- UI resources never embed raw Case/private fields.

### D3

- clean checkout/startup test;
- complete unittest discovery;
- dependency/forbidden-import scan;
- browser Network/source inspection before E02;
- manual 90–120 second script run.

No browser automation dependency is approved in D0. Screenshots may be captured manually or with existing browser tooling.

## 6. Risk review

| Risk | Severity | Control |
|---|---|---|
| initial HTML leaks E02 answer | blocker | remove text and add source scan first |
| UI animation mistaken for Core stage | high | separate names and visible visual-only label |
| frontend invents task/simulation fields | high | map only current public projection |
| D2 silently adds state authorization | high | stop and request backend Spec/CCP |
| Demo-only diagnosis presented as formal | high | retain explicit Demo-only label |
| responsive redesign hides Evidence controls | medium | three required viewport checks |
| animation harms accessibility | medium | controls plus reduced-motion |
| single HTML grows difficult to maintain | medium | keep D1 bounded; reconsider asset split only through review |

## 7. Dependencies

D1 requires no new package, framework, schema, route or network service. It depends only on:

- the current private Demo HTTP surface;
- existing public Case projection;
- existing static SVG/CSS/JavaScript;
- current rule Tutor fallback.

D2 formal-workflow enhancements cannot proceed until an approved backend/Application Spec defines the missing behavior.

## 8. Contract impact

Recommended D1 has no Contract impact. Recommended D2 presentation integration has no Contract impact as long as it consumes only existing fields.

Adding task_status, gripper_state, allowed_actions, evidence-stage rules, formal diagnosis or report semantics is not authorized by this experience Spec alone.

## Decisions requiring human approval

1. Approve the recommended D1 file boundary: index.html plus focused tests only.
2. Approve the visual-only state controller and the wording that distinguishes it from the Core state machine.
3. Approve immediate removal of the E02 70 mm quick prompt as a release-blocking security fix in D1.
4. Confirm that formal state progression/diagnosis/report are deferred instead of being simulated in the frontend.
5. Approve the D1/D2/D3 branch names listed above.
6. Approve a repository path for viewport screenshots, or require them to remain external QA artifacts.

## Facts that cannot be determined

- The design does not specify exact animation timing within the 90–120 second overall script.
- No authoritative allowed_actions or Evidence-stage policy exists.
- No formal backend diagnosis implementation is present.
- The future Next.js/FastAPI migration timing is unknown.
- Visual sign-off and final recording ownership require Product/QA confirmation.
