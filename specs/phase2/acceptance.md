# Phase 2 Acceptance

> Status: DRAFT FOR NEXT ROUND

## Loader tests

- [x] Valid module fixtures load successfully.
- [x] `ST-001.json` loads successfully.
- [x] Malformed objects and unexpected fields fail validation.
- [x] Duplicate module/Case IDs fail catalog construction.

## Session tests

- [x] New Session matches `learner-session.schema.json` defaults.
- [x] Authoritative Case stays isolated and private through defensive deep copies.
- [x] Public Case projection matches `case-public.schema.json`.
- [x] Recording a valid `LearnerAction` changes only Session data.
- [x] No stage-transition rules are implemented.

## Evidence tests

- [x] Valid explicit request returns `ReleasedEvidence` only.
- [x] Unknown Evidence ID returns an error without Session mutation.
- [x] Repeated request does not duplicate `evidence_seen`.
- [x] Ground Truth, fault, optimal path, related faults, information value and scoring rules never cross the public boundary.

## Regression and boundary tests

- [x] All Phase 1 contract tests remain green.
- [x] Core source contains no imports from LLM, LangGraph, Isaac, ROS or Gazebo packages.
- [x] No frontend/backend API/persistence implementation is added.

## Progress tests

- [x] Empty history produces zero progress, zero skill scores and no recommendation.
- [x] Completed Sessions are grouped by Module without duplicate Case IDs.
- [x] Output matches `learner-profile.schema.json`.
- [x] ProgressManager does not calculate Skill scores or choose a Case autonomously.
