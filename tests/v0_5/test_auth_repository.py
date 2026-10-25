from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from apps.training_api.auth.repository import (
    AuthenticationStore,
    LoginRateLimitedError,
    UNKNOWN_LOGIN_FAILURE_CAP,
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
        self.assertEqual(2, version)
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

    def test_schema_v1_failure_rows_are_migrated_and_classified(self) -> None:
        legacy_path = self.store.database_path.with_name("legacy.db")
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE users (username_key TEXT NOT NULL UNIQUE);
                INSERT INTO users(username_key) VALUES ('known01');
                CREATE TABLE login_failures (
                    account_key TEXT PRIMARY KEY,
                    failed_count INTEGER NOT NULL,
                    window_started_at INTEGER NOT NULL,
                    locked_until INTEGER NOT NULL
                );
                INSERT INTO login_failures VALUES ('known01', 2, 100, 0);
                INSERT INTO login_failures VALUES ('missing01', 1, 200, 0);
                PRAGMA user_version = 1;
                """
            )

        legacy = AuthenticationStore(legacy_path, clock=lambda: self.now)
        legacy.initialize()
        with closing(sqlite3.connect(legacy_path)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            rows = connection.execute(
                "SELECT account_key, is_known, updated_at FROM login_failures "
                "ORDER BY account_key"
            ).fetchall()
        self.assertEqual(2, version)
        self.assertEqual(
            [("known01", 1, 100), ("missing01", 0, 200)],
            rows,
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

        restarted = AuthenticationStore(self.store.database_path, clock=lambda: self.now)
        restarted.initialize()
        with self.assertRaises(LoginRateLimitedError):
            restarted.authenticate("missing-user", "wrong-password")

    def test_stale_unknown_login_failure_is_removed_on_next_failure(self) -> None:
        with patch(
            "apps.training_api.auth.repository.verify_password", return_value=False
        ):
            self.assertIsNone(self.store.authenticate("missing-old", "wrong"))
            self.now += 5 * 60
            self.assertIsNone(self.store.authenticate("missing-new", "wrong"))

        with closing(sqlite3.connect(self.store.database_path)) as connection:
            keys = {
                row[0] for row in connection.execute(
                    "SELECT account_key FROM login_failures"
                )
            }
        self.assertNotIn("missing-old", keys)
        self.assertIn("missing-new", keys)

    def test_unknown_login_failure_rows_have_a_hard_capacity(self) -> None:
        self.assertEqual(4096, UNKNOWN_LOGIN_FAILURE_CAP)
        with (
            patch(
                "apps.training_api.auth.repository.UNKNOWN_LOGIN_FAILURE_CAP", 3
            ),
            patch(
                "apps.training_api.auth.repository.verify_password", return_value=False
            ),
        ):
            for index in range(7):
                self.assertIsNone(
                    self.store.authenticate(f"missing-{index}", "wrong")
                )

        with closing(sqlite3.connect(self.store.database_path)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM login_failures WHERE is_known = 0"
            ).fetchone()[0]
        self.assertEqual(3, count)

        with closing(sqlite3.connect(self.store.database_path)) as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO login_failures "
                "(account_key, failed_count, window_started_at, locked_until, is_known, updated_at) "
                "VALUES (?, 1, ?, 0, 0, ?)",
                [(f"legacy-{index}", self.now, index) for index in range(6)],
            )
            connection.commit()
        with (
            patch(
                "apps.training_api.auth.repository.UNKNOWN_LOGIN_FAILURE_CAP", 3
            ),
            patch(
                "apps.training_api.auth.repository.verify_password", return_value=False
            ),
        ):
            self.assertIsNone(self.store.authenticate("trigger-key", "wrong"))
        with closing(sqlite3.connect(self.store.database_path)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM login_failures WHERE is_known = 0"
            ).fetchone()[0]
        self.assertEqual(3, count)

    def test_unknown_name_churn_never_evicts_registered_account_lock(self) -> None:
        self.store.create_user(
            username="Protected01",
            password="correct-horse-battery",
            display_name=None,
        )
        with (
            patch(
                "apps.training_api.auth.repository.UNKNOWN_LOGIN_FAILURE_CAP", 2
            ),
            patch(
                "apps.training_api.auth.repository.verify_password", return_value=False
            ),
        ):
            for _ in range(5):
                self.assertIsNone(self.store.authenticate("protected01", "wrong"))
            for index in range(5):
                self.assertIsNone(
                    self.store.authenticate(f"unknown-{index}", "wrong")
                )

        with closing(sqlite3.connect(self.store.database_path)) as connection:
            protected = connection.execute(
                "SELECT is_known, locked_until FROM login_failures "
                "WHERE account_key = 'protected01'"
            ).fetchone()
            unknown_count = connection.execute(
                "SELECT COUNT(*) FROM login_failures WHERE is_known = 0"
            ).fetchone()[0]
            total_count = connection.execute(
                "SELECT COUNT(*) FROM login_failures"
            ).fetchone()[0]
        self.assertEqual((1, self.now + 15 * 60), protected)
        self.assertEqual(2, unknown_count)
        self.assertLessEqual(total_count, 1 + 2)
        with self.assertRaises(LoginRateLimitedError):
            self.store.authenticate("Protected01", "correct-horse-battery")


if __name__ == "__main__":
    unittest.main()
