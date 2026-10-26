from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from apps.training_api.auth.repository import AuthenticationStore, UnsupportedSchemaError
from apps.training_api.main import create_app
from apps.training_api.session_repository import SessionRepository
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.service import TutorService


PASSWORD = "correct-horse-battery"
DIAGNOSIS = {
    "contract_version": "0.4.0",
    "diagnosis_type": "object_pose_mismatch",
    "reasoning": "公开位姿证据支持该诊断。",
    "cited_evidence_ids": ["E01", "E02"],
}


class TrainingRecordTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "auth.db"
        self.clients: list[AsyncClient] = []
        self.repository = SessionRepository()
        self.app = self.new_app(SessionService(repository=self.repository))
        self.alice = self.client(self.app)

    async def asyncTearDown(self) -> None:
        for client in self.clients:
            await client.aclose()

    def new_app(self, sessions: SessionService | None = None):
        sessions = sessions or SessionService()
        return create_app(
            authentication_store=AuthenticationStore(self.path),
            session_service=sessions,
            tutor_service=TutorService(sessions),
        )

    def client(self, app) -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        )
        self.clients.append(client)
        return client

    async def register(self, client: AsyncClient, username: str) -> None:
        response = await client.post(
            "/api/v0.5/auth/register", json={"username": username, "password": PASSWORD}
        )
        self.assertEqual(201, response.status_code, response.text)

    async def post(self, client: AsyncClient, path: str, payload: dict | None = None):
        return await client.post(
            path, json=payload,
            headers={"X-CSRF-Token": client.cookies.get("simtrouble_csrf", "")},
        )

    async def ready(self, client: AsyncClient, prefix: str = "/api/v0.5") -> str:
        response = await self.post(client, f"{prefix}/sessions", {"case_id": "ST-001"})
        self.assertEqual(201, response.status_code, response.text)
        session_id = response.json()["session_id"]
        for action, payload in (
            ("evidence", {"evidence_id": "E01"}),
            ("hypotheses", {"hypothesis": "夹爪可能未保持工件。"}),
            ("evidence", {"evidence_id": "E02"}),
            ("hypotheses", {"hypothesis": "工件位置与计划位姿不同。"}),
        ):
            response = await self.post(client, f"{prefix}/sessions/{session_id}/{action}", payload)
            self.assertEqual(200, response.status_code, response.text)
        return session_id

    def record_count(self) -> int:
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute("SELECT COUNT(*) FROM training_records").fetchone()[0]

    async def test_completed_record_survives_restart_and_relogin(self) -> None:
        await self.register(self.alice, "alice01")
        session_id = await self.ready(self.alice)
        url = f"/api/v0.5/sessions/{session_id}"
        submitted = await self.post(self.alice, f"{url}/diagnosis", DIAGNOSIS)
        self.assertEqual(202, submitted.status_code, submitted.text)
        before_session = (await self.alice.get(url)).json()
        before_report = (await self.alice.get(f"{url}/report")).json()
        self.assertEqual(1, self.record_count())
        self.assertEqual(91.75, before_report["overall"]["score"])
        self.assertEqual("not_assessed", before_report["dimension_results"]["safety"]["status"])

        self.assertEqual(204, (await self.post(self.alice, "/api/v0.5/auth/logout")).status_code)
        # A genuinely new application has no old SessionRepository or report cache.
        restarted = self.client(self.new_app())
        logged_in = await restarted.post(
            "/api/v0.5/auth/login", json={"username": "alice01", "password": PASSWORD}
        )
        self.assertEqual(200, logged_in.status_code, logged_in.text)
        session = await restarted.get(url)
        report = await restarted.get(f"{url}/report")
        self.assertEqual(200, session.status_code, session.text)
        self.assertEqual(200, report.status_code, report.text)
        self.assertEqual(before_session, session.json())
        self.assertEqual(before_report, report.json())
        self.assertEqual("REVIEWED", session.json()["public_stage"])
        self.assertEqual([], session.json()["allowed_actions"])
        repeated = await self.post(restarted, f"{url}/diagnosis", DIAGNOSIS)
        self.assertEqual(409, repeated.status_code, repeated.text)
        self.assertEqual("diagnosis_already_submitted", repeated.json()["detail"])
        self.assertEqual(1, self.record_count())
        self.assertEqual(before_report, (await restarted.get(f"{url}/report")).json())

    async def test_record_stays_hidden_from_other_users_and_anonymous_routes(self) -> None:
        await self.register(self.alice, "alice01")
        session_id = await self.ready(self.alice)
        url = f"/api/v0.5/sessions/{session_id}"
        self.assertEqual(202, (await self.post(self.alice, f"{url}/diagnosis", DIAGNOSIS)).status_code)
        restarted_app = self.new_app()
        bob = self.client(restarted_app)
        await self.register(bob, "bob0001")
        for target in (url, f"{url}/report"):
            response = await bob.get(target)
            self.assertEqual(404, response.status_code, response.text)
            self.assertEqual({"detail": "session_not_found"}, response.json())
        response = await self.post(bob, f"{url}/diagnosis", DIAGNOSIS)
        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual({"detail": "session_not_found"}, response.json())
        for suffix in ("", "/report"):
            response = await bob.get(f"/api/v0.4/sessions/{session_id}{suffix}")
            self.assertEqual(404, response.status_code, response.text)
        anonymous = self.client(restarted_app)
        self.assertEqual(401, (await anonymous.get(f"{url}/report")).status_code)

    async def test_failed_sql_write_rolls_back_completion_and_can_be_retried(self) -> None:
        await self.register(self.alice, "alice01")
        session_id = await self.ready(self.alice)
        url = f"/api/v0.5/sessions/{session_id}"
        before = self.repository.inspect(session_id, lambda aggregate: aggregate.session)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                "CREATE TRIGGER fail_record BEFORE INSERT ON training_records "
                "BEGIN SELECT RAISE(ABORT, 'test write failure'); END"
            )
        failed = await self.post(self.alice, f"{url}/diagnosis", DIAGNOSIS)
        self.assertEqual(500, failed.status_code)
        self.assertNotIn("test write failure", failed.text)
        after = self.repository.inspect(session_id, lambda aggregate: aggregate.session)
        self.assertEqual(before, after)
        self.assertEqual(0, self.record_count())
        self.assertEqual(409, (await self.alice.get(f"{url}/report")).status_code)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("DROP TRIGGER fail_record")
        retried = await self.post(self.alice, f"{url}/diagnosis", DIAGNOSIS)
        self.assertEqual(202, retried.status_code, retried.text)
        self.assertEqual(1, self.record_count())
        self.assertEqual(200, (await self.alice.get(f"{url}/report")).status_code)

    async def test_unfinished_and_anonymous_training_are_not_persisted(self) -> None:
        await self.register(self.alice, "alice01")
        unfinished = await self.ready(self.alice)
        anonymous = await self.ready(self.alice, "/api/v0.4")
        completed = await self.post(
            self.alice, f"/api/v0.4/sessions/{anonymous}/diagnosis", DIAGNOSIS
        )
        self.assertEqual(202, completed.status_code, completed.text)
        self.assertEqual(0, self.record_count())
        restarted = self.client(self.new_app())
        restarted.cookies.update(self.alice.cookies)
        self.assertEqual(404, (await restarted.get(f"/api/v0.5/sessions/{unfinished}")).status_code)
        self.assertEqual(404, (await restarted.get(f"/api/v0.4/sessions/{anonymous}/report")).status_code)

    async def test_v2_upgrade_preserves_accounts_tokens_and_login_failures(self) -> None:
        await self.register(self.alice, "alice01")
        store = AuthenticationStore(self.path)
        self.assertIsNone(store.authenticate("alice01", "wrong-password"))
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("DROP TABLE training_records")
            connection.execute("PRAGMA user_version = 2")
            before = {
                table: connection.execute(f"SELECT * FROM {table}").fetchall()
                for table in ("users", "auth_sessions", "login_failures")
            }
        store.initialize()
        store.initialize()
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(3, connection.execute("PRAGMA user_version").fetchone()[0])
            for table, rows in before.items():
                self.assertEqual(rows, connection.execute(f"SELECT * FROM {table}").fetchall())
        self.assertEqual(0, self.record_count())
        self.assertIsNotNone(store.resolve(self.alice.cookies.get("simtrouble_auth")))
        self.assertIsNotNone(store.authenticate("alice01", PASSWORD))

    async def test_corrupt_record_is_not_returned_as_a_valid_report(self) -> None:
        await self.register(self.alice, "alice01")
        session_id = await self.ready(self.alice)
        self.assertEqual(202, (await self.post(
            self.alice, f"/api/v0.5/sessions/{session_id}/diagnosis", DIAGNOSIS
        )).status_code)
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute("UPDATE training_records SET report_json = '{}' ")
        restarted = self.client(self.new_app())
        restarted.cookies.update(self.alice.cookies)
        response = await restarted.get(f"/api/v0.5/sessions/{session_id}/report")
        self.assertEqual(500, response.status_code)

    async def test_newer_database_version_is_not_overwritten(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA user_version = 4")
        with self.assertRaises(UnsupportedSchemaError):
            self.new_app()
