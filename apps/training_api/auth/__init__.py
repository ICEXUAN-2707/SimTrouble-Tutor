"""Product v0.5 local identity and authentication boundary."""

from .models import (
    AuthSessionV05,
    AuthUserV05,
    LoginRequest,
    RegisterRequest,
)
from .repository import (
    AuthenticationContext,
    AuthenticationStore,
    UsernameUnavailableError,
)

__all__ = [
    "AuthSessionV05",
    "AuthUserV05",
    "AuthenticationContext",
    "AuthenticationStore",
    "LoginRequest",
    "RegisterRequest",
    "UsernameUnavailableError",
]
