from contextlib import closing
from pathlib import Path
import sqlite3
import unittest

from tests.v0_5 import test_training_records
from tools.sqlite_backup import create_backup, restore_backup, verify_backup


class BackupRecoveryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_training_records.TrainingRecordTests.asyncSetUp
    asyncTearDown = test_training_records.TrainingRecordTests.asyncTearDown
    new_app = test_training_records.TrainingRecordTests.new_app
    client = test_training_records.TrainingRecordTests.client
    register = test_training_records.TrainingRecordTests.register
    post = test_training_records.TrainingRecordTests.post
    ready = test_training_records.TrainingRecordTests.ready

    async def test_backup_restore_login_report_and_isolation(self):
        await self.register(self.alice, "recovery01")
        session_id = await self.ready(self.alice)
        url = f"/api/v0.5/sessions/{session_id}"
        response = await self.post(self.alice, f"{url}/diagnosis", test_training_records.DIAGNOSIS)
        self.assertEqual(202, response.status_code)
        expected = (await self.alice.get(f"{url}/report")).json()
        backup = self.path.parent / "backup"
        metadata = create_backup(self.path, backup, "c45dcb5-drill")
        self.assertEqual(1, metadata["counts"]["training_records"])
        self.assertEqual(metadata, verify_backup(backup))
        restored = self.path.parent / "restored.db"
        restore_backup(backup, restored)
        with closing(sqlite3.connect(restored)) as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0])
        self.path = Path(restored)
        fresh_app = self.new_app()
        learner = self.client(fresh_app)
        learner.cookies.update(self.alice.cookies)
        self.assertEqual(401, (await learner.get(f"{url}/report")).status_code)
        learner.cookies.clear()
        login = await learner.post("/api/v0.5/auth/login", json={
            "username": "recovery01", "password": test_training_records.PASSWORD,
        })
        self.assertEqual(200, login.status_code)
        self.assertEqual(expected, (await learner.get(f"{url}/report")).json())
        stranger = self.client(fresh_app)
        await self.register(stranger, "stranger01")
        self.assertEqual(404, (await stranger.get(f"{url}/report")).status_code)
