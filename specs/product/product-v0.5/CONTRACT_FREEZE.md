# Product v0.5 Identity Contract Freeze

> Status: proposed; implementation is authorized only after review
> Date: 2026-10-24

## Public models

`AuthUserV05`:

| Field | Type | Rule |
|---|---|---|
| `user_id` | string | opaque, server-generated, non-empty |
| `username` | string | 3-32 canonical username characters |
| `display_name` | string | 1-32 characters, no surrounding whitespace or control characters |

`AuthSessionV05`:

| Field | Type | Rule |
|---|---|---|
| `user` | `AuthUserV05` | current authenticated user |
| `expires_at` | integer | Unix epoch seconds |
| `csrf_token` | string | returned only at session creation/restore |

## Routes

| Method | Path | Auth | CSRF | Result |
|---|---|---:|---:|---|
| POST | `/api/v0.5/auth/register` | no | no | `201 AuthSessionV05` |
| POST | `/api/v0.5/auth/login` | no | no | `200 AuthSessionV05` |
| GET | `/api/v0.5/auth/me` | yes | no | `200 AuthSessionV05` |
| POST | `/api/v0.5/auth/logout` | yes | yes | `204` |
| POST | `/api/v0.5/sessions` | yes | yes | Product v0.4 `SessionView` |
| GET | `/api/v0.5/sessions/{session_id}` | yes | no | Product v0.4 `SessionView` |
| POST | `/api/v0.5/sessions/{session_id}/evidence` | yes | yes | Product v0.4 `EvidenceResponse` |
| POST | `/api/v0.5/sessions/{session_id}/hypotheses` | yes | yes | Product v0.4 `SessionView` |
| POST | `/api/v0.5/sessions/{session_id}/tutor` | yes | yes | Product v0.4 `TutorTurnResponse` |
| POST | `/api/v0.5/sessions/{session_id}/diagnosis` | yes | yes | Product v0.4 `SessionView` |
| GET | `/api/v0.5/sessions/{session_id}/report` | yes | no | Product v0.4 `TrainingReportV04` |

Scene configuration remains public at the Product v0.4 path. Product v0.4
anonymous Session routes remain for compatibility and can operate only on
Sessions whose authoritative User ID begins with `anonymous:`.

## Request contracts

Registration and login bodies are frozen by
`auth-register-request.schema.json` and `auth-login-request.schema.json`.
Unknown fields are rejected.

Username rules are identical for registration, login and public identity:

- 3-32 Unicode code points;
- ASCII letters, digits, `_`, `-`, and CJK Unified Ideographs in
  `U+4E00-U+9FFF` only;
- no whitespace trimming or other Unicode normalization is performed;
- the spelling supplied at registration is stored and returned;
- uniqueness and login matching use an identity key formed by lowercasing ASCII
  letters; therefore `Learner01` and `learner01` identify the same account.

Registration passwords contain 15-128 Unicode code points. Login accepts
1-128 code points so a future password-policy change cannot prevent an existing
credential from being verified. Passwords are compared exactly: the server
does not trim, case-fold, truncate or Unicode-normalize them. No character-class
composition rule is imposed.

`display_name` is optional during registration. When omitted, it defaults to
the registered username. When supplied, it contains 1-32 Unicode code points
and has no leading/trailing whitespace or control characters. JSON `null`, an
empty string and a whitespace-only value are invalid.

### Registration

```json
{
  "username": "learner01",
  "password": "example-password-long",
  "display_name": "Learner"
}
```

### Login

```json
{
  "username": "learner01",
  "password": "example-password-long"
}
```

Passwords are accepted only in these two request bodies and are excluded from
validation-error echoes and logs.

## Failed-login state bound

- Five failures for one account identity key within five minutes lock that key
  for 15 minutes.
- Failure rows become stale once both their observation window and lock have
  expired, and stale rows are deleted during subsequent login-failure writes.
- A registered account retains at most one failure row and an active registered
  account lock is never evicted to make room for unknown names.
- Failure rows for unknown usernames have a hard capacity of 4096. After stale
  cleanup, the oldest unknown-name row is evicted before that capacity can be
  exceeded.
- Cleanup, capacity enforcement and failure recording occur in one SQLite
  transaction. The invariant is
  `login_failures rows <= registered users + 4096`.
- Public error bodies remain identical whether or not the username exists.

## Stable errors

| HTTP | `detail` | Meaning |
|---:|---|---|
| 400 | `invalid_registration` | invalid username, password or display name |
| 401 | `authentication_required` | missing, expired, revoked or invalid session |
| 401 | `invalid_credentials` | generic failed login |
| 403 | `csrf_validation_failed` | missing or invalid CSRF proof |
| 409 | `username_unavailable` | normalized username already registered |
| 429 | `login_rate_limited` | bounded failed-login threshold reached |
| 404 | `session_not_found` | absent or wrong-owner training Session |

Existing Product v0.4 domain errors retain their current status and detail.

## Cookie contract

- Authentication cookie name: `simtrouble_auth`.
- CSRF cookie name: `simtrouble_csrf`.
- Authentication cookie is `HttpOnly`; CSRF cookie is readable by the browser.
- Both use `SameSite=Lax`, path `/`, the same lifetime and configurable `Secure`.
- Logout deletes both cookies with the same path and security attributes.

## Change control

Changes to public fields, paths, cookie names, ownership rules or stable error
details, request schemas, identity-key rules or failed-login bounds require a
Product v0.5 contract change proposal and parity tests.
