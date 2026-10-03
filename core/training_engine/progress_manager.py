"""Cross-session progress projection without scoring or recommendation logic."""

from __future__ import annotations

from collections.abc import Iterable

from core.errors import DuplicateIdentifierError
from core.models import (
    LearnerProfile,
    LearnerSession,
    ModuleProgress,
    SkillScores,
    TrainingModule,
)
from core.models.contracts import DiagnosticStage


class ProgressManager:
    def build_profile(
        self,
        *,
        user_id: str,
        modules: Iterable[TrainingModule],
        sessions: Iterable[LearnerSession],
        skill_scores: SkillScores | None = None,
        recommended_case_id: str | None = None,
    ) -> LearnerProfile:
        module_list = tuple(modules)
        module_ids = [module.module_id for module in module_list]
        if len(module_ids) != len(set(module_ids)):
            raise DuplicateIdentifierError("progress input contains duplicate module ids")
        user_sessions = tuple(session for session in sessions if session.user_id == user_id)
        finished_case_ids = {
            session.case_id
            for session in user_sessions
            if session.current_stage is DiagnosticStage.FINISH
        }

        known_case_ids = {case_id for module in module_list for case_id in module.case_ids}
        if recommended_case_id is not None and recommended_case_id not in known_case_ids:
            raise ValueError(
                f"recommended case is not present in the supplied modules: {recommended_case_id}"
            )

        progress = tuple(
            ModuleProgress(
                module_id=module.module_id,
                completed_case_ids=tuple(
                    case_id for case_id in module.case_ids if case_id in finished_case_ids
                ),
                total_case_count=len(module.case_ids),
            )
            for module in module_list
        )

        return LearnerProfile(
            user_id=user_id,
            module_progress=progress,
            skill_scores=skill_scores or SkillScores.zero(),
            recommended_case_id=recommended_case_id,
        )
