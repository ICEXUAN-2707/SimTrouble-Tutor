# Phase 2 Goal — Training Core

> Status: COMPLETED — implemented and regression-tested after CCP-001/CCP-002 acceptance.

## Goal

Implement the smallest deterministic Training Core that can load frozen module/Case data, create an isolated learner Session, disclose requested Evidence through the public projection, and preserve progress inputs without LLM or simulation dependencies.

## Frozen implementation targets

- `TrainingModuleLoader`
- `CaseLoader`
- `CaseSession`
- `EvidenceManager`
- `ProgressManager`

## Required quality

- Contract-first Pydantic validation;
- no hidden-field leakage;
- no mutation of authoritative Case data;
- deterministic unit tests;
- no Phase 3 state-transition logic.
