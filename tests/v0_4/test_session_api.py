from __future__ import annotations

import json
import unittest

from httpx import ASGITransport, AsyncClient

from apps.training_api.main import create_app
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.service import TutorService


class SessionApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        sessions = SessionService()
        self.app = create_app(
            session_service=sessions,
            tutor_service=TutorService(sessions),
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_http_session_flow(self) -> None:
        create_response = await self.client.post(
            "/api/v0.4/sessions",
            json={"case_id": "ST-001"},
        )
        self.assertEqual(201, create_response.status_code)
        created = create_response.json()
        session_id = created["session_id"]
        self.assertEqual("READY", created["public_stage"])

        tutor_response = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/tutor",
            json={"message": "What should I inspect first?"},
        )
        self.assertEqual(200, tutor_response.status_code)
        self.assertEqual("rule_fallback", tutor_response.json()["tutor_mode"])
        self.assertEqual(
            "inspect_evidence",
            tutor_response.json()["tutor"]["suggested_action"],
        )

        evidence_response = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/evidence",
            json={"evidence_id": "E01"},
        )
        self.assertEqual(200, evidence_response.status_code)
        self.assertEqual("E01", evidence_response.json()["evidence"]["id"])

        hypothesis_response = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/hypotheses",
            json={"hypothesis": "gripper did not hold the object"},
        )
        self.assertEqual(200, hypothesis_response.status_code)
        self.assertEqual(
            "gripper did not hold the object",
            hypothesis_response.json()["current_hypothesis"],
        )

        get_response = await self.client.get(f"/api/v0.4/sessions/{session_id}")
        self.assertEqual(200, get_response.status_code)
        self.assertEqual(session_id, get_response.json()["session_id"])

        payload = json.dumps(get_response.json())
        for forbidden in (
            "ground_truth",
            "optimal_path",
            "scoring_rules",
            "information_value",
            "related_faults",
            "skill_scores",
        ):
            self.assertNotIn(forbidden, payload)

    async def test_http_errors_are_stable_and_do_not_leak_internal_details(self) -> None:
        missing_case = await self.client.post(
            "/api/v0.4/sessions",
            json={"case_id": "ST-999"},
        )
        self.assertEqual(404, missing_case.status_code)
        self.assertEqual("case_not_found", missing_case.json()["detail"])

        missing_session = await self.client.get("/api/v0.4/sessions/not-found")
        self.assertEqual(404, missing_session.status_code)
        self.assertEqual("session_not_found", missing_session.json()["detail"])

        missing_tutor_session = await self.client.post(
            "/api/v0.4/sessions/not-found/tutor",
            json={"message": "Help"},
        )
        self.assertEqual(404, missing_tutor_session.status_code)
        self.assertEqual(
            "session_not_found", missing_tutor_session.json()["detail"]
        )

        created = (await self.client.post(
            "/api/v0.4/sessions",
            json={"case_id": "ST-001"},
        )).json()
        session_id = created["session_id"]
        premature = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/hypotheses",
            json={"hypothesis": "too early"},
        )
        self.assertEqual(409, premature.status_code)
        self.assertEqual("invalid_session_stage", premature.json()["detail"])

        unknown_evidence = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/evidence",
            json={"evidence_id": "E99"},
        )
        self.assertEqual(404, unknown_evidence.status_code)
        self.assertEqual("evidence_not_found", unknown_evidence.json()["detail"])

        blank_hypothesis = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/hypotheses",
            json={"hypothesis": "   "},
        )
        self.assertEqual(422, blank_hypothesis.status_code)

        blank_tutor_message = await self.client.post(
            f"/api/v0.4/sessions/{session_id}/tutor",
            json={"message": "   "},
        )
        self.assertEqual(422, blank_tutor_message.status_code)

    async def test_extra_fields_are_rejected(self) -> None:
        response = await self.client.post(
            "/api/v0.4/sessions",
            json={"case_id": "ST-001", "user_id": "caller-controlled"},
        )
        self.assertEqual(422, response.status_code)

    async def test_only_the_planned_v04_routes_are_exposed(self) -> None:
        paths = {
            route.path
            for route in self.app.routes
            if route.path.startswith("/api/v0.4")
        }
        self.assertEqual(
            {
                "/api/v0.4/cases/{case_id}/scene",
                "/api/v0.4/sessions",
                "/api/v0.4/sessions/{session_id}",
                "/api/v0.4/sessions/{session_id}/evidence",
                "/api/v0.4/sessions/{session_id}/hypotheses",
                "/api/v0.4/sessions/{session_id}/tutor",
            },
            paths,
        )


if __name__ == "__main__":
    unittest.main()
