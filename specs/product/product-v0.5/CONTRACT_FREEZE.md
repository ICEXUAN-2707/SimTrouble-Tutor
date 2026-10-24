# Product v0.5 Identity Contract Freeze

> Status: proposed; implementation is authorized only after review
> Date: 2026-10-24

## Public models

`AuthUserV05`:

| Field | Type | Rule |
|---|---|---|
| `user_id` | string | opaque, server-generated, non-empty |
| `username` | string | 3-32 allowed characters |
| `display_name` | string | 1-32 characters |

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

## Request shapes

Registration:

```json
{
  "username": "learner01",
  "password": "example-password",
  "display_name": "Learner"
}
```

Login:

```json
{
  "username": "learner01",
  "password": "example-password"
}
```

Unknown fields are rejected. Passwords are accepted only in these two request
bodies and are excluded from validation-error echoes and logs.

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
details require a Product v0.5 contract change proposal and parity tests.

