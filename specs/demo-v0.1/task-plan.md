# Demo v0.1 Task Plan

## D0 — Planning and repository clarity

- Branch: `task/demo-v0.1-planning`
- Scope: approved Demo Spec, branch-policy exception, README capability truth table, current/target architecture documents and local-input ignore rules.
- Product code: none.
- Exit: 57 regressions pass; no duplicate source is staged; Demo implementation has no unresolved boundary decision.

## D1 — Modular Demo shell

- Planned branch: `task/demo-v0.1-shell`
- Parent: latest `phase/demo-v0.1-integration`.
- Scope:
  - extract only presentation behavior from the local delivery package;
  - implement `apps/demo/` modules from `contract.md`;
  - use official Phase 3 Core and ST-001 data;
  - remove the parallel Demo event store in favor of Core Trace.
- Excludes: tests assigned to D2 beyond minimal unit support, public Contract changes and all items in `out_of_scope.md`.
- Exit: one-command local Demo starts and the existing 57 regressions pass.

## D2 — ST-001 HTTP E2E and startup smoke

- Planned branch: `task/demo-v0.1-e2e-smoke`
- Parent: latest Demo Phase branch after D1.
- Scope:
  - deterministic in-process HTTP E2E;
  - real subprocess startup/health smoke;
  - hidden-field and cookie-session assertions;
  - CI test discovery confirmation.
- Product behavior changes: none except defects required to meet the frozen Demo Contract.
- Exit: all Demo acceptance automation passes with all existing regressions.

## D3 — Demo integration gate

- Planned branch: `task/demo-v0.1-integration-gate`
- Scope: acceptance audit, clean-checkout run, dependency/scope scan and documentation status only.
- Exit: `phase/demo-v0.1-integration` is ready for PR to `develop`.

## Integration order

```text
D0 planning/docs
  ↓
D1 modular shell
  ↓
D2 E2E + startup smoke
  ↓
D3 integration gate
  ↓
phase/demo-v0.1-integration → develop
```

Every task must pass CI and an isolated merge test before integration. No task may commit `zjh/`, personal files or a duplicated Core tree.
