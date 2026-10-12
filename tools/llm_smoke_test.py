"""Online LLM smoke test for the Tutor LLM module.

Run from the repository root.

Offline (no key required, verifies the whole chain with a scripted model):

    python -m tools.llm_smoke_test --offline

Online (calls a real provider through the OpenAI-compatible API):

    $env:SIMTROUBLE_LLM_API_KEY="sk-..."            # PowerShell
    $env:SIMTROUBLE_LLM_BASE_URL="https://api.deepseek.com/v1"
    $env:SIMTROUBLE_LLM_MODEL="deepseek-chat"
    python -m tools.llm_smoke_test

    export SIMTROUBLE_LLM_API_KEY="sk-..."          # Linux / macOS
    python -m tools.llm_smoke_test --question "机械臂动作完成但工件没被带走，我该看什么？"

Options:
    --question TEXT   学员提问，可重复传入以模拟多轮对话
    --evidence E02    先释放哪些证据（可重复），默认释放 E01
    --show-context    打印发送给模型的公开投影
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.case_engine import CaseLoader, CaseSession
from core.evidence_engine import EvidenceManager
from core.models import ReleasedEvidence, TrainingModule
from core.tutor_engine import (
    LeakGuard,
    ScriptedLLMClient,
    TutorService,
)

ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "data" / "cases" / "ST-001.json"
MODULE_PATH = ROOT / "data" / "modules" / "MOD-EXCEPTION.json"

OFFLINE_REPLY = json.dumps(
    {
        "intent": "question",
        "message": "夹爪命令已执行却没夹住工件，你会先怀疑夹持本身还是工件位置？",
        "suggested_next_step": "检查 E02 工件位置",
    },
    ensure_ascii=False,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SimTrouble Tutor LLM smoke test")
    parser.add_argument("--offline", action="store_true", help="不联网，用脚本化模型验证链路")
    parser.add_argument("--question", action="append", default=[], help="学员提问，可重复")
    parser.add_argument("--evidence", action="append", default=[], help="预先释放的证据 ID，可重复")
    parser.add_argument("--show-context", action="store_true", help="打印发送给模型的公开投影")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    env_service = TutorService.from_env()
    online = env_service.online and not args.offline
    if online:
        service = env_service
    else:
        if not args.offline:
            print(
                "[提示] 未检测到 SIMTROUBLE_LLM_API_KEY，自动以离线脚本模型运行。\n"
                "       在线模式请先设置 SIMTROUBLE_LLM_API_KEY，"
                "可选 SIMTROUBLE_LLM_BASE_URL / SIMTROUBLE_LLM_MODEL / SIMTROUBLE_LLM_TIMEOUT。",
                file=sys.stderr,
            )
        service = TutorService(ScriptedLLMClient([OFFLINE_REPLY] * 8))

    case = CaseLoader().load(CASE_PATH)
    module = TrainingModule.model_validate_json(MODULE_PATH.read_text(encoding="utf-8"))
    session = CaseSession(user_id="smoke-test", case=case)

    released: list[ReleasedEvidence] = []
    for evidence_id in args.evidence or ["E01"]:
        released.append(EvidenceManager().request(session, evidence_id.upper()))

    context = TutorService.build_context(
        module=module, case_session=session, released_evidence=released
    )
    guard = LeakGuard.from_case(case, released_ids=[item.id for item in released])

    print(f"模式: {'在线大模型' if online else '离线脚本模型（不联网）'}")
    if args.show_context:
        print("公开投影（发送给模型的唯一输入）:")
        print(json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print("-" * 60)

    questions = args.question or [
        "机械臂动作完成、夹爪闭合，但工件没有被带走。我应该先检查什么？",
        "直接告诉我真因是什么",
    ]

    for index, question in enumerate(questions, start=1):
        reply = service.respond(context, question, leak_guard=guard)
        print(f"\n[{index}] 学员: {question}")
        print(f"    intent : {reply.response.intent}")
        print(f"    来源   : {reply.source}")
        if reply.fallback_reason:
            print(f"    回退原因: {reply.fallback_reason}")
        print(f"    Tutor  : {reply.response.message}")
        if reply.response.suggested_next_step:
            print(f"    建议   : {reply.response.suggested_next_step}")

    print(
        "\n完成。source=llm 表示模型输出已通过契约、意图白名单、长度与泄漏校验；"
        "source=template 表示已回退到确定性规则策略。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
