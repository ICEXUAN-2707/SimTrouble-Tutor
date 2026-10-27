# Product v0.5 Identity and Persistence Task Plan

> Base dependency: Product v0.4 must pass its Phase gate before this Phase may
> enter `develop`.
> Implementation status: M0 and M2 have merged into the Product v0.5 Phase; M1 local launcher implementation is complete. Browser acceptance is recorded in the M1 delivery note. Product v0.4 integration remains the prerequisite before this Phase can enter `develop`.

## T0 — Contract and threat boundary

Status: complete on `task/product-v0.5-auth-contract`.

- Freeze the Product v0.5 scope, routes, public models and stable errors.
- Freeze authentication-to-training-Session ownership rules.
- Freeze SQLite and cookie/CSRF boundaries.

## T1 — Authentication repository and API

Status: implementation complete.

- Add versioned SQLite schema initialization.
- Add account creation, password verification and login-rate limiting.
- Bound failed-login persistence by expiry and a 4096-row unknown-name cap.
- Add revocable server-side authentication sessions.
- Add register, login, identity restore and logout routes.
- Add security headers and configuration validation.

## T2 — Training ownership

Status: implementation complete.

- Create authenticated training Sessions with the authenticated User ID.
- Guard every Session/Tutor/Diagnosis/Report operation by owner.
- Preserve Product v0.4 anonymous compatibility without allowing it to access
  account-owned Sessions.

## T3 — Web integration

Status: implementation complete.

- Add login/register views to the existing Vite application.
- Restore identity before creating the page-lifetime training Session.
- Send credentials and CSRF proof on the approved routes.
- Clear learner UI state after logout or authentication expiry.

## T4 — Verification and Phase gate

Status: local gates complete; GitHub review/CI and base-Phase ordering remain.

- Contract/model parity tests.
- Auth repository, expiry, rate-limit enumeration-resistance and CSRF tests.
- Cross-user ownership and regression API tests.
- Desktop/mobile browser flow.
- Full Product v0.4 regression, production build and dependency audit.

The Phase may enter `develop` only after Product v0.4 has entered `develop` and
all T4 checks pass.

## T5 / M2 — Minimal completed training records

Scope authorized on 2026-10-26; see [M2_STORAGE.md](M2_STORAGE.md).

1. Add one `training_records` table to the existing SQLite file and initializer.
2. Save a user-owned public completion snapshot and authoritative report inside
   the existing atomic completion callback; read through existing GET routes.
3. Verify restart/relogin, ownership, duplicate submission, failed-write retry,
   migration preservation and full regression.

No history list, new route, UI, export, analytics, unfinished-session recovery,
Tutor conversation persistence, ORM or additional database service.
Implementation and local verification complete: seven new M2 tests, all 163
Python tests, production build and authenticated Edge browser E2E pass.
PR #24 (M0) and PR #25 (M2) have merged into the Product v0.5 Phase. This does not bypass the Product v0.4 to `develop` ordering requirement.

## T6 / M1 — Windows launcher and configuration preflight

See [M1_LOCAL_LAUNCHER.md](M1_LOCAL_LAUNCHER.md).

- Add a double-click Windows entry and a small Python launcher.
- Check local runtimes, Vite packages, existing Provider configuration and fixed ports.
- Pass Provider secrets to the API process only; start API and Vite and wait for health.
- Clean up only the two services created by this launcher.
- Keep the existing credential-gated DeepSeek smoke as a separate, explicit command.

No dependency installation, production deployment, new API, frontend flow or database work. M0 and M2 are merged. Launcher preflight and startup succeeded; browser acceptance was completed by the user. Human UAT and existing deployment acceptance remain.
