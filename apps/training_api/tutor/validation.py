"""Post-provider safety checks that preserve the deterministic policy."""

from __future__ import annotations

from ..learning_models import TutorRequest, TutorResponse
from .policy import TutorPolicyDecision


class UnsafeTutorResponseError(ValueError):
    """Raised when model output violates policy or learner-safe boundaries."""


_FORBIDDEN_MARKERS = (
    "ground_truth",
    "optimal_path",
    "scoring_rules",
    "information_value",
    "related_faults",
    "authoritative_case",
    "skill_scores",
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
    return response
