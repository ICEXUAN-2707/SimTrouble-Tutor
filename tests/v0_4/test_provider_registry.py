from __future__ import annotations

import unittest

from apps.training_api.tutor.deepseek import DeepSeekResponsesAdapter
from apps.training_api.tutor.providers.openai_compat import OpenAICompatChatAdapter
from apps.training_api.tutor.providers.registry import TutorProviderRegistry
from apps.training_api.tutor.settings import LLMProviderSettings


class ProviderSettingsTests(unittest.TestCase):
    def test_qwen_preset_accepts_generic_overrides_and_hides_key(self) -> None:
        settings = LLMProviderSettings.from_env({
            "SIMTROUBLE_LLM_ENABLED": "true",
            "SIMTROUBLE_LLM_PROVIDER": "qwen",
            "SIMTROUBLE_LLM_MODEL": "qwen-plus",
            "SIMTROUBLE_LLM_TIMEOUT_SECONDS": "12.5",
            "SIMTROUBLE_LLM_MAX_RETRIES": "2",
            "DASHSCOPE_API_KEY": "secret-qwen-key",
        })

        self.assertTrue(settings.configured)
        self.assertEqual("qwen", settings.provider)
        self.assertEqual("qwen-plus", settings.model)
        self.assertEqual("chat_completions", settings.api_style)
        self.assertEqual(
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            settings.base_url,
        )
        self.assertEqual(12.5, settings.timeout_seconds)
        self.assertEqual(2, settings.max_retries)
        self.assertNotIn("secret-qwen-key", repr(settings))

    def test_legacy_deepseek_variables_remain_supported(self) -> None:
        settings = LLMProviderSettings.from_env({
            "SIMTROUBLE_LLM_ENABLED": "true",
            "DEEPSEEK_API_KEY": "legacy-key",
            "DEEPSEEK_MODEL": "deepseek-chat",
            "DEEPSEEK_BASE_URL": "https://legacy.deepseek.test/v1/",
            "DEEPSEEK_TIMEOUT_SECONDS": "3",
            "DEEPSEEK_MAX_RETRIES": "0",
        })

        self.assertEqual("deepseek", settings.provider)
        self.assertEqual("deepseek-chat", settings.model)
        self.assertEqual("https://legacy.deepseek.test/v1", settings.base_url)
        self.assertEqual(3, settings.timeout_seconds)
        self.assertEqual(0, settings.max_retries)


class ProviderRegistryTests(unittest.TestCase):
    def test_disabled_and_missing_credentials_return_safe_reasons(self) -> None:
        registry = TutorProviderRegistry()

        disabled = registry.build(environ={})
        missing = registry.build(environ={
            "SIMTROUBLE_LLM_ENABLED": "true",
            "SIMTROUBLE_LLM_PROVIDER": "kimi",
        })

        self.assertIsNone(disabled.provider)
        self.assertEqual("llm_disabled", disabled.disabled_reason)
        self.assertIsNone(missing.provider)
        self.assertEqual("llm_credentials_missing", missing.disabled_reason)

    def test_invalid_configuration_is_fail_closed_without_startup_error(self) -> None:
        result = TutorProviderRegistry().build(environ={
            "SIMTROUBLE_LLM_ENABLED": "true",
            "SIMTROUBLE_LLM_TIMEOUT_SECONDS": "not-a-number",
        })

        self.assertIsNone(result.provider)
        self.assertEqual("llm_config_invalid", result.disabled_reason)
        self.assertIsNone(result.settings)

    def test_unknown_provider_and_untrusted_endpoint_have_distinct_reasons(self) -> None:
        registry = TutorProviderRegistry()
        unknown = registry.build(environ={
            "SIMTROUBLE_LLM_ENABLED": "true",
            "SIMTROUBLE_LLM_PROVIDER": "unknown-provider",
        })
        rejected = registry.build(settings=LLMProviderSettings(
            enabled=True,
            api_key="test-key",
            base_url="https://attacker.invalid/v1",
            model="qwen-plus",
            provider="qwen",
            api_style="chat_completions",
        ))

        self.assertEqual("llm_provider_unknown", unknown.disabled_reason)
        self.assertEqual("llm_endpoint_rejected", rejected.disabled_reason)
        self.assertIsNone(unknown.provider)
        self.assertIsNone(rejected.provider)

    def test_registry_resolves_deepseek_and_domestic_chat_adapters(self) -> None:
        registry = TutorProviderRegistry()
        cases = (
            ("deepseek", "DEEPSEEK_API_KEY", None, DeepSeekResponsesAdapter),
            ("qwen", "DASHSCOPE_API_KEY", None, OpenAICompatChatAdapter),
            ("kimi", "MOONSHOT_API_KEY", None, OpenAICompatChatAdapter),
            (
                "siliconflow",
                "SILICONFLOW_API_KEY",
                "Qwen/Qwen3-8B",
                OpenAICompatChatAdapter,
            ),
        )
        for provider, key_name, model, expected_type in cases:
            with self.subTest(provider=provider):
                environ = {
                    "SIMTROUBLE_LLM_ENABLED": "true",
                    "SIMTROUBLE_LLM_PROVIDER": provider,
                    key_name: "test-key",
                }
                if model is not None:
                    environ["SIMTROUBLE_LLM_MODEL"] = model
                result = registry.build(environ=environ)
                self.assertIsInstance(result.provider, expected_type)
                self.assertEqual("", result.disabled_reason)
                self.assertEqual(provider, result.settings.provider)
                self.assertEqual(
                    result.settings.api_style,
                    result.capabilities.api_style,
                )


if __name__ == "__main__":
    unittest.main()
