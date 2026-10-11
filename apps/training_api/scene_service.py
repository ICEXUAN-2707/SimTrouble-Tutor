"""Load public-safe CAD scene configurations from the repository data tree."""

from __future__ import annotations

from pathlib import Path

from .models import SceneConfiguration


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENE_DIRECTORY = ROOT / "data" / "scenes"


class SceneNotFoundError(LookupError):
    """Raised when no public scene configuration exists for a Case."""


class SceneRepository:
    def __init__(self, directory: Path = DEFAULT_SCENE_DIRECTORY) -> None:
        self._directory = directory

    def load(self, case_id: str) -> SceneConfiguration:
        if not case_id.startswith("ST-") or not case_id[3:].isdigit():
            raise SceneNotFoundError(case_id)

        path = self._directory / f"{case_id}.json"
        if not path.is_file():
            raise SceneNotFoundError(case_id)

        return SceneConfiguration.model_validate_json(path.read_text(encoding="utf-8"))
