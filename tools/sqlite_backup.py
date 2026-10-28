"""Create verified local SQLite snapshots and restore into a new file only."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time


TABLES = ("users", "auth_sessions", "login_failures", "training_records")
SCHEMA_VERSION = 3


def connect_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)


def inspect_database(path: Path) -> dict:
    with closing(connect_readonly(path)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("database integrity check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("database foreign key check failed")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise ValueError("unsupported database schema")
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLES
        }
    return {"schema_version": version, "counts": counts}


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot(source: Path, destination: Path) -> None:
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    deadline = time.monotonic() + 60

    def progress(status: int, remaining: int, total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError("snapshot exceeded 60 seconds")

    try:
        with closing(connect_readonly(source)) as origin:
            with closing(sqlite3.connect(destination)) as target:
                origin.backup(target, pages=256, progress=progress, sleep=0.1)
        with destination.open("r+b") as stream:
            os.fsync(stream.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def create_backup(source: Path, directory: Path, revision: str) -> dict:
    if not source.is_file():
        raise ValueError("source database must exist")
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    database = directory / "snapshot.sqlite3"
    snapshot(source, database)
    metadata = inspect_database(database)
    metadata.update({
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "revision": revision,
        "sha256": checksum(database),
        "size_bytes": database.stat().st_size,
    })
    manifest = directory / "manifest.json"
    descriptor = os.open(manifest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return metadata


def verify_backup(directory: Path) -> dict:
    database = directory / "snapshot.sqlite3"
    metadata = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if metadata.get("format_version") != 1:
        raise ValueError("unsupported backup format")
    if database.stat().st_size != metadata["size_bytes"]:
        raise ValueError("backup size mismatch")
    if checksum(database) != metadata["sha256"]:
        raise ValueError("backup checksum mismatch")
    actual = inspect_database(database)
    if any(actual[key] != metadata[key] for key in actual):
        raise ValueError("backup metadata mismatch")
    return metadata


def restore_backup(directory: Path, destination: Path) -> dict:
    verify_backup(directory)
    if any(Path(str(destination) + suffix).exists() for suffix in ("", "-wal", "-shm", "-journal")):
        raise FileExistsError("restore requires a new path without SQLite sidecars")
    snapshot(directory / "snapshot.sqlite3", destination)
    try:
        with closing(sqlite3.connect(destination)) as connection:
            with connection:
                connection.execute("DELETE FROM auth_sessions")
        return inspect_database(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--source", type=Path, required=True)
    backup.add_argument("--directory", type=Path, required=True)
    backup.add_argument("--revision", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--directory", type=Path, required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--directory", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            result = create_backup(args.source, args.directory, args.revision)
        elif args.command == "verify":
            result = verify_backup(args.directory)
        else:
            result = restore_backup(args.directory, args.destination)
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        parser.exit(1, f"{type(exc).__name__}: backup operation failed; no success recorded\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
