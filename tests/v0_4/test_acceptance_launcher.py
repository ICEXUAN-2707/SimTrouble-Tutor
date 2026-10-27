from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools import start_product_v04_acceptance as launcher


class AcceptanceLauncherTests(unittest.TestCase):
    def test_local_config_reads_only_supported_name_value_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".env.local"
            config.write_text(
                "# local-only\nSIMTROUBLE_LLM_ENABLED=true\nDEEPSEEK_API_KEY='secret-value'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                launcher.load_local_config(config),
                {
                    "SIMTROUBLE_LLM_ENABLED": "true",
                    "DEEPSEEK_API_KEY": "secret-value",
                },
            )

    def test_local_config_rejects_unknown_and_duplicate_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".env.local"
            for content in (
                "SIMTROUBLE_LLM_ENABLED=true\nOTHER_SECRET=value\n",
                "SIMTROUBLE_LLM_ENABLED=true\nSIMTROUBLE_LLM_ENABLED=false\n",
                "export DEEPSEEK_API_KEY=value\n",
            ):
                config.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(launcher.LauncherError):
                    launcher.load_local_config(config)

    def test_provider_settings_are_removed_from_frontend_environment(self) -> None:
        backend, frontend = launcher.build_child_environments(
            {
                "PATH": "path-value",
                "DEEPSEEK_API_KEY": "process-secret",
                "SIMTROUBLE_LLM_ENABLED": "false",
            },
            {
                "DEEPSEEK_API_KEY": "local-secret",
                "SIMTROUBLE_LLM_ENABLED": "true",
            },
        )
        self.assertEqual(backend["DEEPSEEK_API_KEY"], "local-secret")
        self.assertEqual(backend["SIMTROUBLE_LLM_ENABLED"], "true")
        self.assertEqual(frontend, {"PATH": "path-value"})

    def test_log_redaction_masks_exact_secrets_and_common_secret_fields(self) -> None:
        line = 'provider error DEEPSEEK_API_KEY=abc123 Authorization: Bearer qwerty'
        result = launcher.redact_log_line(line, ("abc123",))
        self.assertNotIn("abc123", result)
        self.assertNotIn("qwerty", result)
        self.assertIn("[REDACTED]", result)

    def test_console_log_line_can_be_rendered_in_legacy_windows_encoding(self) -> None:
        line = "[Preview] ➜ http://127.0.0.1:5174/\n"
        safe_line = launcher.safe_console_text(line, "gbk")
        self.assertIn("127.0.0.1:5174", safe_line)

    def test_web_readiness_requires_built_page_and_proxied_api_health(self) -> None:
        responses = iter(
            (
                b'<html><div id="app"></div></html>',
                b'{"status":"ok","version":"0.5.0"}',
            )
        )
        original = launcher._read_local
        try:
            launcher._read_local = lambda _url: next(responses)  # type: ignore[assignment]
            self.assertTrue(launcher.web_is_ready())
        finally:
            launcher._read_local = original

    def test_readiness_rejects_a_stale_v04_service(self) -> None:
        original = launcher._read_local
        try:
            launcher._read_local = lambda _url: b'{"status":"ok","version":"0.4.0"}'
            self.assertFalse(launcher.api_is_ready())
        finally:
            launcher._read_local = original


if __name__ == "__main__":
    unittest.main()
