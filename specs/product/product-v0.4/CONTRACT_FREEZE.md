# Product v0.4 Learning Contract Freeze

> Status: approved implementation baseline  
> Version: 0.4.0  
> Scope: T2 Tutor and T3 diagnosis/evaluation/report boundaries

## 1. Compatibility decision

The Phase 1 schemas under `contracts/schemas/` remain frozen for existing Core
and legacy Demo regression. Product v0.4 uses the versioned schemas under
`contracts/v0.4/`. A later migration may replace the legacy shapes only through
an explicit compatibility task.

## 2. Tutor boundary

Tutor input is limited to:

- public Case projection;
- Evidence already released to this Session;
- learner and Tutor messages from this Session;
- learner hypotheses;
- actions currently permitted by program code.

Tutor input must not contain `fault`, `ground_truth`, `optimal_path`, scoring
rules, Evidence information value, related faults, or unreleased Evidence
content.

Tutor output uses `TutorResponseV04`:

- `intent`: question, hint, explain, or reflect;
- `message`: learner-facing expression;
- `hint_level`: integer 0–3;
- `suggested_action`: one advisory action or null.

`suggested_action` is never executed directly. The application checks it
against the request's `allowed_actions`, and Core remains the state authority.
Provider timeout, invalid JSON, schema failure, or leakage detection must fall
back to the deterministic rule Tutor.

## 3. Diagnosis and Evaluator boundary

Diagnosis submission is accepted once per Session after the application enters
the submitted stage. It contains a structured diagnosis type, written
reasoning, and one or more cited released Evidence IDs.

Evaluator mode runs only after submission. It may receive private Ground Truth,
the versioned rubric, submitted diagnosis, cited Evidence, and the public-safe
Session Trace. Its response contains qualitative findings and trace references.
It contains no numeric score or weight.

Program code must validate references and structured output, apply versioned
rules and weights, constrain every score to 0–100, preserve rule/Trace rationale,
and generate the final report deterministically.

## 4. Skill and report decision

Every report contains all five dimensions. Each dimension is either:

- `scored`: numeric score, effective weight, rationale, rules, and Trace refs;
- `not_assessed`: null score, zero weight, and an explanation.

The overall score is normalized over scored dimensions only. `coverage` reports
the proportion of configured dimensions actually assessed. ST-001 Safety
remains `not_assessed` until the Case supplies an observable safety action and
matching rule.

## 5. API route freeze

| Method | Route | Contract/result |
|---|---|---|
| POST | `/api/v0.4/sessions` | create an in-memory learner Session |
| GET | `/api/v0.4/sessions/{session_id}` | learner-safe Session view |
| POST | `/api/v0.4/sessions/{session_id}/evidence` | released Evidence + Session view |
| POST | `/api/v0.4/sessions/{session_id}/hypotheses` | updated Session view |
| POST | `/api/v0.4/sessions/{session_id}/tutor` | `TutorResponseV04` + Session view |
| POST | `/api/v0.4/sessions/{session_id}/diagnosis` | accepted submission; starts evaluation |
| GET | `/api/v0.4/sessions/{session_id}/report` | `TrainingReportV04` after review |

Sessions remain process-local for v0.4. Authentication, persistence, streaming,
multi-tenant administration, and provider-specific fields are outside this
contract.

## 6. Journey and Trace decision

The public journey remains:

`READY -> PLAYING -> INVESTIGATING -> SUBMITTED -> REVIEWED`

The nine-stage Core model remains internal. Animation playback does not mutate
Core state or create scoring events. Only explicit learner/application commands
may append learning Trace events.

The existing seven-field Trace shape remains unchanged. T2/T3 may extend the
approved `action_type` vocabulary for Tutor request/delivery/fallback,
diagnosis submission/evaluation, report generation, and reflection, but may not
store private Ground Truth or an unredacted model prompt in Trace.

## 7. Implementation order

1. Session repository and learner-safe Session view.
2. Evidence/action guards and approved Trace vocabulary.
3. Tutor context projector, provider port, validation, and rule fallback.
4. Diagnosis evaluator and versioned program scoring.
5. Report builder and web integration.
