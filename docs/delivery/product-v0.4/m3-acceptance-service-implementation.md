# Product v0.4 M3 Acceptance Service Implementation

Date: 2026-10-27
Branch: `task/product-v0.4-m3-acceptance-service`
Base: `phase/product-v0.4@c67d131`

## Delivered

- Added a Windows double-click entry and CLI for local Product v0.4 acceptance.
- Reuses the existing Tutor settings and registry, validates local `.env.local`, keeps Provider secrets in the API child process, and removes them from the build and Preview environments.
- Builds TypeScript and the Vite production bundle before starting FastAPI and Vite Preview.
- Configured Preview `/api` and `/healthz` proxies, strict ports `127.0.0.1:8001` and `127.0.0.1:5174`, version-aware readiness, and cleanup of launcher-owned processes only.
- Writes service logs under ignored `var/acceptance/logs/`; exact secret values and common credential fields are redacted. Console output safely replaces characters unsupported by legacy Windows encodings while log files remain UTF-8.
- Added an explicit `--ci-smoke` mode. It runs the existing Playwright browser suite against production Preview, then shuts down the services. It does not call a real Provider.
- Added a local `.env.example` matching the v0.5 shared provider example and documented setup, acceptance, and explicit real-smoke commands.

## Verification

- Acceptance launcher unit tests: 6 passed.
- Full Product v0.4 Python suite: 137 passed.
- `npm audit --audit-level=high`: 0 vulnerabilities.
- Launcher `--check-only`: passed.
- Launcher production build + Preview + `e2e/smoke-ci.mjs`: passed, including the report flow, Step-4 unlock, controlled Tutor success/fallback scenarios, and desktop/tablet/mobile viewports.
- TypeScript and Vite production build passed. Vite reports the existing Three.js chunk above 500 kB.
- Explicit real DeepSeek smoke: passed one request with retries disabled; validated response mode and safe suggested action. The key was read from the process environment and was not printed or written to a file.

## Remaining gates

- Complete product-owner browser acceptance on the production Preview and record the result.
- Merge this task into the v0.4 Phase, rerun the Phase gate and browser acceptance on the resulting RC, then follow [the v0.4/v0.5 develop integration plan](v0.4-v0.5-develop-integration-plan.md).

This task adds no database work, authentication, public API, Tutor behavior, or frontend redesign.
