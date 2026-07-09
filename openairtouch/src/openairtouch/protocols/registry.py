"""Protocol profile registry for OpenAirTouch."""

from __future__ import annotations

from .at4 import PROFILE as AT4
from .at5 import PROFILE as AT5
from .base import ProtocolProfile


def get_profile(name: str | None) -> ProtocolProfile:
    normalized = (name or "at4").lower()
    if normalized in {"auto", "at4", "airtouch4", "airtouch_4"}:
        return AT4
    if normalized in {"at5", "airtouch5", "airtouch_5"}:
        return AT5
    raise ValueError(f"unknown OpenAirTouch protocol profile: {name}")
