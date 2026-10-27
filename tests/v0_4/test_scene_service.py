from __future__ import annotations

import json
import unittest

from apps.training_api.main import create_app
from apps.training_api.scene_service import SceneNotFoundError, SceneRepository


class SceneRepositoryTests(unittest.TestCase):
    def test_st001_scene_is_public_safe_and_animation_driven(self) -> None:
        scene = SceneRepository().load("ST-001")

        self.assertEqual("ST-001", scene.case_id)
        self.assertEqual("READY", scene.timeline[0].status)
        self.assertEqual("FAILURE_OBSERVED", scene.timeline[-1].status)
        self.assertFalse(scene.timeline[-1].object_attached)

        payload = json.dumps(scene.model_dump(mode="json"), ensure_ascii=False)
        for forbidden in ("ground_truth", "optimal_path", "scoring_rules", "70 mm"):
            self.assertNotIn(forbidden, payload)

    def test_unknown_or_malformed_scene_is_rejected(self) -> None:
        repository = SceneRepository()
        for case_id in ("ST-999", "../ST-001", "ST-ABC"):
            with self.subTest(case_id=case_id):
                with self.assertRaises(SceneNotFoundError):
                    repository.load(case_id)

    def test_fastapi_application_exposes_named_routes(self) -> None:
        paths = {route.path for route in create_app().routes}
        self.assertIn("/healthz", paths)
        self.assertIn("/api/v0.4/cases/{case_id}/scene", paths)


if __name__ == "__main__":
    unittest.main()
