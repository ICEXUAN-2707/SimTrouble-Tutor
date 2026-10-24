# SimTrouble Tutor Product Spec v0.5

> Status: proposed identity and local-persistence baseline
> Date: 2026-10-24
> Base: Product v0.4 integration candidate `845eef8`

## 1. Objective

Product v0.5 adds the smallest account boundary required to associate a learner
with their own training Sessions on one local deployment. It does not change
the Product v0.4 CAD, Tutor, diagnosis, evaluation or scoring semantics.

The deliverable is:

1. local username/password registration and login;
2. server-side revocable authentication sessions in SQLite;
3. authenticated ownership of newly created training Sessions;
4. denial of cross-user access without disclosing whether a Session exists;
5. an integrated login/register experience in `apps/training_web`.

## 2. User journey

1. An unauthenticated learner sees login and registration instead of the
   training workspace.
2. Registration creates one account and one authentication session.
3. Login rotates to a new random authentication session.
4. The learner creates and completes Product v0.4 training Sessions normally.
5. Refreshing the browser restores the authenticated identity while the
   authentication session is valid.
6. Logout revokes the server-side authentication session and clears cookies.

## 3. Identity and ownership boundary

- User IDs are opaque server-generated strings and are never accepted from a
  registration, login or create-Session request.
- A Product v0.5 training Session is created with the authenticated User ID.
- Every read or command for that Session must compare the authenticated User ID
  with the authoritative `LearnerSession.user_id` before domain work begins.
- Missing, expired, revoked, malformed and wrong-owner credentials return the
  same public authentication/not-found shapes defined by the contract.
- Authentication never grants authority to mutate Core state directly.
- Existing Product v0.4 anonymous Sessions remain a compatibility path only.
  Anonymous routes must not read or mutate an account-owned Session.

## 4. Storage boundary

SQLite stores only:

- account identity and password verifier;
- authentication session token digest, CSRF token digest and expiry;
- schema version and bounded failed-login state.

The raw authentication token, raw CSRF token, passwords, Tutor prompts, Case
private data, training Trace and Reports are not stored in the authentication
database. Product v0.5 does not make authoritative training Sessions durable;
they remain process-local and are lost when the API restarts.

Database schema changes are versioned and fail closed when a newer unsupported
schema is encountered. Runtime database files remain outside Git.

## 5. Security baseline

- Passwords use a versioned salted password-based derivation format.
- Authentication tokens contain at least 256 bits of randomness; SQLite stores
  only their SHA-256 digests.
- Authentication cookies are `HttpOnly`, `SameSite=Lax`, path `/`, and use
  `Secure` when configured for HTTPS.
- State-changing authenticated requests require an `X-CSRF-Token` value that
  matches both the browser CSRF cookie and the server-side session digest.
- Login failure responses do not disclose whether the account exists.
- Repeated failed logins are bounded by a persisted per-account-key limiter.
- API responses include basic anti-sniffing, framing and referrer headers.
- Secrets, password values, raw tokens and provider credentials never enter
  application logs, Trace, metrics or API error details.

## 6. Availability and recovery

- Missing credentials yield `401 authentication_required`.
- A wrong owner yields `404 session_not_found` to avoid resource enumeration.
- A bad or missing CSRF value yields `403 csrf_validation_failed`.
- SQLite unavailability fails the authentication operation; it must never fall
  back to an implicitly authenticated identity.
- The deterministic rule Tutor remains available after login when LLM providers
  are disabled or unavailable.

## 7. Non-goals

- email or phone verification;
- password reset or account recovery;
- roles, administrators, organizations or multi-tenancy;
- OAuth, social login, SSO or institutional identity providers;
- cloud sync, cross-device learning history or durable training Sessions;
- profile editing, account deletion UI or analytics dashboards;
- importing the standalone server-rendered HTML application as a second app.

## 8. Acceptance

- Registration, login, identity restore and logout pass API and browser tests.
- Password and raw-token values are absent from the database and responses.
- Cross-user Session reads and commands return `404 session_not_found`.
- Missing/expired credentials and invalid CSRF values fail closed.
- Product v0.4 anonymous regression tests remain green.
- All Product v0.4 Python, TypeScript, production-build and browser gates pass.
- No `.db`, `.env`, local secret, `.venv` or generated build file is committed.

