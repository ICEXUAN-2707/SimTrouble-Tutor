"""Project authoritative Session state into the learner-safe v0.4 view."""

from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType

from core.case_engine import CaseSession
from core.models import ReleasedEvidence
from core.models.contracts import DiagnosticStage

from .learning_models import TutorAction
from .session_models import PublicSessionStage, SessionView


_PUBLIC_STAGE = MappingProxyType(
    {
        DiagnosticStage.START: PublicSessionStage.READY,
        DiagnosticStage.OBSERVE: PublicSessionStage.READY,
        DiagnosticStage.INVESTIGATE: PublicSessionStage.INVESTIGATING,
        DiagnosticStage.HYPOTHESIZE: PublicSessionStage.INVESTIGATING,
        DiagnosticStage.TEST: PublicSessionStage.INVESTIGATING,
        DiagnosticStage.UPDATE: PublicSessionStage.INVESTIGATING,
        DiagnosticStage.DIAGNOSE: PublicSessionStage.INVESTIGATING,
        DiagnosticStage.REFLECT: PublicSessionStage.SUBMITTED,
        DiagnosticStage.FINISH: PublicSessionStage.REVIEWED,
    }
)

_ALLOWED_ACTIONS = MappingProxyType(
    {
        DiagnosticStage.START: (TutorAction.OBSERVE_SCENE,),
        DiagnosticStage.OBSERVE: (
            TutorAction.OBSERVE_SCENE,
            TutorAction.INSPECT_EVIDENCE,
        ),
        DiagnosticStage.INVESTIGATE: (
            TutorAction.INSPECT_EVIDENCE,
            TutorAction.SUBMIT_HYPOTHESIS,
        ),
        DiagnosticStage.HYPOTHESIZE: (
            TutorAction.INSPECT_EVIDENCE,
            TutorAction.REVISE_HYPOTHESIS,
        ),
        DiagnosticStage.TEST: (
            TutorAction.INSPECT_EVIDENCE,
            TutorAction.REVISE_HYPOTHESIS,
        ),
        DiagnosticStage.UPDATE: (
            TutorAction.INSPECT_EVIDENCE,
            TutorAction.REVISE_HYPOTHESIS,
            TutorAction.SUBMIT_DIAGNOSIS,
        ),
        DiagnosticStage.DIAGNOSE: (TutorAction.SUBMIT_DIAGNOSIS,),
        DiagnosticStage.REFLECT: (TutorAction.REFLECT,),
        DiagnosticStage.FINISH: (),
    }
)


class SessionProjector:
    def project(self, aggregate: CaseSession) -> SessionView:
        session = aggregate.session
        authoritative_case = aggregate.authoritative_case
        released_ids = set(session.evidence_seen)
        released_evidence = tuple(
            ReleasedEvidence(id=item.id, type=item.type, content=deepcopy(item.content))
            for item in authoritative_case.evidence
            if item.id in released_ids
        )
        return SessionView(
            contract_version="0.4.0",
            session_id=session.session_id,
            case_public_state=aggregate.public_case_state(),
            public_stage=_PUBLIC_STAGE[session.current_stage],
            released_evidence=released_evidence,
            current_hypothesis=session.current_hypothesis,
            hypotheses=tuple(session.hypothesis_history),
            allowed_actions=_ALLOWED_ACTIONS[session.current_stage],
        )
