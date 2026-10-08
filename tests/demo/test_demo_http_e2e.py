from __future__ import annotations

import http.cookiejar
import json
import threading
import unittest
import urllib.request
from typing import Any

from apps.demo.server import create_server


HIDDEN_KEYS = {
    "fault",
    "ground_truth",
    "optimal_path",
    "scoring_rules",
    "initial_state",
    "information_value",
    "related_faults",
}


def nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(nested_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for nested in value:
            keys.update(nested_keys(nested))
        return keys
    return set()


class DemoHttpEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        self.cookies = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def get_json(self, path: str) -> tuple[dict[str, Any], Any]:
        response = self.client.open(self.base_url + path, timeout=5)
        with response:
            return json.load(response), response.headers

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with self.client.open(request, timeout=5) as response:
            return json.load(response)

    def test_st001_public_flow_uses_core_trace_and_resets_session(self) -> None:
        health, _ = self.get_json("/healthz")
        self.assertEqual(
            {"status": "ok", "case": "ST-001", "mode": "demo-v0.1"},
            health,
        )
        with self.client.open(self.base_url + "/", timeout=5) as response:
            page = response.read().decode("utf-8")
        self.assertIn("SimTrouble Tutor", page)
        self.assertIn("Demo-only", page)

        state, headers = self.get_json("/api/state")
        self.assertEqual("ST-001", state["case"]["case_id"])
        self.assertEqual("START", state["session"]["current_stage"])
        self.assertEqual(["SessionStarted"], [e["action_type"] for e in state["trace"]])
        self.assertTrue(HIDDEN_KEYS.isdisjoint(nested_keys(state)))
        cookie_header = headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("SameSite=Lax", cookie_header)
        first_token = next(iter(self.cookies)).value

        state = self.post_json("/api/evidence", {"id": "E02"})
        self.assertEqual(["E02"], state["session"]["evidence_seen"])
        self.assertEqual(["E02"], [item["id"] for item in state["released"]])
        self.assertEqual(
            ["SessionStarted", "EvidenceRequested", "EvidenceReleased", "ActionPerformed"],
            [event["action_type"] for event in state["trace"]],
        )

        state = self.post_json("/api/evidence", {"id": "E01"})
        state = self.post_json("/api/evidence", {"id": "E03"})
        self.assertEqual(
            ["E02", "E01", "E03"],
            [item["id"] for item in state["released"]],
        )

        hypothesis = "工件 X 方向位置偏移导致抓取失败"
        state = self.post_json("/api/hypothesis", {"text": hypothesis})
        self.assertEqual(hypothesis, state["session"]["current_hypothesis"])
        self.assertEqual("HypothesisAdded", state["trace"][-1]["action_type"])

        updated_hypothesis = "E01 与 E02 支持工件位置偏移假设"
        state = self.post_json("/api/hypothesis", {"text": updated_hypothesis})
        self.assertEqual(updated_hypothesis, state["session"]["current_hypothesis"])
        self.assertEqual("HypothesisUpdated", state["trace"][-1]["action_type"])

        state = self.post_json("/api/chat", {"text": "请解释 E02"})
        self.assertEqual(["user", "tutor"], [item["role"] for item in state["messages"]])
        self.assertEqual("ActionPerformed", state["trace"][-1]["action_type"])

        state = self.post_json(
            "/api/diagnose",
            {"text": "诊断为工件位置偏移，依据是 E02"},
        )
        self.assertTrue(state["diagnosis"]["correct"])
        self.assertEqual("ST-001 Demo-only", state["diagnosis"]["mode"])
        self.assertEqual("START", state["session"]["current_stage"])
        self.assertTrue(all(event["tutor_hint"] is None for event in state["trace"]))
        self.assertTrue(HIDDEN_KEYS.isdisjoint(nested_keys(state)))

        reset = self.post_json("/api/reset", {})
        self.assertNotEqual(first_token, next(iter(self.cookies)).value)
        self.assertEqual([], reset["released"])
        self.assertIsNone(reset["session"]["current_hypothesis"])
        self.assertEqual(["SessionStarted"], [e["action_type"] for e in reset["trace"]])

    def test_cookie_sessions_are_isolated_and_server_generated(self) -> None:
        first, _ = self.get_json("/api/state")
        self.post_json("/api/evidence", {"id": "E01"})

        other_cookies = http.cookiejar.CookieJar()
        other = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(other_cookies)
        )
        with other.open(self.base_url + "/api/state", timeout=5) as response:
            second = json.load(response)

        self.assertEqual([], first["released"])
        self.assertEqual([], second["released"])
        self.assertEqual(1, len(other_cookies))
        self.assertNotEqual(next(iter(self.cookies)).value, next(iter(other_cookies)).value)


if __name__ == "__main__":
    unittest.main()
