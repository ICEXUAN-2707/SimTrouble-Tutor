"""Strict public request and response models for Product v0.5 auth."""

from __future__ import annotations

import re

from pydantic import Field, field_validator, model_validator

from ..learning_models import FrozenContract


USERNAME_PATTERN_TEXT = r"^[A-Za-z0-9_\u4e00-\u9fff-]{3,32}$"
DISPLAY_NAME_PATTERN_TEXT = r"^(?!\s)(?!.*[\x00-\x1F\x7F]).*\S$"
USERNAME_PATTERN = re.compile(USERNAME_PATTERN_TEXT)
DISPLAY_NAME_PATTERN = re.compile(DISPLAY_NAME_PATTERN_TEXT)
MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128


class AuthUserV05(FrozenContract):
    user_id: str = Field(min_length=1)
    username: str = Field(
        min_length=3, max_length=32, pattern=USERNAME_PATTERN_TEXT
    )
    display_name: str = Field(min_length=1, max_length=32)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        if not DISPLAY_NAME_PATTERN.fullmatch(value):
            raise ValueError("invalid display name")
        return value


class AuthSessionV05(FrozenContract):
    user: AuthUserV05
    expires_at: int = Field(ge=0)
    csrf_token: str = Field(min_length=32)


class RegisterRequest(FrozenContract):
    username: str
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    display_name: str | None = Field(default=None, max_length=32)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_display_name(cls, value: object) -> object:
        if isinstance(value, dict) and value.get("display_name", ...) is None:
            raise ValueError("display_name cannot be null")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("invalid username")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not DISPLAY_NAME_PATTERN.fullmatch(value):
            raise ValueError("invalid display name")
        return value


class LoginRequest(FrozenContract):
    username: str
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("invalid username")
        return value
