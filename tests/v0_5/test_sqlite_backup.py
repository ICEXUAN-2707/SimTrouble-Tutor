from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from apps.training_api.auth.repository import AuthenticationStore
from tools.sqlite_backup import create_backup, restore_backup, verify_backup


class SQLiteBackupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source.db"
        AuthenticationStore(self.source).initialize()
        self.backup = self.root / "backup"

    def test_wal_snapshot_and_restore(self):
        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                           ("user-id", "learner", "learner", "Learner", "test-verifier", 1))
            writer.commit()
            result = create_backup(self.source, self.backup, "test-revision")
            self.assertEqual(1, result["counts"]["users"])
            restored = restore_backup(self.backup, self.root / "restored.db")
            self.assertEqual(result["counts"], restored["counts"])
        self.assertEqual(result, verify_backup(self.backup))

    def test_reject_overwrite_and_sidecar(self):
        create_backup(self.source, self.backup, "test")
        with self.assertRaises(FileExistsError):
            create_backup(self.source, self.backup, "test")
        with self.assertRaises(FileExistsError):
            restore_backup(self.backup, self.source)
        destination = self.root / "restored.db"
        Path(str(destination) + "-wal").touch()
        with self.assertRaises(FileExistsError):
            restore_backup(self.backup, destination)

    def test_reject_corrupt_snapshot(self):
        create_backup(self.source, self.backup, "test")
        with (self.backup / "snapshot.sqlite3").open("ab") as stream:
            stream.write(b"corrupt")
        with self.assertRaises(ValueError):
            restore_backup(self.backup, self.root / "restored.db")
        self.assertFalse((self.root / "restored.db").exists())

    def test_reject_unknown_schema_and_missing_source(self):
        with self.assertRaises(ValueError):
            create_backup(self.root / "missing.db", self.backup, "test")
        with closing(sqlite3.connect(self.source)) as connection:
            connection.execute("PRAGMA user_version=99")
        with self.assertRaises(ValueError):
            create_backup(self.source, self.backup, "test")
        self.assertFalse((self.backup / "manifest.json").exists())

    def test_reject_metadata_tampering(self):
        create_backup(self.source, self.backup, "test")
        manifest = self.backup / "manifest.json"
        metadata = json.loads(manifest.read_text())
        metadata["counts"]["users"] = 999
        manifest.write_text(json.dumps(metadata))
        with self.assertRaises(ValueError):
            verify_backup(self.backup)
