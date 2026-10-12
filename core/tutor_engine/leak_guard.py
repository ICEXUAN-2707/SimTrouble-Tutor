"""Leakage guard for Tutor output (ADR-014: external output is untrusted)."""

from __future__ import annotations

import re
from collections.abc import Iterable

from core.models import TrainingCase


class LeakGuard:
    """Rejects Tutor text that exposes hidden Case material."""

    def __init__(self, forbidden: Iterable[str] = ()) -> None:
        self._terms: dict[str, str] = {}
        for term in forbidden:
            normalized = self.normalize(term)
            if normalized:
                self._terms.setdefault(normalized, str(term))

    @staticmethod
    def normalize(value: str) -> str:
        return re.sub(r"[\s_\-]+", "", str(value)).lower()

    @classmethod
    def from_case(
        cls,
        case: TrainingCase,
        *,
        released_ids: Iterable[str] = (),
        include_ground_truth: bool = True,
    ) -> "LeakGuard":
        released = set(released_ids)
        terms: list[str] = []
        if include_ground_truth:
            terms.append(case.ground_truth.diagnosis)
        terms.extend(case.optimal_path)
        for evidence in case.evidence:
            if evidence.id in released:
                continue
            terms.extend(cls._evidence_terms(evidence.content))
        return cls(terms)

    @classmethod
    def _evidence_terms(cls, content: dict) -> list[str]:
        terms: list[str] = []
        for value in content.values():
            if isinstance(value, bool):
                continue
            if isinstance(value, str):
                if len(value.strip()) >= 3:
                    terms.append(value)
            elif isinstance(value, (int, float)):
                if abs(value) >= 10:
                    terms.append(str(value))
        return terms

    def scan(self, text: str) -> list[str]:
        """Return the hidden terms present in ``text`` (original spelling)."""

        normalized = self.normalize(text)
        return [
            original
            for normalized_term, original in self._terms.items()
            if normalized_term in normalized
        ]
