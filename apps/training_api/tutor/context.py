"""Projection from SessionView to the frozen learner-safe TutorRequest."""

from __future__ import annotations

from ..learning_models import TutorMessage, TutorRequest
from ..session_models import SessionView


class TutorContextProjector:
    def project(
        self,
        session: SessionView,
        history: tuple[TutorMessage, ...],
        learner_message: str,
    ) -> TutorRequest:
        return TutorRequest(
            contract_version="0.4.0",
            session_id=session.session_id,
            case_public_state=session.case_public_state,
            released_evidence=session.released_evidence,
            messages=(
                *history,
                TutorMessage(role="learner", content=learner_message),
            ),
            hypotheses=session.hypotheses,
            current_hypothesis=session.current_hypothesis,
            allowed_actions=session.allowed_actions,
        )
