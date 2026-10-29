"""Case-aware deterministic guard for learner-facing Tutor output."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
import re
import unicodedata

from core.case_engine import CaseLoader
from core.models import TrainingCase

from ..learning_models import TutorRequest, TutorResponse
from .validation import UnsafeTutorResponseError

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASE_DIRECTORY = ROOT / "data" / "cases"
DEFAULT_ANSWER_ALIASES: dict[str, tuple[str, ...]] = {
    "ST-001": ("工件位置不匹配", "工件位置偏移", "object pose mismatch"),
}


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"[\s_\-]+", "", text)


class TutorOutputGuard:
    def __init__(
        self,
        cases: Mapping[str, TrainingCase],
        aliases: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        self._cases = dict(cases)
        self._aliases = {
            case_id: tuple(values)
            for case_id, values in (aliases or DEFAULT_ANSWER_ALIASES).items()
        }

    @classmethod
    def from_default_cases(cls) -> "TutorOutputGuard":
        return cls(CaseLoader().load_directory(DEFAULT_CASE_DIRECTORY))

    def validate(self, request: TutorRequest, response: TutorResponse) -> TutorResponse:
        case_id = request.case_public_state.case_id
        case = self._cases.get(case_id)
        if case is None:
            raise UnsafeTutorResponseError("guard_case_unknown")
        visible = _normalize(json.dumps(request.model_dump(mode="json"), ensure_ascii=False))
        visible_numbers = self._visible_numbers(request)
        message = _normalize(response.message)

        answer_terms = [
            case.ground_truth.diagnosis,
            case.fault.type.value,
            *self._aliases.get(case_id, ()),
        ]
        if self._contains_private_term(message, visible, answer_terms):
            raise UnsafeTutorResponseError("hidden_answer_detected")
        if self._contains_private_term(message, visible, case.optimal_path):
            raise UnsafeTutorResponseError("private_path_detected")

        released_ids = {item.id for item in request.released_evidence}
        for evidence in case.evidence:
            if evidence.id in released_ids:
                continue
            strings, numbers = self._evidence_terms(evidence.content)
            if self._contains_private_term(message, visible, strings):
                raise UnsafeTutorResponseError("unreleased_evidence_detected")
            if any(
                self._number_is_hidden(value, message, visible_numbers)
                for value in numbers
            ):
                raise UnsafeTutorResponseError("unreleased_evidence_detected")
        return response

    @staticmethod
    def _contains_private_term(message: str, visible: str, terms: Iterable[object]) -> bool:
        for value in terms:
            term = _normalize(value)
            if len(term) < 3 or term in visible:
                continue
            if term in message:
                return True
        return False

    @staticmethod
    def _number_is_hidden(
        value: int | float,
        message: str,
        visible_numbers: frozenset[float],
    ) -> bool:
        numeric = float(value)
        if abs(numeric) < 10 or numeric in visible_numbers:
            return False
        term = format(numeric, "g")
        return re.search(rf"(?<!\d){re.escape(term)}(?!\d)", message) is not None

    @staticmethod
    def _visible_numbers(request: TutorRequest) -> frozenset[float]:
        values: set[float] = set()

        def collect(value: object) -> None:
            if isinstance(value, bool):
                return
            if isinstance(value, (int, float)):
                values.add(float(value))
            elif isinstance(value, Mapping):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, (list, tuple)):
                for nested in value:
                    collect(nested)

        for evidence in request.released_evidence:
            collect(evidence.model_dump(mode="json"))
        for item in request.messages:
            for match in re.findall(r"(?<!\d)-?\d+(?:\.\d+)?(?!\d)", item.content):
                values.add(float(match))
        return frozenset(values)

    @staticmethod
    def _evidence_terms(content: Mapping[str, object]) -> tuple[list[str], list[int | float]]:
        strings: list[str] = []
        numbers: list[int | float] = []
        for value in content.values():
            if isinstance(value, bool):
                continue
            if isinstance(value, str) and len(value.strip()) >= 4:
                strings.append(value)
            elif isinstance(value, (int, float)):
                numbers.append(value)
        return strings, numbers
