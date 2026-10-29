"""Deterministic teaching policy.  The LLM may phrase, but not decide."""

from __future__ import annotations

from dataclasses import dataclass

from ..learning_models import TutorAction, TutorIntent, TutorRequest


@dataclass(frozen=True)
class TutorPolicyDecision:
    rule_id: str
    intent: TutorIntent
    hint_level: int
    suggested_action: TutorAction | None
    instruction: str

    def as_prompt_data(self) -> dict[str, str | int | None]:
        return {
            "rule_id": self.rule_id,
            "intent": self.intent.value,
            "hint_level": self.hint_level,
            "suggested_action": (
                self.suggested_action.value if self.suggested_action else None
            ),
            "instruction": self.instruction,
        }


class TutorPolicy:
    """Choose the next pedagogical move from learner-visible state only."""

    def decide(self, request: TutorRequest) -> TutorPolicyDecision:
        allowed = set(request.allowed_actions)

        if TutorAction.REFLECT in allowed:
            return TutorPolicyDecision(
                rule_id="TUTOR_REFLECT_AFTER_SUBMISSION",
                intent=TutorIntent.REFLECT,
                hint_level=0,
                suggested_action=TutorAction.REFLECT,
                instruction="Ask the learner to reflect on the evidence and reasoning.",
            )

        if not request.released_evidence and TutorAction.INSPECT_EVIDENCE in allowed:
            return TutorPolicyDecision(
                rule_id="TUTOR_INSPECT_FIRST_EVIDENCE",
                intent=TutorIntent.QUESTION,
                hint_level=0,
                suggested_action=TutorAction.INSPECT_EVIDENCE,
                instruction=(
                    "Ask the learner to choose one available evidence item and explain "
                    "what uncertainty it could reduce. Do not select the answer for them."
                ),
            )

        if (
            request.current_hypothesis is None
            and TutorAction.SUBMIT_HYPOTHESIS in allowed
        ):
            return TutorPolicyDecision(
                rule_id="TUTOR_FORM_TESTABLE_HYPOTHESIS",
                intent=TutorIntent.QUESTION,
                hint_level=0,
                suggested_action=TutorAction.SUBMIT_HYPOTHESIS,
                instruction=(
                    "Ask for one testable hypothesis linked to the released evidence."
                ),
            )

        if (
            len(request.released_evidence) < 2
            and TutorAction.INSPECT_EVIDENCE in allowed
        ):
            return TutorPolicyDecision(
                rule_id="TUTOR_GATHER_DISCRIMINATING_EVIDENCE",
                intent=TutorIntent.HINT,
                hint_level=1,
                suggested_action=TutorAction.INSPECT_EVIDENCE,
                instruction=(
                    "Prompt the learner to gather another evidence item that can "
                    "distinguish between competing explanations."
                ),
            )

        if (
            request.current_hypothesis is not None
            and TutorAction.SUBMIT_DIAGNOSIS in allowed
        ):
            return TutorPolicyDecision(
                rule_id="TUTOR_PREPARE_DIAGNOSIS",
                intent=TutorIntent.REFLECT,
                hint_level=1,
                suggested_action=TutorAction.SUBMIT_DIAGNOSIS,
                instruction=(
                    "Ask the learner to state how at least two released evidence items "
                    "support or weaken the hypothesis before submitting a diagnosis."
                ),
            )

        if TutorAction.REVISE_HYPOTHESIS in allowed:
            return TutorPolicyDecision(
                rule_id="TUTOR_REVISE_WITH_EVIDENCE",
                intent=TutorIntent.QUESTION,
                hint_level=1,
                suggested_action=TutorAction.REVISE_HYPOTHESIS,
                instruction=(
                    "Ask the learner whether the latest released evidence supports, "
                    "weakens, or requires revising the current hypothesis."
                ),
            )

        if TutorAction.OBSERVE_SCENE in allowed:
            return TutorPolicyDecision(
                rule_id="TUTOR_OBSERVE_BEFORE_INFERENCE",
                intent=TutorIntent.QUESTION,
                hint_level=0,
                suggested_action=TutorAction.OBSERVE_SCENE,
                instruction="Ask the learner to separate observations from conclusions.",
            )

        return TutorPolicyDecision(
            rule_id="TUTOR_NO_STATE_MUTATION",
            intent=TutorIntent.EXPLAIN,
            hint_level=0,
            suggested_action=None,
            instruction=(
                "Explain that no Tutor action is available and the learner should "
                "continue through the application controls."
            ),
        )
