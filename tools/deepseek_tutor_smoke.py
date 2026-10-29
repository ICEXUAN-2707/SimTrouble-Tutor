"""One explicit, credential-gated real DeepSeek Tutor smoke request."""

from __future__ import annotations

import asyncio
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.training_api.learning_models import TutorMode
from apps.training_api.session_service import SessionService
from apps.training_api.tutor.service import build_tutor_service
from apps.training_api.tutor.settings import DeepSeekSettings
from tools.start_product_v04_acceptance import DEFAULT_CONFIG, load_local_config


async def main(config_path: Path) -> None:
    effective_environment = load_local_config(config_path)
    effective_environment.update(os.environ)
    settings = DeepSeekSettings.from_env(effective_environment)
    if settings.provider != "deepseek":
        raise SystemExit("FAIL: this explicit smoke command requires SIMTROUBLE_LLM_PROVIDER=deepseek")
    if not settings.configured:
        raise SystemExit(
            "SKIP: set SIMTROUBLE_LLM_ENABLED=true and DEEPSEEK_API_KEY before "
            "running the real-provider smoke test"
        )

    sessions = SessionService()
    session = sessions.create("ST-001")
    service = build_tutor_service(sessions, settings)
    result = await service.ask(
        session.session_id,
        "请引导我决定下一步观察什么，不要直接告诉我故障答案。",
    )
    if result.tutor_mode is not TutorMode.LLM:
        metric = service.metrics.snapshot(session.session_id)[-1]
        raise SystemExit(
            f"FAIL: provider call used fallback ({metric.fallback_reason})"
        )
    print(
        "PASS: real DeepSeek Tutor response validated; "
        f"action={result.tutor.suggested_action}; hint_level={result.tutor.hint_level}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    asyncio.run(main(args.config))
