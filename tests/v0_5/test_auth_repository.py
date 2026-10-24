from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from apps.training_api.auth.repository import (
    AuthenticationStore,
    LoginRateLimitedError,
    UsernameUnavailableError,
    hash_password,
    verify_password,
)


class AuthenticationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.now = 1_800_000_000
        self.store = AuthenticationStore(
            Path(directory.name) / "auth.db",
            clock=lambda: self.now,
        )
        self.store.initialize()

    def test_password_hash_is_salted_versioned_and_verifiable(self) -> None:
        first = hash_password("correct-horse")
        second = hash_password("correct-horse")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct-horse", first))
        self.assertFalse(verify_password("wrong-password", first))
        self.assertFalse(verify_password("anything", "malformed"))

    def test_account_and_session_store_no_raw_secrets(self) -> None:
        user = self.store.create_user(
            username="Learner01",
            password="correct-horse",
            display_name="Learner",
        )
        issued = self.store.issue_session(user)
        resolved = self.store.resolve(issued.token)
        self.assertIsNotNone(resolved)
        self.assertEqual(user, resolved.user)
        self.assertTrue(self.store.csrf_matches(resolved, issued.csrf_token))

        with closing(sqlite3.connect(self.store.database_path)) as connection:
            values = " ".join(
                str(value)
                for row in connection.execute("SELECT * FROM users")
                for value in row
            ) + " " + " ".join(
                str(value)
                for row in connection.execute("SELECT * FROM auth_sessions")
                for value in row
            )
            version = connection.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(1, version)
        self.assertNotIn("correct-horse", values)
        self.assertNotIn(issued.token, values)
        self.assertNotIn(issued.csrf_token, values)

    def test_username_is_case_insensitive_and_duplicate_is_rejected(self) -> None:
        self.store.create_user(
            username="Learner01",
            password="correct-horse",
            display_name=None,
        )
        authenticated = self.store.authenticate("learner01", "correct-horse")
        self.assertIsNotNone(authenticated)
        with self.assertRaises(UsernameUnavailableError):
            self.store.create_user(
                username="LEARNER01",
                password="another-password",
                display_name=None,
            )

    def test_expired_and_revoked_sessions_fail_closed(self) -> None:
        user = self.store.create_user(
            username="learner01",
            password="correct-horse",
            display_name=None,
        )
        issued = self.store.issue_session(user)
        self.store.revoke_session(issued.token)
        self.assertIsNone(self.store.resolve(issued.token))

        issued = self.store.issue_session(user)
        self.now = issued.expires_at
        self.assertIsNone(self.store.resolve(issued.token))

    def test_failed_login_is_rate_limited_without_account_disclosure(self) -> None:
        for _ in range(5):
            self.assertIsNone(self.store.authenticate("missing-user", "wrong-password"))
        with self.assertRaises(LoginRateLimitedError):
            self.store.authenticate("missing-user", "wrong-password")


if __name__ == "__main__":
    unittest.main()
