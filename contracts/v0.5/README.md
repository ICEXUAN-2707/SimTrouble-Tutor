# Product v0.5 Contracts

This package freezes the public identity models introduced by Product v0.5.
The learning payloads referenced by authenticated training routes continue to
use the frozen Product v0.4 schemas.

- `auth-user.schema.json`: public account identity.
- `auth-session.schema.json`: authenticated identity, expiry and CSRF proof.
- `auth-register-request.schema.json`: strict registration input.
- `auth-login-request.schema.json`: strict login input.

Password fields, cookie contents and SQLite rows are private implementation
details and are intentionally absent from public response schemas.
