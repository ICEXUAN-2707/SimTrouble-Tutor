"""Explicit Evidence release with internal metadata stripping."""

from __future__ import annotations

from copy import deepcopy

from core.case_engine import CaseSession
from core.errors import EvidenceNotFoundError
from core.models import ReleasedEvidence


class EvidenceManager:
    def request(self, case_session: CaseSession, evidence_id: str) -> ReleasedEvidence:
        evidence = next(
            (
                item
                for item in case_session.authoritative_case.evidence
                if item.id == evidence_id
            ),
            None,
        )
        if evidence is None:
            raise EvidenceNotFoundError(
                f"evidence {evidence_id!r} is not present in case "
                f"{case_session.authoritative_case.case_id}"
            )

        if evidence.id not in case_session.session.evidence_seen:
            case_session.session.evidence_seen.append(evidence.id)

        return ReleasedEvidence(
            id=evidence.id,
            type=evidence.type,
            content=deepcopy(evidence.content),
        )
