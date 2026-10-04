# Phase 2 Contract

> Status: IMPLEMENTED — contract retained as the Phase 2 implementation boundary.

## Intended modules

```text
core/
├── models/
├── training_engine/
│   └── module_loader.py
├── case_engine/
│   ├── case_loader.py
│   └── case_session.py
└── evidence_engine/
    └── evidence_manager.py

tests/training_core/
```

`progress_manager.py` produces the approved `LearnerProfile` read model without implementing automatic recommendation logic.

## TrainingModuleLoader

- Input: file/object conforming to `training-module.schema.json`.
- Output: immutable validated Training Module model.
- Rejects duplicate module IDs and missing referenced Case IDs when a catalog is assembled.
- Does not fetch knowledge through RAG or modify content.

## CaseLoader

- Input: file/object conforming to server-side `case.schema.json`.
- Output: immutable authoritative Case model.
- Rejects duplicate Case IDs and invalid fault/evidence structures.
- Never returns the authoritative Case directly to learner/Tutor callers.

## CaseSession

- Created from `user_id` and an already loaded Case.
- Initial values follow `learner-session.schema.json`: stage `START`, no seen Evidence, no hypothesis/actions, zero counters and zero skill scores.
- Owns mutable Session data while retaining a private immutable Case reference.
- Can create the `CasePublicState` projection and record schema-valid `LearnerAction` values.
- Can submit a non-empty Hypothesis, updating `current_hypothesis` and append-only `hypothesis_history` without changing stage.
- Does not implement legal stage transitions; that belongs to Phase 3.
- Does not interpret or score `scoring_rules`.

## EvidenceManager

- Accepts an explicit `evidence_id` request for the Session's Case.
- Rejects unknown IDs without mutating the Session.
- Returns only `ReleasedEvidence` (`id`, `type`, `content`).
- Adds the ID to `evidence_seen`; a repeated request does not duplicate the ID.
- Never returns `related_faults`, `information_value`, `fault`, `ground_truth`, `optimal_path` or `scoring_rules`.
- Phase 2 does not invent stage-based release conditions; Phase 3 may wrap requests with State Machine authorization.

## ProgressManager

- Aggregates completed Case IDs per Module from completed Session inputs.
- Produces `LearnerProfile` with module progress and current five-dimensional scores.
- Accepts a preselected `recommended_case_id` or `None`; automatic recommendation belongs to a later Skill/selection Spec.
- Does not calculate Skill scores or interpret Case scoring rules.

## Contract ownership

JSON Schemas remain the product contracts. Pydantic models must be parity-tested against them and may not add public fields. Any mismatch returns to a Contract Change Proposal.
