"""Environment-only configuration for the optional DeepSeek adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import os


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError("SIMTROUBLE_LLM_ENABLED must be a boolean value")


@dataclass(frozen=True)
class DeepSeekSettings:
    enabled: bool = False
    api_key: str | None = field(default=None, repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    timeout_seconds: float = 8.0
    max_retries: int = 1

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "DeepSeekSettings":
        source = os.environ if environ is None else environ
        timeout_seconds = float(source.get("DEEPSEEK_TIMEOUT_SECONDS", "8"))
        max_retries = int(source.get("DEEPSEEK_MAX_RETRIES", "1"))
        base_url = source.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        model = source.get("DEEPSEEK_MODEL", "deepseek-flash").strip()
        api_key = source.get("DEEPSEEK_API_KEY")

        if timeout_seconds <= 0:
            raise ValueError("DEEPSEEK_TIMEOUT_SECONDS must be positive")
        if not 0 <= max_retries <= 3:
            raise ValueError("DEEPSEEK_MAX_RETRIES must be between 0 and 3")
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("DEEPSEEK_BASE_URL must be an HTTP(S) URL")
        if not model:
            raise ValueError("DEEPSEEK_MODEL must not be empty")

        return cls(
            enabled=_parse_bool(source.get("SIMTROUBLE_LLM_ENABLED")),
            api_key=api_key.strip() if api_key and api_key.strip() else None,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    @property
    def configured(self) -> bool:
        return self.enabled and self.api_key is not None
