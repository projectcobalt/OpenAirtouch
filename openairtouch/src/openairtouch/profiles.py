"""Compatibility imports for OpenAirTouch protocol profiles."""

from __future__ import annotations

from .protocols import AT4, AT5, ProtocolProfile, get_profile
from .protocols.at4 import AT4Profile
from .protocols.at5 import AT5Profile

__all__ = [
    "AT4",
    "AT5",
    "AT4Profile",
    "AT5Profile",
    "ProtocolProfile",
    "get_profile",
]
