# Product v0.5 Identity and Persistence Task Plan

> Base dependency: Product v0.4 must pass its Phase gate before this Phase may
> enter `develop`.

## T0 — Contract and threat boundary

- Freeze the Product v0.5 scope, routes, public models and stable errors.
- Freeze authentication-to-training-Session ownership rules.
- Freeze SQLite and cookie/CSRF boundaries.

## T1 — Authentication repository and API

- Add versioned SQLite schema initialization.
- Add account creation, password verification and login-rate limiting.
- Add revocable server-side authentication sessions.
- Add register, login, identity restore and logout routes.
- Add security headers and configuration validation.

## T2 — Training ownership

- Create authenticated training Sessions with the authenticated User ID.
- Guard every Session/Tutor/Diagnosis/Report operation by owner.
- Preserve Product v0.4 anonymous compatibility without allowing it to access
  account-owned Sessions.

## T3 — Web integration

- Add login/register views to the existing Vite application.
- Restore identity before creating the page-lifetime training Session.
- Send credentials and CSRF proof on the approved routes.
- Clear learner UI state after logout or authentication expiry.

## T4 — Verification and Phase gate

- Contract/model parity tests.
- Auth repository, expiry, rate-limit and CSRF unit tests.
- Cross-user ownership and regression API tests.
- Desktop/mobile browser flow.
- Full Product v0.4 regression, production build and dependency audit.

The Phase may enter `develop` only after Product v0.4 has entered `develop` and
all T4 checks pass.

