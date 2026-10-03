"""Validated authoritative Case loading."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from core.errors import DuplicateIdentifierError
from core.models import TrainingCase


class CaseLoader:
    def load(self, path: str | Path) -> TrainingCase:
        return TrainingCase.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def load_many(self, paths: Iterable[str | Path]) -> dict[str, TrainingCase]:
        catalog: dict[str, TrainingCase] = {}
        for path in paths:
            case = self.load(path)
            if case.case_id in catalog:
                raise DuplicateIdentifierError(f"duplicate case id: {case.case_id}")
            catalog[case.case_id] = case
        return catalog

    def load_directory(self, directory: str | Path) -> dict[str, TrainingCase]:
        return self.load_many(sorted(Path(directory).glob("*.json")))
