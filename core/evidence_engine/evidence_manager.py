"""Explicit Evidence release with internal metadata stripping."""

from __future__ import annotations

from copy import deepcopy

from core.case_engine import CaseSession
from core.errors import EvidenceNotFoundError
from core.models import ReleasedEvidence


class EvidenceManager:
    def request(self, case_session: CaseSession, evidence_id: str) -> ReleasedEvidence:
        authoritative_case = case_session.authoritative_case
        evidence = next(
            (
                item
                for item in authoritative_case.evidence
                if item.id == evidence_id
            ),
            None,
        )
        if evidence is None:
            raise EvidenceNotFoundError(
                f"evidence {evidence_id!r} is not present in case "
                f"{authoritative_case.case_id}"
            )

        case_session._record_evidence_seen(evidence.id)

        return ReleasedEvidence(
            id=evidence.id,
            type=evidence.type,
            content=deepcopy(evidence.content),
        )
