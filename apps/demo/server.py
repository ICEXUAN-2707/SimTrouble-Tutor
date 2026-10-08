"""Standard-library HTTP transport for the bounded Demo adapter."""

from __future__ import annotations

import json
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.errors import EvidenceNotFoundError

from .runtime import DemoRuntime


MAX_BODY_BYTES = 8192
MAX_TEXT_CHARS = 500
COOKIE_NAME = "simtrouble_demo"
HTML_PATH = Path(__file__).parent / "static" / "index.html"


class DemoHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], runtime: DemoRuntime) -> None:
        super().__init__(server_address, DemoRequestHandler)
        self.runtime = runtime
        self.html = HTML_PATH.read_bytes()


class DemoRequestHandler(BaseHTTPRequestHandler):
    server: DemoHTTPServer
    server_version = "SimTroubleDemo/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} {format % args}", flush=True)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, self.server.html, "text/html; charset=utf-8")
            return
        if path == "/healthz":
            self._json(
                200,
                {"status": "ok", "case": "ST-001", "mode": "demo-v0.1"},
            )
            return
        if path == "/api/state":
            token, state, fresh = self.server.runtime.state(self._cookie_token())
            self._json(200, state, token if fresh else None)
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        allowed = {
            "/api/reset",
            "/api/evidence",
            "/api/hypothesis",
            "/api/chat",
            "/api/diagnose",
        }
        if path not in allowed:
            self._json(404, {"error": "Not found"})
            return

        try:
            payload = self._read_json_object()
        except ValueError as exc:
            self._json(400 if str(exc) != "输入过长" else 413, {"error": str(exc)})
            return

        if path == "/api/reset":
            token, state = self.server.runtime.reset()
            self._json(200, state, token)
            return

        token, _, fresh = self.server.runtime.state(self._cookie_token())
        try:
            if path == "/api/evidence":
                evidence_id = self._required_text(payload, "id").upper()
                state = self.server.runtime.request_evidence(token, evidence_id)
            elif path == "/api/hypothesis":
                state = self.server.runtime.submit_hypothesis(
                    token, self._required_text(payload, "text")
                )
            elif path == "/api/chat":
                state = self.server.runtime.ask_tutor(
                    token, self._required_text(payload, "text")
                )
            else:
                state = self.server.runtime.diagnose(
                    token, self._required_text(payload, "text")
                )
        except (EvidenceNotFoundError, ValueError) as exc:
            self._json(400, {"error": str(exc)}, token if fresh else None)
            return
        self._json(200, state, token if fresh else None)

    def _cookie_token(self) -> str | None:
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            return None
        return jar[COOKIE_NAME].value if COOKIE_NAME in jar else None

    def _read_json_object(self) -> dict[str, Any]:
        raw_size = self.headers.get("Content-Length", "0")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise ValueError("Content-Length 无效") from exc
        if size < 0:
            raise ValueError("Content-Length 无效")
        if size > MAX_BODY_BYTES:
            raise ValueError("输入过长")
        try:
            value = json.loads(self.rfile.read(size) or b"{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("JSON 格式无效") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON 必须是对象")
        return value

    @staticmethod
    def _required_text(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            raise ValueError(f"{key} 必须是文本")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{key} 不能为空")
        if len(normalized) > MAX_TEXT_CHARS:
            raise ValueError(f"{key} 不能超过 {MAX_TEXT_CHARS} 个字符")
        return normalized

    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str,
        token: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if token is not None:
            self.send_header(
                "Set-Cookie",
                f"{COOKIE_NAME}={token}; HttpOnly; SameSite=Lax; Path=/",
            )
        self.end_headers()
        self.wfile.write(body)

    def _json(
        self,
        status: int,
        value: dict[str, Any],
        token: str | None = None,
    ) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", token)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    runtime: DemoRuntime | None = None,
) -> DemoHTTPServer:
    return DemoHTTPServer((host, port), DemoRuntime() if runtime is None else runtime)
