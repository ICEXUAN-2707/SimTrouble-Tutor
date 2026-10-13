# Product v0.4 Task Plan

> Status: active integration plan
> Contract authority: CONTRACT_FREEZE.md and contracts/v0.4/

## Delivery status

- T0 product and contract baseline: complete.
- T1 CAD scene and Session API: complete.
- T2A bounded Tutor backend foundation: complete on the current task branch.
- T2B Tutor frontend, Trace and runtime hardening: implementation complete;
  credential-gated live-provider smoke remains an explicit release check.
- T3 Diagnosis, Evaluator, deterministic scoring and Report: not started.
- T4 integrated MVP and release gate: not started.

## T0 — Baseline

- Freeze the two-core product definition.
- Freeze the public five-step learner journey.
- Freeze Tutor, Diagnosis, Evaluator and Report contracts.

## T1 — CAD and Session foundation

- Vite, TypeScript and Three.js CAD workcell.
- FastAPI Scene endpoint.
- Process-local Session repository.
- Evidence release and Hypothesis commands.
- Learner-safe SessionView projection.
- Python, TypeScript and browser CI.

## T2A — Bounded Tutor backend

- Project SessionView into a learner-safe TutorRequest.
- Choose intent, hint level and suggested action with deterministic Policy.
- Call DeepSeek through a provider-neutral asynchronous port.
- Require structured JSON Schema output and validate it again with Pydantic.
- Reject policy changes, disallowed actions and private-field markers.
- Fall back to deterministic rules for disabled, failed or unsafe providers.
- Keep bounded conversation history isolated by session ID.

Streaming remains outside Product v0.4. A complete response must be validated
before any model text is returned to the learner.

## T2B — Tutor delivery closeout

- Bind the frontend Tutor panel to the formal Session route.
- Serialize concurrent Tutor calls within one Session.
- Record request, delivery and fallback Trace events without raw prompts,
  API keys, private Case fields or provider error bodies.
- Add latency, mode, retry and fallback-reason metrics.
- Add a server-side pre-diagnosis direct-answer leak policy.
- Run one explicit real-DeepSeek smoke test outside CI.
- Add browser tests for success, timeout, malformed output and leakage fallback.

Implementation status: complete. The repository includes a credential-gated
`tools/deepseek_tutor_smoke.py`; it must be run once with a real key before the
phase gate, because CI and the repository do not contain provider credentials.

## T3 — Diagnosis and learning evaluation

- Accept one structured diagnosis with reasoning and released Evidence IDs.
- Reject unreleased or unknown Evidence references.
- Run Evaluator mode only after submission.
- Keep qualitative LLM findings separate from numeric program scoring.
- Apply versioned rules and effective weights.
- Produce all five dimensions with scored or not_assessed status.
- Build a deterministic TrainingReportV04 and expose the Report route.

## T4 — Integrated MVP

- Bind animation, Evidence, Hypothesis, Tutor, Diagnosis and Report into one page.
- Verify correct, incorrect, insufficient and repeated submissions.
- Verify Safety=not_assessed for ST-001.
- Verify animation replay never changes learning Trace or scores.
- Validate desktop, tablet and phone layouts.
- Freeze the 90–120 second demonstration path.

## Phase gate

The phase branch may enter develop only when:

1. every frozen Product v0.4 API route is implemented;
2. JSON Schema and Pydantic parity tests pass;
3. provider success and fallback browser paths pass;
4. report generation is deterministic from the same Trace;
5. README and architecture documentation match the implementation;
6. Python, TypeScript, production build, browser E2E and dependency audit pass.
