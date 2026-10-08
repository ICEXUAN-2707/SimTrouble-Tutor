"""Explicitly Demo-only deterministic diagnosis check for ST-001."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any


def judge_diagnosis(text: str, *, released_evidence_ids: Collection[str]) -> dict[str, Any]:
    normalized = text.lower().replace(" ", "")
    correct = any(
        marker in normalized
        for marker in ("位置偏移", "位置不匹配", "位姿偏移", "object_pose")
    )
    return {
        "mode": "ST-001 Demo-only",
        "submitted": text,
        "correct": correct,
        "reference": "工件 X 方向位置相对预期偏移 70 mm，导致抓取位置不匹配。",
        "evidence_used": list(released_evidence_ids),
        "note": "本结果仅为 ST-001 演示判定；正式诊断合同与五维能力评分尚未实现。",
    }
