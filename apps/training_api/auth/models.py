"""Strict public request and response models for Product v0.5 auth."""

from __future__ import annotations

import re

from pydantic import Field, field_validator

from ..learning_models import FrozenContract


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fff-]{3,32}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class AuthUserV05(FrozenContract):
    user_id: str = Field(min_length=1)
    username: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=1, max_length=32)


class AuthSessionV05(FrozenContract):
    user: AuthUserV05
    expires_at: int = Field(ge=0)
    csrf_token: str = Field(min_length=32)


class RegisterRequest(FrozenContract):
    username: str
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    display_name: str | None = Field(default=None, max_length=32)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError("invalid username")
        return normalized

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class LoginRequest(FrozenContract):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()

