# Product v0.5 Authentication Foundation

> Status: implementation complete on `task/product-v0.5-auth-foundation`
> Base: Product v0.4 integration candidate `845eef8`
> Contract: `specs/product/product-v0.5/CONTRACT_FREEZE.md`

## Delivered

- versioned SQLite account and authentication-session schema;
- salted PBKDF2-SHA256 password verifiers and transparent iteration upgrade;
- random server-issued authentication and CSRF tokens with digest-only storage;
- persisted failed-login window and lock with stale-row cleanup and a 4096-row
  cap for unknown usernames;
- uniform `401 invalid_credentials` behavior across unknown, locked and
  capacity-evicted account keys, with one real or dummy verifier check per
  well-formed login attempt;
- strict request validation for canonical usernames, exact 15-128-character
  registration passwords and optional non-blank display names;
- registration, login, identity restore and logout APIs;
- `HttpOnly` authentication cookie, CSRF double proof and configurable Secure flag;
- authenticated `/api/v0.5/sessions` learning routes;
- authoritative training-Session ownership checks across Evidence, Hypothesis,
  Tutor, Diagnosis and Report operations;
- ownership checks before report create-once lookup, including completed
  diagnosis submissions through authenticated and anonymous routes;
- strict cookie-security configuration and migration-time failed-login cleanup;
- centralized runtime authentication-expiry cleanup for all learner UI state;
- integrated Vite login/register/logout interface;
- Product v0.4 anonymous compatibility without access to account-owned Sessions.

## Storage truth

Only accounts, authentication sessions, CSRF digests and bounded failed-login
state are durable. Training Sessions, Tutor conversations and Reports remain
process-local and are lost when the API restarts. This implementation therefore
does not claim durable learning history or cloud sync.

## Verification

- 154 Python tests: pass;
- Product v0.5 contract/repository/API tests: pass;
- TypeScript type check and production build: pass;
- browser E2E including registration, logout, login, desktop/mobile learning,
  Tutor fallback, diagnosis and report: pass;
- `npm audit`: 0 vulnerabilities;
- `git diff --check`: pass.

## Remaining gates

- human review of the v0.5 contract task PR;
- human review of the implementation task PR;
- GitHub Actions result on the pushed implementation commit;
- Product v0.4 Phase gate and merge into `develop`;
- rebase the stacked v0.5 Phase onto that updated `develop` before Phase merge.

Password recovery, account deletion UI, roles, SSO and durable learning history
remain explicitly out of scope.
