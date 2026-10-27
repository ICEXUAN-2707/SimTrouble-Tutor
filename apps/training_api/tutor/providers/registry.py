"""Resolve safe runtime settings into one Tutor provider."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

from ..deepseek import DeepSeekResponsesAdapter
from ..ports import TutorProvider
from ..settings import LLMConfigurationError, LLMProviderSettings
from .capabilities import PROVIDER_CAPABILITIES, ProviderCapabilities
from .openai_compat import OpenAICompatChatAdapter


@dataclass(frozen=True)
class ProviderBuildResult:
    provider: TutorProvider | None
    disabled_reason: str
    settings: LLMProviderSettings | None = None
    capabilities: ProviderCapabilities | None = None


class TutorProviderRegistry:
    def build(
        self,
        *,
        settings: LLMProviderSettings | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> ProviderBuildResult:
        try:
            resolved = settings or LLMProviderSettings.from_env(environ)
        except LLMConfigurationError as exc:
            return ProviderBuildResult(None, exc.code)
        except ValueError:
            return ProviderBuildResult(None, "llm_config_invalid")

        capabilities = PROVIDER_CAPABILITIES.get(resolved.provider)
        if capabilities is None:
            return ProviderBuildResult(None, "llm_provider_unknown", resolved)
        if capabilities.api_style != resolved.api_style:
            return ProviderBuildResult(
                None,
                "llm_config_invalid",
                resolved,
                capabilities,
            )
        if not capabilities.allows_host(urlparse(resolved.base_url).hostname):
            return ProviderBuildResult(
                None,
                "llm_endpoint_rejected",
                resolved,
                capabilities,
            )
        if not resolved.enabled:
            return ProviderBuildResult(
                None,
                "llm_disabled",
                resolved,
                capabilities,
            )
        if capabilities.requires_api_key and resolved.api_key is None:
            return ProviderBuildResult(
                None,
                "llm_credentials_missing",
                resolved,
                capabilities,
            )
        if resolved.provider == "deepseek":
            provider: TutorProvider = DeepSeekResponsesAdapter(resolved)
        else:
            provider = OpenAICompatChatAdapter(resolved)
        return ProviderBuildResult(provider, "", resolved, capabilities)
