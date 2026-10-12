"""独立的在线大模型（LLM）适配器 —— 演示层与模型调用之间的解耦边界。

职责边界：
- 集中管理模型设置（提供商 / 接口地址 / API Key / 模型名 / 核心参数）的
  运行时状态与本地持久化（``demo_app/llm_settings.json``，可用环境变量
  ``SIMTROUBLE_LLM_SETTINGS`` 覆盖路径）；
- 按“仅支持 OpenAI 兼容协议 API”的约定装配客户端；真正的网络调用复用
  ``core.tutor_engine.llm_client.OpenAICompatClient``，本模块不实现任何传输细节；
- 对上层（``server.py`` / ``TutorService``）只暴露 :class:`LLMClient` 端口
  （``complete(system=..., user=...)``）。未配置时 ``get_client()`` 返回 ``None``，
  调用失败抛出 ``LLMUnavailableError``，由 ``TutorService`` 既有逻辑降级到内置规则。

首次启动且尚无本地设置文件时，会尝试用 ``SIMTROUBLE_LLM_*`` 环境变量播种，
以保持与此前基于环境变量的用法兼容。
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from core.tutor_engine.errors import LLMUnavailableError
from core.tutor_engine.llm_client import OpenAICompatClient

DEFAULT_SETTINGS_FILE = Path(__file__).resolve().parent / "llm_settings.json"

# 提供商预设：与“添加模型”弹窗中的提供商下拉框一一对应。
# 全部为 OpenAI 兼容协议，仅预填接口地址与常用模型名，可自由修改。
PROVIDERS: dict[str, dict[str, str]] = {
    "custom": {"label": "自定义 / Custom", "base_url": "", "model": ""},
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "moonshot": {"label": "Moonshot AI", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    "siliconflow": {"label": "SiliconFlow", "base_url": "https://api.siliconflow.cn/v1", "model": "deepseek-ai/DeepSeek-V3"},
    "ollama": {"label": "Ollama（本地）", "base_url": "http://127.0.0.1:11434/v1", "model": "qwen2.5:7b"},
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": "custom",
    "base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0.2,
    "max_tokens": 500,
    "timeout": 20.0,
}

_SETTING_KEYS = tuple(DEFAULT_SETTINGS)
_KEY_MASK = "________SAVED________"


def normalize_base_url(url: object) -> str:
    """规范化接口地址：兼容用户直接粘贴完整 chat/completions 地址。"""

    value = str(url or "").strip()
    if value.lower().endswith("/chat/completions"):
        value = value[: -len("/chat/completions")]
    return value.rstrip("/")


def _clamp(value: float, low: float, high: float, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return min(high, max(low, number))


class LLMAdapter:
    """模型设置存储 + OpenAI 兼容客户端装配器（线程安全）。"""

    def __init__(self, settings_file: str | Path | None = None) -> None:
        self._lock = threading.RLock()
        self._file = Path(settings_file) if settings_file else Path(
            os.environ.get("SIMTROUBLE_LLM_SETTINGS", DEFAULT_SETTINGS_FILE)
        )
        self._settings: dict[str, Any] = self._load()

    # ------------------------------------------------------------------ 存储

    def _load(self) -> dict[str, Any]:
        settings = dict(DEFAULT_SETTINGS)
        env_key = os.environ.get("SIMTROUBLE_LLM_API_KEY", "").strip()
        if self._file.exists():
            try:
                stored = json.loads(self._file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                stored = {}
            if isinstance(stored, dict):
                for key in _SETTING_KEYS:
                    if key in stored and stored[key] is not None:
                        settings[key] = stored[key]
        elif env_key:
            # 兼容旧的环境变量方式（base_url/model 为空时交由用户在界面中补全）
            settings["api_key"] = env_key
            settings["base_url"] = normalize_base_url(
                os.environ.get("SIMTROUBLE_LLM_BASE_URL", "https://api.openai.com/v1")
            )
            settings["model"] = os.environ.get("SIMTROUBLE_LLM_MODEL", "gpt-4o-mini").strip()
        return self._sanitize(settings)

    @staticmethod
    def _sanitize(settings: dict[str, Any]) -> dict[str, Any]:
        clean = dict(DEFAULT_SETTINGS)
        clean["provider"] = str(settings.get("provider", "custom")).strip() or "custom"
        if clean["provider"] not in PROVIDERS:
            clean["provider"] = "custom"
        clean["base_url"] = normalize_base_url(settings.get("base_url"))
        clean["api_key"] = str(settings.get("api_key", "")).strip()
        clean["model"] = str(settings.get("model", "")).strip()
        clean["temperature"] = _clamp(settings.get("temperature", DEFAULT_SETTINGS["temperature"]), 0.0, 2.0, 0.2)
        clean["max_tokens"] = int(_clamp(settings.get("max_tokens", DEFAULT_SETTINGS["max_tokens"]), 1, 8192, 500))
        clean["timeout"] = _clamp(settings.get("timeout", DEFAULT_SETTINGS["timeout"]), 1.0, 120.0, 20.0)
        return clean

    def _save(self) -> None:
        payload = {k: v for k, v in self._settings.items() if k != "api_key"}
        payload["api_key"] = self._settings["api_key"]
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            # 持久化失败不影响本次运行（会话内设置仍然生效）
            pass

    # ------------------------------------------------------------------ 查询

    def is_configured(self) -> bool:
        with self._lock:
            return bool(self._settings["api_key"] and self._settings["base_url"] and self._settings["model"])

    def get_settings(self) -> dict[str, Any]:
        """返回脱敏后的设置（API Key 只露出末 4 位），用于前端回显。"""

        with self._lock:
            settings = dict(self._settings)
        key = settings.pop("api_key", "")
        settings["api_key_set"] = bool(key)
        settings["api_key_masked"] = f"****{key[-4:]}" if len(key) >= 4 else ("****" if key else "")
        settings["configured"] = self.is_configured()
        settings["providers"] = {
            name: {"label": meta["label"], "base_url": meta["base_url"], "model": meta["model"]}
            for name, meta in PROVIDERS.items()
        }
        return settings

    # ------------------------------------------------------------------ 更新

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """合并保存设置；API Key 留空或保持脱敏占位时沿用已保存的 Key。"""

        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        with self._lock:
            if payload.get("clear"):
                self._settings = dict(DEFAULT_SETTINGS)
                self._save()
                return self.get_settings()
            merged = dict(self._settings)
            for key in ("provider", "base_url", "model"):
                if key in payload and str(payload[key]).strip():
                    merged[key] = str(payload[key]).strip()
            api_key = str(payload.get("api_key", "")).strip()
            if api_key and api_key != _KEY_MASK and not set(api_key) <= {"*"}:
                merged["api_key"] = api_key
            for key in ("temperature", "max_tokens", "timeout"):
                if key in payload and str(payload[key]).strip() != "":
                    merged[key] = payload[key]
            self._settings = self._sanitize(merged)
            if self._settings["provider"] != "custom" and not merged.get("base_url"):
                self._settings["base_url"] = normalize_base_url(
                    PROVIDERS[self._settings["provider"]]["base_url"]
                )
            self._save()
            return self.get_settings()

    # ------------------------------------------------------------------ 客户端

    def get_client(self) -> OpenAICompatClient | None:
        """返回实现 ``complete(system=, user=)`` 端口的客户端；未配置时为 ``None``。"""

        with self._lock:
            if not self.is_configured():
                return None
            settings = dict(self._settings)
        return OpenAICompatClient(
            api_key=settings["api_key"],
            base_url=settings["base_url"],
            model=settings["model"],
            timeout=float(settings["timeout"]),
            temperature=float(settings["temperature"]),
            max_tokens=int(settings["max_tokens"]),
        )

    def test_connection(self, payload: dict[str, Any] | None = None) -> tuple[bool, str]:
        """用当前（或待保存的）设置发一次最小请求，返回 (是否成功, 说明)。"""

        if payload:
            with self._lock:
                merged = self._sanitize({**self._settings, **{
                    k: payload[k] for k in ("provider", "base_url", "model", "temperature", "max_tokens", "timeout")
                    if k in payload
                }})
                api_key = str(payload.get("api_key", "")).strip()
                if api_key and api_key != _KEY_MASK and not set(api_key) <= {"*"}:
                    merged["api_key"] = api_key
        else:
            with self._lock:
                merged = dict(self._settings)
        if not (merged["api_key"] and merged["base_url"] and merged["model"]):
            return False, "设置不完整：接口地址、API Key 与模型名称均不能为空"
        client = OpenAICompatClient(
            api_key=merged["api_key"],
            base_url=merged["base_url"],
            model=merged["model"],
            timeout=float(merged["timeout"]),
            temperature=float(merged["temperature"]),
            max_tokens=min(int(merged["max_tokens"]), 64),
        )
        try:
            text = client.complete(system="你是连接测试助手。", user="请只回复两个字：正常")
        except LLMUnavailableError as exc:
            return False, f"连接失败：{exc}"
        except ValueError as exc:
            return False, f"配置无效：{exc}"
        preview = text.strip().replace("\n", " ")[:40]
        return True, f"连接成功，模型已响应：{preview}"
