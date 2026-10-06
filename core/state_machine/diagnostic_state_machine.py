"""Topology-only Diagnostic State Machine frozen by Phase 3 DG-01/DG-02."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from core.errors import InvalidStateTransitionError
from core.models import LearnerSession
from core.models.contracts import DiagnosticStage


_LEGAL_SUCCESSOR: Mapping[DiagnosticStage, DiagnosticStage] = MappingProxyType(
    {
        DiagnosticStage.START: DiagnosticStage.OBSERVE,
        DiagnosticStage.OBSERVE: DiagnosticStage.INVESTIGATE,
        DiagnosticStage.INVESTIGATE: DiagnosticStage.HYPOTHESIZE,
        DiagnosticStage.HYPOTHESIZE: DiagnosticStage.TEST,
        DiagnosticStage.TEST: DiagnosticStage.UPDATE,
        DiagnosticStage.UPDATE: DiagnosticStage.DIAGNOSE,
        DiagnosticStage.DIAGNOSE: DiagnosticStage.REFLECT,
        DiagnosticStage.REFLECT: DiagnosticStage.FINISH,
    }
)


class DiagnosticStateMachine:
    """Apply only the single legal successor for the authoritative stage."""

    @staticmethod
    def transition(
        session: LearnerSession,
        target_stage: DiagnosticStage,
    ) -> None:
        current_stage = session.current_stage
        if _LEGAL_SUCCESSOR.get(current_stage) is not target_stage:
            raise InvalidStateTransitionError(
                f"illegal diagnostic transition: "
                f"{current_stage.value} -> {target_stage.value}"
            )

        session.current_stage = target_stage
