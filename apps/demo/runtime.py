"""In-memory orchestration and public read model for the ST-001 Demo."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import LearnerAction, ReleasedEvidence

from .rule_tutor import reply_to
from .st001_judge import judge_diagnosis


ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"


@dataclass
class DemoSession:
    core: CaseSession
    released: dict[str, ReleasedEvidence] = field(default_factory=dict)
    messages: list[dict[str, str]] = field(default_factory=list)
    diagnosis: dict[str, Any] | None = None


class DemoRuntime:
    """Thread-safe process-local sessions over the official Phase 3 Core."""

    def __init__(self) -> None:
        self._case = CaseLoader().load(CASE_PATH)
        self._evidence = EvidenceManager()
        self._sessions: dict[str, DemoSession] = {}
        self._lock = threading.RLock()

    def create_session(self) -> tuple[str, DemoSession]:
        with self._lock:
            token = secrets.token_urlsafe(24)
            item = DemoSession(
                core=CaseSession(user_id="anonymous-demo", case=self._case)
            )
            self._sessions[token] = item
            return token, item

    def get_or_create(self, token: str | None) -> tuple[str, DemoSession, bool]:
        with self._lock:
            if token is not None and token in self._sessions:
                return token, self._sessions[token], False
            new_token, item = self.create_session()
            return new_token, item, True

    def reset(self) -> tuple[str, dict[str, Any]]:
        with self._lock:
            token, item = self.create_session()
            return token, self._public_state(item)

    def state(self, token: str | None) -> tuple[str, dict[str, Any], bool]:
        with self._lock:
            actual_token, item, fresh = self.get_or_create(token)
            return actual_token, self._public_state(item), fresh

    def request_evidence(self, token: str, evidence_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._require_active(token)
            released = self._evidence.request(item.core, evidence_id)
            item.released[released.id] = released
            item.core.record_action(
                LearnerAction(
                    action_type="inspect",
                    parameters={"evidence_id": released.id},
                )
            )
            return self._public_state(item)

    def submit_hypothesis(self, token: str, text: str) -> dict[str, Any]:
        with self._lock:
            item = self._require_active(token)
            item.core.submit_hypothesis(text)
            return self._public_state(item)

    def ask_tutor(self, token: str, text: str) -> dict[str, Any]:
        with self._lock:
            item = self._require_active(token)
            answer = reply_to(
                text,
                released_evidence_ids=item.released,
                current_hypothesis=item.core.session.current_hypothesis,
            )
            item.core.record_action(
                LearnerAction(action_type="ask_tutor", parameters={"text": text})
            )
            item.messages.extend(
                ({"role": "user", "text": text}, {"role": "tutor", "text": answer})
            )
            return self._public_state(item)

    def diagnose(self, token: str, text: str) -> dict[str, Any]:
        with self._lock:
            item = self._require_active(token)
            result = judge_diagnosis(text, released_evidence_ids=item.released)
            item.core.record_action(
                LearnerAction(action_type="diagnose", parameters={"text": text})
            )
            item.diagnosis = result
            return self._public_state(item)

    def _require_active(self, token: str) -> DemoSession:
        try:
            item = self._sessions[token]
        except KeyError as exc:
            raise ValueError("演示会话不存在，请刷新页面") from exc
        if item.diagnosis is not None:
            raise ValueError("本轮已提交诊断，请重新开始")
        return item

    @staticmethod
    def _public_state(item: DemoSession) -> dict[str, Any]:
        snapshot = item.core.session
        return {
            "mode": "Demo v0.1｜规则引导｜ST-001 only",
            "case": item.core.public_case_state().model_dump(mode="json"),
            "released": [value.model_dump(mode="json") for value in item.released.values()],
            "session": {
                "case_id": snapshot.case_id,
                "current_stage": snapshot.current_stage.value,
                "evidence_seen": list(snapshot.evidence_seen),
                "current_hypothesis": snapshot.current_hypothesis,
                "hypothesis_history": list(snapshot.hypothesis_history),
            },
            "messages": [dict(message) for message in item.messages],
            "trace": [event.model_dump(mode="json") for event in snapshot.trace],
            "diagnosis": None if item.diagnosis is None else dict(item.diagnosis),
        }
