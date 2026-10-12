"""Small, honest ST-001 demo built on the published Phase 2 core.

This is an independent presentation adapter. It does not implement the
planned Phase 3 state machine or skill scoring.

When ``SIMTROUBLE_LLM_API_KEY`` is configured, Tutor replies come from the
online LLM port in ``core.tutor_engine``; otherwise the deterministic
rule policy is used. Either way the Tutor only receives the public projection.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import datetime, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import LearnerAction, ReleasedEvidence, TrainingModule
from core.tutor_engine import LeakGuard, TutorService
from demo_app.llm_adapter import LLMAdapter

ROOT = Path(__file__).resolve().parents[1]
CASE = CaseLoader().load(ROOT / "data" / "cases" / "ST-001.json")
MODULE = TrainingModule.model_validate_json(
    (ROOT / "data" / "modules" / "MOD-EXCEPTION.json").read_text(encoding="utf-8")
)
# 模型设置与在线调用统一走独立适配器；TutorService 按请求用当前客户端重建，
# 配置变更即时生效，无需重启服务。
ADAPTER = LLMAdapter()
HTML = (Path(__file__).parent / "index.html").read_bytes()
SESSIONS: dict[str, dict] = {}
LOCK = threading.RLock()


def new_session() -> tuple[str, dict]:
    token = secrets.token_urlsafe(24)
    item = {"core": CaseSession(user_id="anonymous-demo", case=CASE),
            "released": {}, "messages": [], "events": [], "diagnosis": None,
            "tutor_source": None, "tutor_fallback": None}
    SESSIONS[token] = item
    return token, item


def event(item: dict, kind: str, detail: str) -> None:
    item["events"].append({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "kind": kind, "detail": detail})


def public_state(item: dict) -> dict:
    core = item["core"]
    return {
        "mode": "在线大模型引导演示原型" if ADAPTER.is_configured() else "规则引导演示原型｜非在线大模型",
        "llm_configured": ADAPTER.is_configured(),
        "case": core.public_case_state().model_dump(mode="json"),
        "released": list(item["released"].values()),
        "hypothesis": core.session.current_hypothesis,
        "messages": item["messages"],
        "events": item["events"],
        "diagnosis": item["diagnosis"],
        "tutor_source": item["tutor_source"],
        "tutor_fallback": item["tutor_fallback"],
    }


def tutor_reply(item: dict, message: str) -> str:
    released = [ReleasedEvidence.model_validate(value) for value in item["released"].values()]
    context = TutorService.build_context(
        module=MODULE, case_session=item["core"], released_evidence=released
    )
    guard = LeakGuard.from_case(CASE, released_ids=[item.id for item in released])
    # 配置了模型则优先在线大模型；未配置或调用失败时由 TutorService 降级到内置规则。
    tutor = TutorService(client=ADAPTER.get_client())
    reply = tutor.respond(
        context,
        message,
        finished=item["diagnosis"] is not None,
        leak_guard=guard,
    )
    item["tutor_source"] = reply.source
    item["tutor_fallback"] = reply.fallback_reason
    return reply.response.message


class Handler(BaseHTTPRequestHandler):
    server_version = "SimTroubleDemo/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def _session(self) -> tuple[str, dict, bool]:
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            pass
        token = jar["simtrouble_demo"].value if "simtrouble_demo" in jar else ""
        with LOCK:
            if token in SESSIONS:
                return token, SESSIONS[token], False
            token, item = new_session()
            return token, item, True

    def _send(self, status: int, body: bytes, content_type: str, token: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if token:
            self.send_header("Set-Cookie", f"simtrouble_demo={token}; HttpOnly; SameSite=Lax; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict, token: str | None = None) -> None:
        self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8", token)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, HTML, "text/html; charset=utf-8")
            return
        if path == "/healthz":
            self._json(200, {"status": "ok", "case": "ST-001"})
            return
        if path == "/api/state":
            token, item, fresh = self._session()
            self._json(200, public_state(item), token if fresh else None)
            return
        if path == "/api/model-settings":
            self._json(200, ADAPTER.get_settings())
            return
        self._json(404, {"error": "Not found"})

    def _read_json(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size > 8192:
            raise ValueError("输入过长")
        payload = json.loads(self.rfile.read(size) or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        return payload

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/model-settings":
            try:
                settings = ADAPTER.update_settings(self._read_json())
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, {"settings": settings, "configured": settings["configured"]})
            return
        if path == "/api/model-settings/test":
            try:
                payload = self._read_json()
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})
                return
            ok, message = ADAPTER.test_connection(payload or None)
            self._json(200, {"ok": ok, "message": message})
            return
        if path not in {"/api/reset", "/api/evidence", "/api/hypothesis", "/api/chat", "/api/diagnose"}:
            self._json(404, {"error": "Not found"})
            return
        size = int(self.headers.get("Content-Length", "0"))
        if size > 8192:
            self._json(413, {"error": "输入过长"})
            return
        try:
            payload = json.loads(self.rfile.read(size) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "JSON 格式无效"})
            return
        with LOCK:
            if path == "/api/reset":
                token, item = new_session()
                self._json(200, public_state(item), token)
                return
            token, item, fresh = self._session()
            core = item["core"]
            try:
                if item["diagnosis"] is not None:
                    raise ValueError("本轮已结束，请重新开始")
                if path == "/api/evidence":
                    evidence_id = str(payload.get("id", "")).upper()
                    released = EvidenceManager().request(core, evidence_id)
                    item["released"][evidence_id] = released.model_dump(mode="json")
                    core.record_action(LearnerAction(action_type="inspect", parameters={"evidence_id": evidence_id}))
                    event(item, "检查", evidence_id)
                elif path == "/api/hypothesis":
                    value = str(payload.get("text", "")).strip()[:500]
                    core.submit_hypothesis(value)
                    event(item, "假设", value)
                elif path == "/api/chat":
                    value = str(payload.get("text", "")).strip()[:500]
                    if not value:
                        raise ValueError("请输入问题")
                    reply = tutor_reply(item, value)
                    item["messages"].extend([{"role": "user", "text": value},
                                             {"role": "tutor", "text": reply}])
                    core.record_action(LearnerAction(action_type="ask_tutor", parameters={"text": value}))
                    event(item, "对话", value)
                elif path == "/api/diagnose":
                    value = str(payload.get("text", "")).strip()[:500]
                    if not value:
                        raise ValueError("请输入诊断结论")
                    normalized = value.lower().replace(" ", "")
                    correct = any(x in normalized for x in ("位置偏移", "位置不匹配", "位姿偏移", "object_pose"))
                    item["diagnosis"] = {
                        "submitted": value, "correct": correct,
                        "reference": "工件 X 方向位置相对预期偏移 70 mm，导致抓取位置不匹配。",
                        "evidence_used": list(item["released"]),
                        "note": "本结果仅为 ST-001 演示判定；五维能力评分尚未实现。",
                    }
                    core.record_action(LearnerAction(action_type="diagnose", parameters={"text": value}))
                    event(item, "诊断", value)
            except Exception as exc:
                self._json(400, {"error": str(exc)}, token if fresh else None)
                return
            self._json(200, public_state(item), token if fresh else None)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"SimTrouble demo: http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
