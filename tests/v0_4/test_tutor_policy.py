from __future__ import annotations

import unittest

from apps.training_api.learning_models import TutorAction, TutorIntent
from apps.training_api.tutor.context import TutorContextProjector
from apps.training_api.tutor.policy import TutorPolicy
from apps.training_api.session_service import SessionService


class TutorPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sessions = SessionService()
        self.projector = TutorContextProjector()
        self.policy = TutorPolicy()
        self.view = self.sessions.create("ST-001")

    def decide(self):
        request = self.projector.project(self.view, (), "What should I do next?")
        return self.policy.decide(request)

    def test_policy_advances_without_revealing_the_answer(self) -> None:
        decision = self.decide()
        self.assertEqual(TutorIntent.QUESTION, decision.intent)
        self.assertEqual(TutorAction.INSPECT_EVIDENCE, decision.suggested_action)
        self.assertEqual(0, decision.hint_level)

        self.view = self.sessions.request_evidence(
            self.view.session_id, "E01"
        ).session
        decision = self.decide()
        self.assertEqual(TutorAction.SUBMIT_HYPOTHESIS, decision.suggested_action)

        self.view = self.sessions.submit_hypothesis(
            self.view.session_id, "The grasp did not hold the object."
        )
        decision = self.decide()
        self.assertEqual(TutorAction.INSPECT_EVIDENCE, decision.suggested_action)
        self.assertEqual(1, decision.hint_level)

        self.view = self.sessions.request_evidence(
            self.view.session_id, "E02"
        ).session
        decision = self.decide()
        self.assertEqual(TutorAction.REVISE_HYPOTHESIS, decision.suggested_action)

        self.view = self.sessions.submit_hypothesis(
            self.view.session_id, "The object position may be offset."
        )
        decision = self.decide()
        self.assertEqual(TutorAction.SUBMIT_DIAGNOSIS, decision.suggested_action)
        self.assertEqual(TutorIntent.REFLECT, decision.intent)


if __name__ == "__main__":
    unittest.main()
