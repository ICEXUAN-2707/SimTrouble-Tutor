"""Validated Training Module loading without persistence or API concerns."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from core.errors import DuplicateIdentifierError, MissingReferenceError
from core.models import TrainingModule


class TrainingModuleLoader:
    def load(self, path: str | Path) -> TrainingModule:
        return TrainingModule.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def load_many(
        self,
        paths: Iterable[str | Path],
        *,
        known_case_ids: set[str] | None = None,
    ) -> dict[str, TrainingModule]:
        catalog: dict[str, TrainingModule] = {}
        for path in paths:
            module = self.load(path)
            if module.module_id in catalog:
                raise DuplicateIdentifierError(
                    f"duplicate training module id: {module.module_id}"
                )
            if known_case_ids is not None:
                missing = sorted(set(module.case_ids) - known_case_ids)
                if missing:
                    raise MissingReferenceError(
                        f"module {module.module_id} references missing cases: {missing}"
                    )
            catalog[module.module_id] = module
        return catalog

    def load_directory(
        self,
        directory: str | Path,
        *,
        known_case_ids: set[str] | None = None,
    ) -> dict[str, TrainingModule]:
        return self.load_many(
            sorted(Path(directory).glob("*.json")), known_case_ids=known_case_ids
        )
