# Learning Contracts v0.4

This directory is the versioned contract package for Product v0.4 tutoring,
diagnosis evaluation, and learning reports. It does not replace or silently
modify the frozen Phase 1 schemas in `contracts/schemas/`.

Contract rules:

- Tutor requests contain learner-safe public projections only.
- Tutor responses are structured and advisory; they cannot mutate Session state.
- Evaluator responses contain qualitative findings and no authoritative score.
- Program code applies versioned scoring rules and produces the final report.
- `not_assessed` dimensions have a null score and zero effective weight.

The matching runtime models live in
`apps/training_api/learning_models.py` and are parity-tested.

