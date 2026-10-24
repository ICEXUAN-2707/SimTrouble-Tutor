"""Versioned SQLite account and revocable authentication-session storage."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .models import AuthUserV05


SCHEMA_VERSION = 1
PASSWORD_ITERATIONS = 600_000
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
LOGIN_WINDOW_SECONDS = 5 * 60
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCK_SECONDS = 15 * 60


class UsernameUnavailableError(ValueError):
    """Raised when a normalized username already exists."""


class LoginRateLimitedError(RuntimeError):
    """Raised after the bounded failed-login threshold is reached."""


class UnsupportedSchemaError(RuntimeError):
    """Raised when the database is newer than this application."""


@dataclass(frozen=True)
class IssuedAuthentication:
    user: AuthUserV05
    token: str
    csrf_token: str
    expires_at: int


@dataclass(frozen=True)
class AuthenticationContext:
    user: AuthUserV05
    expires_at: int
    csrf_digest: str


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _username_key(value: str) -> str:
    return value.strip().casefold()


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = PASSWORD_ITERATIONS,
) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_text),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _needs_rehash(stored: str) -> bool:
    try:
        return int(stored.split("$")[1]) < PASSWORD_ITERATIONS
    except (IndexError, ValueError):
        return True


_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


def default_database_path() -> Path:
    configured = os.environ.get("SIMTROUBLE_AUTH_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "var" / "auth.db"


class AuthenticationStore:
    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.database_path = (
            Path(database_path) if database_path is not None else default_database_path()
        )
        self._clock = clock

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current > SCHEMA_VERSION:
                raise UnsupportedSchemaError(
                    f"auth schema {current} is newer than supported {SCHEMA_VERSION}"
                )
            if current == 0:
                connection.executescript(
                    """
                    CREATE TABLE users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        username_key TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    );
                    CREATE TABLE auth_sessions (
                        token_hash TEXT PRIMARY KEY,
                        csrf_hash TEXT NOT NULL,
                        user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL
                    );
                    CREATE INDEX auth_sessions_expiry_idx
                        ON auth_sessions(expires_at);
                    CREATE INDEX auth_sessions_user_idx
                        ON auth_sessions(user_id);
                    CREATE TABLE login_failures (
                        account_key TEXT PRIMARY KEY,
                        failed_count INTEGER NOT NULL,
                        window_started_at INTEGER NOT NULL,
                        locked_until INTEGER NOT NULL
                    );
                    PRAGMA user_version = 1;
                    """
                )

    def create_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str | None,
    ) -> AuthUserV05:
        user = AuthUserV05(
            user_id=str(uuid4()),
            username=username,
            display_name=display_name or username,
        )
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO users "
                    "(user_id, username, username_key, display_name, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        user.user_id,
                        user.username,
                        _username_key(user.username),
                        user.display_name,
                        hash_password(password),
                        int(self._clock()),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise UsernameUnavailableError(username) from exc
        return user

    def authenticate(self, username: str, password: str) -> AuthUserV05 | None:
        account_key = _username_key(username)
        now = int(self._clock())
        with self._connect() as connection:
            failure = connection.execute(
                "SELECT failed_count, window_started_at, locked_until "
                "FROM login_failures WHERE account_key = ?",
                (account_key,),
            ).fetchone()
            if failure is not None and int(failure["locked_until"]) > now:
                raise LoginRateLimitedError(account_key)

            row = connection.execute(
                "SELECT user_id, username, display_name, password_hash "
                "FROM users WHERE username_key = ?",
                (account_key,),
            ).fetchone()
            stored = row["password_hash"] if row is not None else _DUMMY_PASSWORD_HASH
            valid = verify_password(password, stored)
            if row is None or not valid:
                self._record_failure(connection, account_key, failure, now)
                return None

            connection.execute(
                "DELETE FROM login_failures WHERE account_key = ?", (account_key,)
            )
            if _needs_rehash(stored):
                connection.execute(
                    "UPDATE users SET password_hash = ? WHERE user_id = ?",
                    (hash_password(password), row["user_id"]),
                )
            return AuthUserV05(
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
            )

    def _record_failure(
        self,
        connection: sqlite3.Connection,
        account_key: str,
        failure: sqlite3.Row | None,
        now: int,
    ) -> None:
        if failure is None or now - int(failure["window_started_at"]) >= LOGIN_WINDOW_SECONDS:
            count = 1
            window_started = now
        else:
            count = int(failure["failed_count"]) + 1
            window_started = int(failure["window_started_at"])
        locked_until = now + LOGIN_LOCK_SECONDS if count >= LOGIN_FAILURE_LIMIT else 0
        connection.execute(
            "INSERT INTO login_failures "
            "(account_key, failed_count, window_started_at, locked_until) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(account_key) DO UPDATE SET "
            "failed_count=excluded.failed_count, "
            "window_started_at=excluded.window_started_at, "
            "locked_until=excluded.locked_until",
            (account_key, count, window_started, locked_until),
        )

    def issue_session(self, user: AuthUserV05) -> IssuedAuthentication:
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = int(self._clock())
        expires_at = now + SESSION_TTL_SECONDS
        with self._connect() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
            connection.execute(
                "INSERT INTO auth_sessions "
                "(token_hash, csrf_hash, user_id, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (_digest(token), _digest(csrf_token), user.user_id, now, expires_at),
            )
        return IssuedAuthentication(user, token, csrf_token, expires_at)

    def resolve(self, token: str) -> AuthenticationContext | None:
        now = int(self._clock())
        with self._connect() as connection:
            row = connection.execute(
                "SELECT u.user_id, u.username, u.display_name, "
                "s.csrf_hash, s.expires_at "
                "FROM auth_sessions AS s JOIN users AS u ON u.user_id = s.user_id "
                "WHERE s.token_hash = ? AND s.expires_at > ?",
                (_digest(token), now),
            ).fetchone()
        if row is None:
            return None
        return AuthenticationContext(
            user=AuthUserV05(
                user_id=row["user_id"],
                username=row["username"],
                display_name=row["display_name"],
            ),
            expires_at=int(row["expires_at"]),
            csrf_digest=row["csrf_hash"],
        )

    def csrf_matches(self, context: AuthenticationContext, value: str) -> bool:
        return hmac.compare_digest(context.csrf_digest, _digest(value))

    def revoke_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?", (_digest(token),)
            )
