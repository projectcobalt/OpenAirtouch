"""Compressor state grouping and minimum-cycle tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompressorTracker:
    ac_state: dict[int, bool] = field(default_factory=dict)
    state: dict[int, bool] = field(default_factory=dict)
    changed_at: dict[int, float] = field(default_factory=dict)
    groups: tuple[tuple[int, ...], ...] = ()

    def configure(self, groups: tuple[tuple[int, ...], ...]) -> None:
        self.groups = tuple(tuple(group) for group in groups)
        self._recompute_all(0.0, preserve_existing=True)

    def observe(self, ac_id: int, power_on: bool, now: float) -> None:
        self.ac_state[ac_id] = power_on
        self._recompute_group(self._group_key(ac_id), now)

    def can_power_off(
        self,
        ac_id: int,
        now: float,
        minimum_run_seconds: float,
        *,
        planned_off: set[int] | None = None,
    ) -> bool:
        key = self._group_key(ac_id)
        if self._other_members_on(ac_id, planned_off=planned_off or set()):
            return True
        if self.state.get(key) is not True:
            return True
        changed = self.changed_at.get(key)
        return changed is None or now - changed >= minimum_run_seconds

    def can_power_on(self, ac_id: int, now: float, minimum_off_seconds: float) -> bool:
        key = self._group_key(ac_id)
        if self.state.get(key) is True:
            return True
        if self.state.get(key) is not False:
            return True
        changed = self.changed_at.get(key)
        return changed is None or now - changed >= minimum_off_seconds

    def status(self, now: float) -> dict[str, Any]:
        return {
            str(key): {
                "acs": list(self._members_for_key(key)),
                "power_on": power_on,
                "seconds_since_change": None if key not in self.changed_at else round(now - self.changed_at[key], 1),
            }
            for key, power_on in sorted(self.state.items())
        }

    def _recompute_all(self, now: float, *, preserve_existing: bool = False) -> None:
        keys = {self._group_key(ac_id) for ac_id in self.ac_state}
        keys.update(range(len(self.groups)))
        for key in sorted(keys):
            self._recompute_group(key, now, preserve_existing=preserve_existing)

    def _recompute_group(self, key: int, now: float, *, preserve_existing: bool = False) -> None:
        power_on = any(self.ac_state.get(member) is True for member in self._members_for_key(key))
        previous = self.state.get(key)
        if previous is None:
            self.state[key] = power_on
            if not preserve_existing:
                self.changed_at[key] = now
            return
        if previous != power_on:
            self.state[key] = power_on
            self.changed_at[key] = now

    def _group_key(self, ac_id: int) -> int:
        for index, group in enumerate(self.groups):
            if ac_id in group:
                return index
        return len(self.groups) + ac_id

    def _members_for_key(self, key: int) -> tuple[int, ...]:
        if 0 <= key < len(self.groups):
            return self.groups[key]
        return (key - len(self.groups),)

    def _other_members_on(self, ac_id: int, *, planned_off: set[int]) -> bool:
        members = self._members_for_key(self._group_key(ac_id))
        return any(member != ac_id and member not in planned_off and self.ac_state.get(member) is True for member in members)
