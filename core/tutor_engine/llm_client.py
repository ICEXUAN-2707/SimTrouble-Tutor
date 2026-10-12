"""Optional online LLM port.

The port speaks the OpenAI-compatible Chat Completions HTTP API using only the
standard library, so ``requirements.txt`` stays at ``pydantic``. Any provider
exposing that shape (OpenAI, DeepSeek, Moonshot, DashScope compatible mode,
vLLM, Ollama ``/v1``, ...) can be used by changing ``base_url`` and ``model``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol

from core.tutor_engine.errors import LLMUnavailableError


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class LLMClient(Protocol):
    """Minimal port for the Tutor expression layer."""

    def complete(self, *, system: str, user: str) -> str:
        """Return raw model text for one Tutor turn."""


def http_transport(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise LLMUnavailableError(f"LLM request failed: {exc}") from exc


class OpenAICompatClient:
    """OpenAI-compatible Chat Completions client."""

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 20.0,
        temperature: float = 0.2,
        max_tokens: int = 500,
        transport: Transport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._transport = transport or http_transport

    def complete(self, *, system: str, user: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = self._transport(url, headers, payload, self.timeout)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailableError("unexpected LLM response shape") from exc

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "OpenAICompatClient | None":
        """Build a client from environment variables; ``None`` when unconfigured."""

        source = os.environ if env is None else env
        api_key = source.get("SIMTROUBLE_LLM_API_KEY", "").strip()
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            base_url=source.get("SIMTROUBLE_LLM_BASE_URL", "https://api.openai.com/v1").strip()
            or "https://api.openai.com/v1",
            model=source.get("SIMTROUBLE_LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            timeout=float(source.get("SIMTROUBLE_LLM_TIMEOUT", "20") or 20),
        )


class ScriptedLLMClient:
    """Deterministic client used by tests and offline smoke runs."""

    def __init__(self, replies: Iterable[str]) -> None:
        self._replies = list(replies)
        self.prompts: list[tuple[str, str]] = []

    def complete(self, *, system: str, user: str) -> str:
        self.prompts.append((system, user))
        if not self._replies:
            raise LLMUnavailableError("scripted replies exhausted")
        return self._replies.pop(0)
