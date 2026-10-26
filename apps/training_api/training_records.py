"""One SQLite row per completed, user-owned training record."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .learning_models import TrainingReportV04
from .session_models import PublicSessionStage, SessionView


@dataclass(frozen=True)
class CompletedTrainingRecord:
    session: SessionView
    report: TrainingReportV04


class TrainingRecordStore:
    """Use the database initialized by AuthenticationStore, without a second schema manager."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def save_completed(
        self, user_id: str, session: SessionView, report: TrainingReportV04
    ) -> None:
        if (
            not user_id
            or user_id.startswith("anonymous:")
            or session.public_stage is not PublicSessionStage.REVIEWED
            or session.session_id != report.session_id
            or session.case_public_state.case_id != report.case_id
        ):
            raise ValueError("only a matching completed user-owned record can be saved")
        with closing(sqlite3.connect(self.database_path, timeout=10)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                connection.execute(
                    "INSERT INTO training_records "
                    "(session_id, user_id, case_id, completed_at, session_json, report_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session.session_id, user_id, report.case_id, int(time.time()),
                        session.model_dump_json(), report.model_dump_json(),
                    ),
                )

    def get_completed(
        self, user_id: str, session_id: str
    ) -> CompletedTrainingRecord | None:
        with closing(sqlite3.connect(self.database_path, timeout=10)) as connection:
            row = connection.execute(
                "SELECT session_json, report_json FROM training_records "
                "WHERE session_id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()
        if row is None:
            return None
        return CompletedTrainingRecord(
            session=SessionView.model_validate_json(row[0]),
            report=TrainingReportV04.model_validate_json(row[1]),
        )
