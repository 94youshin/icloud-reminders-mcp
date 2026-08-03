from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(frozen=True)
class Settings:
    username: str
    china_mainland: bool = False
    default_list: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        username = os.getenv("ICLOUD_USERNAME", "").strip()
        if not username:
            raise RuntimeError(
                "ICLOUD_USERNAME is required. Authenticate locally with the "
                "pyicloud CLI first; do not put an Apple password in MCP config."
            )
        default_list = os.getenv("ICLOUD_DEFAULT_REMINDER_LIST", "").strip() or None
        return cls(
            username=username,
            china_mainland=_env_bool("ICLOUD_CHINA_MAINLAND"),
            default_list=default_list,
        )
