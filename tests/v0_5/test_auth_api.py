from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from apps.training_api.auth.repository import AuthenticationStore
from apps.training_api.main import CSRF_COOKIE_NAME, create_app
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.service import TutorService


TEST_PASSWORD = "correct-horse-battery"


class AuthenticationApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = AuthenticationStore(Path(directory.name) / "auth.db")
        self.store = store
        sessions = SessionService()
        self.app = create_app(
            session_service=sessions,
            tutor_service=TutorService(sessions),
            authentication_store=store,
        )
        transport = ASGITransport(app=self.app)
        self.alice = AsyncClient(transport=transport, base_url="http://testserver")
        self.bob = AsyncClient(transport=transport, base_url="http://testserver")

    async def asyncTearDown(self) -> None:
        await self.alice.aclose()
        await self.bob.aclose()

    async def register(self, client: AsyncClient, username: str) -> dict:
        response = await client.post(
            "/api/v0.5/auth/register",
            json={
                "username": username,
                "password": TEST_PASSWORD,
                "display_name": username.title(),
            },
        )
        self.assertEqual(201, response.status_code, response.text)
        return response.json()

    def csrf_headers(self, client: AsyncClient) -> dict[str, str]:
        token = client.cookies.get(CSRF_COOKIE_NAME)
        assert token is not None
        return {"X-CSRF-Token": token}

    async def test_register_restore_logout_and_security_headers(self) -> None:
        registered = await self.register(self.alice, "alice01")
        self.assertEqual("alice01", registered["user"]["username"])
        self.assertNotIn("password", str(registered))

        current = await self.alice.get("/api/v0.5/auth/me")
        self.assertEqual(200, current.status_code)
        self.assertEqual("nosniff", current.headers["x-content-type-options"])
        self.assertEqual("DENY", current.headers["x-frame-options"])

        rejected = await self.alice.post("/api/v0.5/auth/logout")
        self.assertEqual(403, rejected.status_code)
        logged_out = await self.alice.post(
            "/api/v0.5/auth/logout", headers=self.csrf_headers(self.alice)
        )
        self.assertEqual(204, logged_out.status_code)
        self.assertEqual(401, (await self.alice.get("/api/v0.5/auth/me")).status_code)

    async def test_login_errors_are_stable_and_bodies_are_not_echoed(self) -> None:
        invalid_registration = await self.alice.post(
            "/api/v0.5/auth/register",
            json={"username": "x", "password": "secret-value"},
        )
        self.assertEqual(400, invalid_registration.status_code)
        self.assertEqual("invalid_registration", invalid_registration.json()["detail"])
        self.assertNotIn("secret-value", invalid_registration.text)

        invalid_login = await self.alice.post(
            "/api/v0.5/auth/login",
            json={"username": "missing", "password": "secret-value"},
        )
        self.assertEqual(401, invalid_login.status_code)
        self.assertEqual("invalid_credentials", invalid_login.json()["detail"])
        self.assertNotIn("secret-value", invalid_login.text)

    async def test_auth_requests_enforce_frozen_input_contract(self) -> None:
        invalid_registrations = (
            {"username": " user01", "password": TEST_PASSWORD},
            {"username": "user.01", "password": TEST_PASSWORD},
            {"username": "user01", "password": "x" * 14},
            {"username": "user01", "password": TEST_PASSWORD, "display_name": None},
            {"username": "user01", "password": TEST_PASSWORD, "display_name": "   "},
            {"username": "user01", "password": TEST_PASSWORD, "display_name": "A\u0080B"},
            {"username": "user01", "password": TEST_PASSWORD, "display_name": "A\u0085B"},
            {"username": "user01", "password": TEST_PASSWORD, "display_name": "A\u009fB"},
            {"username": "user01", "password": TEST_PASSWORD, "unknown": True},
        )
        for payload in invalid_registrations:
            with self.subTest(payload=payload):
                response = await self.alice.post(
                    "/api/v0.5/auth/register", json=payload
                )
                self.assertEqual(400, response.status_code, response.text)
                self.assertEqual("invalid_registration", response.json()["detail"])

        invalid_logins = (
            {"username": " user01", "password": "x"},
            {"username": "user.01", "password": "x"},
            {"username": "user01", "password": ""},
            {"username": "user01", "password": "x", "unknown": True},
        )
        for payload in invalid_logins:
            with self.subTest(payload=payload):
                response = await self.alice.post(
                    "/api/v0.5/auth/login", json=payload
                )
                self.assertEqual(401, response.status_code, response.text)
                self.assertEqual("invalid_credentials", response.json()["detail"])

    async def test_capacity_pressure_cannot_reveal_account_existence(self) -> None:
        await self.register(self.alice, "target01")
        attempts = 0
        responses = []
        with (
            patch(
                "apps.training_api.auth.repository.UNKNOWN_LOGIN_FAILURE_CAP", 3
            ),
            patch(
                "apps.training_api.auth.repository.verify_password",
                return_value=False,
            ) as verifier,
        ):
            for _ in range(5):
                responses.append(
                    await self.bob.post(
                        "/api/v0.5/auth/login",
                        json={"username": "target01", "password": "wrong"},
                    )
                )
                attempts += 1
                responses.append(
                    await self.bob.post(
                        "/api/v0.5/auth/login",
                        json={"username": "missing-target", "password": "wrong"},
                    )
                )
                attempts += 1
            for index in range(6):
                responses.append(
                    await self.bob.post(
                        "/api/v0.5/auth/login",
                        json={"username": f"churn-{index}", "password": "wrong"},
                    )
                )
                attempts += 1

            known = await self.bob.post(
                "/api/v0.5/auth/login",
                json={"username": "target01", "password": TEST_PASSWORD},
            )
            unknown = await self.bob.post(
                "/api/v0.5/auth/login",
                json={"username": "missing-target", "password": TEST_PASSWORD},
            )
            responses.extend((known, unknown))
            attempts += 2
            self.assertEqual(attempts, verifier.call_count)

        for response in responses:
            self.assertEqual(401, response.status_code, response.text)
            self.assertEqual({"detail": "invalid_credentials"}, response.json())
            self.assertNotIn("retry-after", response.headers)
            self.assertNotIn("set-cookie", response.headers)
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.content, unknown.content)
        self.assertEqual(dict(known.headers), dict(unknown.headers))

        with closing(sqlite3.connect(self.store.database_path)) as connection:
            protected = connection.execute(
                "SELECT is_known, locked_until FROM login_failures "
                "WHERE account_key = 'target01'"
            ).fetchone()
            unknown_count = connection.execute(
                "SELECT COUNT(*) FROM login_failures WHERE is_known = 0"
            ).fetchone()[0]
        self.assertEqual(1, protected[0])
        self.assertGreater(protected[1], 0)
        self.assertLessEqual(unknown_count, 3)

    async def test_display_name_default_case_matching_and_exact_password(self) -> None:
        exact_password = " exact password "
        registered = await self.alice.post(
            "/api/v0.5/auth/register",
            json={"username": "CaseUser", "password": exact_password},
        )
        self.assertEqual(201, registered.status_code, registered.text)
        self.assertEqual("CaseUser", registered.json()["user"]["display_name"])

        wrong_password = await self.bob.post(
            "/api/v0.5/auth/login",
            json={"username": "caseuser", "password": exact_password.strip()},
        )
        self.assertEqual(401, wrong_password.status_code)
        logged_in = await self.bob.post(
            "/api/v0.5/auth/login",
            json={"username": "caseuser", "password": exact_password},
        )
        self.assertEqual(200, logged_in.status_code, logged_in.text)
        self.assertEqual("CaseUser", logged_in.json()["user"]["username"])

    async def test_authenticated_training_session_enforces_owner_and_csrf(self) -> None:
        await self.register(self.alice, "alice01")
        await self.register(self.bob, "bob0001")

        no_csrf = await self.alice.post(
            "/api/v0.5/sessions", json={"case_id": "ST-001"}
        )
        self.assertEqual(403, no_csrf.status_code)

        created = await self.alice.post(
            "/api/v0.5/sessions",
            json={"case_id": "ST-001"},
            headers=self.csrf_headers(self.alice),
        )
        self.assertEqual(201, created.status_code, created.text)
        session_id = created.json()["session_id"]

        owner_read = await self.alice.get(f"/api/v0.5/sessions/{session_id}")
        wrong_owner = await self.bob.get(f"/api/v0.5/sessions/{session_id}")
        anonymous_bypass = await self.alice.get(f"/api/v0.4/sessions/{session_id}")
        self.assertEqual(200, owner_read.status_code)
        self.assertEqual(404, wrong_owner.status_code)
        self.assertEqual("session_not_found", wrong_owner.json()["detail"])
        self.assertEqual(404, anonymous_bypass.status_code)

        evidence = await self.alice.post(
            f"/api/v0.5/sessions/{session_id}/evidence",
            json={"evidence_id": "E01"},
            headers=self.csrf_headers(self.alice),
        )
        self.assertEqual(200, evidence.status_code, evidence.text)

    async def test_missing_authentication_fails_closed(self) -> None:
        response = await self.alice.post(
            "/api/v0.5/sessions",
            json={"case_id": "ST-001"},
            headers={"X-CSRF-Token": "x" * 32},
        )
        self.assertEqual(401, response.status_code)
        self.assertEqual("authentication_required", response.json()["detail"])

    async def test_wrong_owner_is_hidden_across_every_training_command(self) -> None:
        await self.register(self.alice, "alice01")
        await self.register(self.bob, "bob0001")
        created = await self.alice.post(
            "/api/v0.5/sessions",
            json={"case_id": "ST-001"},
            headers=self.csrf_headers(self.alice),
        )
        session_id = created.json()["session_id"]
        headers = self.csrf_headers(self.bob)
        attempts = (
            ("post", f"/api/v0.5/sessions/{session_id}/evidence", {"evidence_id": "E01"}),
            ("post", f"/api/v0.5/sessions/{session_id}/hypotheses", {"hypothesis": "guess"}),
            ("post", f"/api/v0.5/sessions/{session_id}/tutor", {"message": "help"}),
            (
                "post",
                f"/api/v0.5/sessions/{session_id}/diagnosis",
                {
                    "contract_version": "0.4.0",
                    "diagnosis_type": "object_pose_mismatch",
                    "reasoning": "wrong owner",
                    "cited_evidence_ids": ["E01"],
                },
            ),
            ("get", f"/api/v0.5/sessions/{session_id}/report", None),
        )
        for method, url, payload in attempts:
            response = await self.bob.request(
                method, url, json=payload, headers=headers
            )
            self.assertEqual(404, response.status_code, (url, response.text))
            self.assertEqual("session_not_found", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
