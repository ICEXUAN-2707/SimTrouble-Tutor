"""UTC clock boundary for deterministic Session Trace tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_utc_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Trace clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)
