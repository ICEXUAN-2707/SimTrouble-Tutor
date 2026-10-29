# Product v0.4 Task Plan

> Status: integration candidate; implementation complete through T4B, release gate open
> Contract authority: CONTRACT_FREEZE.md and contracts/v0.4/

## Delivery status

- T0 product and contract baseline: complete.
- T1 CAD scene and Session API: complete.
- T2A bounded Tutor backend foundation: complete on the integration candidate.
- T2B Tutor frontend, Trace and runtime hardening: implementation complete;
  credential-gated live-provider smoke remains an explicit release check.
- T2C provider registry, configuration resilience and Case-aware output guard: complete on the integration candidate.
- T3 Diagnosis, Evaluator, deterministic scoring and Report: implementation complete on the integration candidate.
- T4A/T4B integrated learner workflow and localized product UI: implementation complete on the integration candidate.
- M1 Step-4 diagnosis unlock: regression fix merged into the Phase;
  Evidence may be collected before the initial Hypothesis, while one revised
  Hypothesis remains mandatory before Diagnosis.
- T4 release gate: launcher, automated Phase checks, dependency audit and one explicit DeepSeek smoke pass on the M3 task branch; task/Phase review, product-owner RC browser acceptance and Phase-to-develop integration remain.

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

## T2C — Provider and output-safety hardening

- Select DeepSeek Responses or an approved OpenAI-compatible provider through one registry.
- Support Qwen, Kimi and SiliconFlow presets without changing the public Tutor contract.
- Treat invalid configuration and missing credentials as safe rule-fallback conditions.
- Validate model output with a Case-aware guard for hidden answers, private paths and unreleased Evidence.
- Keep API keys, full prompts, private Case values and provider error bodies out of API responses, Trace and metrics.

Implementation status: complete. Unit tests cover registry selection, endpoint
validation, configuration failure, bounded retry, structured output and Guard
allow/deny paths without making real provider calls.

## T3 — Diagnosis and learning evaluation

- Accept one structured diagnosis with reasoning and released Evidence IDs.
- Reject unreleased or unknown Evidence references.
- Run Evaluator mode only after submission.
- Keep qualitative LLM findings separate from numeric program scoring.
- Apply versioned rules and effective weights.
- Produce all five dimensions with scored or not_assessed status.
- Build a deterministic TrainingReportV04 and expose the Report route.

Implementation status: complete. Diagnosis is create-once and accepted only in
UPDATE. Evaluation/report generation is atomic with Session completion; invalid
stages and unreleased Evidence leave the authoritative Trace unchanged. The
Evaluator emits qualitative findings only, while the versioned program engine
owns numeric scoring. ST-001 Safety is `not_assessed` with zero effective
weight.

## T4 — Integrated MVP

- Bind animation, Evidence, Hypothesis, Tutor, Diagnosis and Report into one page.
- Add a one-click local launcher with backend-only secret preflight: read the
  DeepSeek key from an environment variable or ignored local secret store,
  start API and web, and keep credentials out of frontend assets and Git.
- Complete one real-DeepSeek smoke test before the release gate; rule fallback
  remains available when the provider is unavailable.
- Verify correct, incorrect, insufficient and repeated submissions.
- Verify Safety=not_assessed for ST-001.
- Verify animation replay never changes learning Trace or scores.
- Validate desktop, tablet and phone layouts.
- Freeze the 90–120 second demonstration path.

Implementation status: T4A/T4B are complete. The localized responsive web
workspace binds CAD playback, Evidence, initial and revised Hypotheses, Tutor,
create-once Diagnosis and the authoritative Report to one page-lifetime
Session. Browser fixtures cover the learner workflow, API recovery, Tutor
delivery modes and desktop/tablet/mobile layouts. The Step-4 regression suite
also covers collecting every available Evidence item before the initial
Hypothesis; the first Hypothesis now enters TEST immediately, and the revised
Hypothesis unlocks Diagnosis without requiring another Evidence request. The
overall T4 gate remains
open until the launcher, credential-gated provider smoke, dependency audit and
Phase integration are complete.

## Phase gate

The phase branch may enter develop only when:

1. every frozen Product v0.4 API route is implemented;
2. JSON Schema and Pydantic parity tests pass;
3. provider success and fallback browser paths pass;
4. report generation is deterministic from the same Trace;
5. README and architecture documentation match the implementation;
6. Python, TypeScript, production build, browser E2E and dependency audit pass.
