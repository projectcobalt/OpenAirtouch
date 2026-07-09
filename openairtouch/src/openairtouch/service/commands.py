"""OpenAirTouch command intent routing for app/API callers."""

from __future__ import annotations

from typing import Any

from ..protocols import ProtocolProfile, get_profile
from ..protocols.base import ProtocolCommandError
from ..session.queue import TransactionSpec


class CommandRequestError(ValueError):
    """Raised when an API command request is invalid or unsupported."""


def build_transaction(
    action: str,
    data: dict[str, Any],
    *,
    state: dict[str, Any] | None = None,
    profile: ProtocolProfile | None = None,
) -> TransactionSpec:
    """Build a runtime transaction from an OpenAirTouch command intent."""
    selected = profile or get_profile("auto")
    try:
        return selected.build_transaction(action, data, state=state)
    except ProtocolCommandError as exc:
        raise CommandRequestError(str(exc)) from exc
