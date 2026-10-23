"""Declarative capability and endpoint policy for supported providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    api_style: str
    structured_output: str
    allowed_base_url_hosts: tuple[str, ...]
    requires_api_key: bool = True
    supports_usage: bool = True
    supports_reasoning_control: bool = False

    def allows_host(self, hostname: str | None) -> bool:
        if hostname is None:
            return False
        normalized = hostname.rstrip(".").casefold()
        return any(
            normalized == allowed or normalized.endswith(f".{allowed}")
            for allowed in self.allowed_base_url_hosts
        )


PROVIDER_CAPABILITIES: dict[str, ProviderCapabilities] = {
    "deepseek": ProviderCapabilities(
        api_style="responses",
        structured_output="json_schema",
        allowed_base_url_hosts=("api.deepseek.com",),
        supports_reasoning_control=True,
    ),
    "qwen": ProviderCapabilities(
        api_style="chat_completions",
        structured_output="json_schema",
        allowed_base_url_hosts=(
            "dashscope.aliyuncs.com",
            "dashscope-intl.aliyuncs.com",
            "dashscope-us.aliyuncs.com",
            "maas.aliyuncs.com",
        ),
    ),
    "kimi": ProviderCapabilities(
        api_style="chat_completions",
        structured_output="json_schema",
        allowed_base_url_hosts=("api.moonshot.cn",),
        supports_reasoning_control=True,
    ),
    "siliconflow": ProviderCapabilities(
        api_style="chat_completions",
        structured_output="json_schema",
        allowed_base_url_hosts=(
            "api.siliconflow.cn",
            "api-st.siliconflow.cn",
        ),
        supports_reasoning_control=True,
    ),
}
