"""Post-provider safety checks that preserve the deterministic policy."""

from __future__ import annotations

from ..learning_models import TutorAction, TutorRequest, TutorResponse
from .policy import TutorPolicyDecision


class UnsafeTutorResponseError(ValueError):
    """Raised when model output violates policy or learner-safe boundaries."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


_FORBIDDEN_MARKERS = (
    "ground_truth",
    "optimal_path",
    "scoring_rules",
    "information_value",
    "related_faults",
    "authoritative_case",
    "skill_scores",
)

_DIRECT_ANSWER_MARKERS = (
    "object_pose_mismatch",
    "object pose mismatch",
    "grasp_failure",
    "grasp failure",
    "obstacle_collision_risk",
    "obstacle collision risk",
    "placement_target_conflict",
    "placement target conflict",
    "the answer is",
    "correct diagnosis is",
    "the fault is",
    "root cause is",
    "答案是",
    "正确诊断是",
    "故障是",
    "根因是",
)


def validate_tutor_response(
    request: TutorRequest,
    decision: TutorPolicyDecision,
    response: TutorResponse,
) -> TutorResponse:
    if response.contract_version != "0.4.0":
        raise UnsafeTutorResponseError("contract_version_mismatch")
    if response.intent is not decision.intent:
        raise UnsafeTutorResponseError("policy_intent_mismatch")
    if response.hint_level != decision.hint_level:
        raise UnsafeTutorResponseError("policy_hint_level_mismatch")
    if response.suggested_action is not decision.suggested_action:
        raise UnsafeTutorResponseError("policy_action_mismatch")
    if (
        response.suggested_action is not None
        and response.suggested_action not in request.allowed_actions
    ):
        raise UnsafeTutorResponseError("suggested_action_not_allowed")

    normalized_message = response.message.casefold()
    if any(marker in normalized_message for marker in _FORBIDDEN_MARKERS):
        raise UnsafeTutorResponseError("private_field_marker_detected")
    before_review = TutorAction.REFLECT not in request.allowed_actions
    if before_review and any(
        marker in normalized_message for marker in _DIRECT_ANSWER_MARKERS
    ):
        raise UnsafeTutorResponseError("direct_answer_marker_detected")
    return response
