# Phase 1 Contract Change Proposals — Decision Required

> Status: APPROVED — 2026-10-04  
> Authority required: Tech Lead / Contract Owner  
> No option below is accepted merely by appearing in this document.

## CCP-001 — Learner Progress/Profile and Dashboard API

### Requirement conflict

- Dashboard must show current training progress, five-dimensional ability and recommended Case.
- Phase 2 includes `ProgressManager`.
- Frozen API has no route that can retrieve a learner's cross-session state.

### Option A — Add a learner profile resource

- Add `LearnerProgress/Profile Schema`.
- Add a read route such as `GET /users/{user_id}/profile`.
- Keep Session and Report focused on a single training run.

Impact: changes the frozen ten-route API and therefore requires explicit approval.

### Option B — Define Dashboard as single-session only

- Read the latest known Session/Report ID from client state.
- Do not add an API route.

Impact: does not truly satisfy persistent “current training progress” across devices/sessions and changes the apparent product meaning.

### Decision

**Option A approved.** Added `learner-profile.schema.json` and `GET /users/{user_id}/profile`. This is the only approved extension to the original ten-route API.

## CCP-002 — Explainable Scoring Rule Representation

### Requirement conflict

- Case requires `scoring_rules`.
- Phase 4 requires deterministic, explainable five-dimensional scoring.
- Current `{}` cannot be interpreted or validated.

### Option A — Case-embedded declarative rules

Each Case stores versioned rules containing a rule identifier, target dimension, observable event/condition, score delta and explanation.

Impact: Case files are self-contained but require a deliberately limited condition vocabulary.

### Option B — Versioned scoring policy reference

Case stores a `scoring_policy_id`; the Skill Engine owns the versioned rule set.

Impact: simpler Case authoring, but changes the already frozen `scoring_rules` field and moves part of Case behavior outside the Case.

### Decision

**Option A approved.** `Case.scoring_rules` is now a versioned list of declarative rules containing `rule_id`, `dimension`, `event_type`, observable `condition`, `score_delta` and `explanation`. Phase 2 loads and preserves these rules but does not interpret them; concrete ST-001 scoring weights remain Phase 4 content work.
