"""Environment-only configuration for optional Tutor LLM providers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from urllib.parse import urlparse


class LLMConfigurationError(ValueError):
    """A configuration error with a public-safe fallback reason."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProviderPreset:
    provider_id: str
    base_url: str
    default_model: str
    api_style: str
    api_key_env: str


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "deepseek": ProviderPreset(
        "deepseek",
        "https://api.deepseek.com",
        "deepseek-flash",
        "responses",
        "DEEPSEEK_API_KEY",
    ),
    "qwen": ProviderPreset(
        "qwen",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen3.8-flash",
        "chat_completions",
        "DASHSCOPE_API_KEY",
    ),
    "kimi": ProviderPreset(
        "kimi",
        "https://api.moonshot.cn/v1",
        "kimi-k2.6",
        "chat_completions",
        "MOONSHOT_API_KEY",
    ),
    "siliconflow": ProviderPreset(
        "siliconflow",
        "https://api.siliconflow.cn/v1",
        "",
        "chat_completions",
        "SILICONFLOW_API_KEY",
    ),
}


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise LLMConfigurationError("llm_config_invalid")


def _first(source: Mapping[str, str], *names: str, default: str = "") -> str:
    for name in names:
        if not name:
            continue
        value = source.get(name)
        if value is not None and value.strip():
            return value.strip()
    return default


@dataclass(frozen=True)
class LLMProviderSettings:
    enabled: bool = False
    api_key: str | None = field(default=None, repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    timeout_seconds: float = 8.0
    max_retries: int = 1
    provider: str = "deepseek"
    api_style: str = "responses"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "LLMProviderSettings":
        source = os.environ if environ is None else environ
        provider = source.get("SIMTROUBLE_LLM_PROVIDER", "deepseek").strip().lower()
        preset = PROVIDER_PRESETS.get(provider)
        if preset is None:
            raise LLMConfigurationError("llm_provider_unknown")
        legacy = "DEEPSEEK_" if provider == "deepseek" else ""
        try:
            timeout_seconds = float(_first(
                source,
                "SIMTROUBLE_LLM_TIMEOUT_SECONDS",
                f"{legacy}TIMEOUT_SECONDS" if legacy else "",
                default="8",
            ))
            max_retries = int(_first(
                source,
                "SIMTROUBLE_LLM_MAX_RETRIES",
                f"{legacy}MAX_RETRIES" if legacy else "",
                default="1",
            ))
        except ValueError as exc:
            raise LLMConfigurationError("llm_config_invalid") from exc
        base_url = _first(
            source,
            "SIMTROUBLE_LLM_BASE_URL",
            f"{legacy}BASE_URL" if legacy else "",
            default=preset.base_url,
        ).rstrip("/")
        model = _first(
            source,
            "SIMTROUBLE_LLM_MODEL",
            f"{legacy}MODEL" if legacy else "",
            default=preset.default_model,
        )
        api_key = source.get(preset.api_key_env)
        if timeout_seconds <= 0 or not 0 <= max_retries <= 3:
            raise LLMConfigurationError("llm_config_invalid")
        parsed_url = urlparse(base_url)
        if (
            parsed_url.scheme not in {"https", "http"}
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise LLMConfigurationError("llm_config_invalid")
        if not model:
            raise LLMConfigurationError("llm_config_invalid")
        return cls(
            enabled=_parse_bool(source.get("SIMTROUBLE_LLM_ENABLED")),
            api_key=api_key.strip() if api_key and api_key.strip() else None,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            provider=provider,
            api_style=preset.api_style,
        )

    @property
    def configured(self) -> bool:
        return self.enabled and self.api_key is not None


# Compatibility for the existing DeepSeek adapter and callers.
DeepSeekSettings = LLMProviderSettings
