"""Restore ledger helpers for adaptive control."""

from __future__ import annotations

from typing import Any

from ..session.queue import TransactionSpec
from .adaptive_contracts import AdaptiveCommandIntent
from .adaptive_runtime_state import (
    _ac_name,
    _ac_setting_record_for,
    _command_value,
    _group_for_id,
    _group_name,
    _groups_for_ac,
    _indexed,
    _mode_name,
    _number,
    _optional_int,
)


class AdaptiveRestoreMixin:
    def _restore_all(self, state: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for key in list(self._restore_records):
            specs.extend(self._restore_record(state, key, status, now))
        return specs

    def _restore_ac(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs = self._restore_ac_mode(state, ac_id, status, now)
        specs.extend(self._restore_ac_setpoint(state, ac_id, status, now))
        specs.extend(self._restore_ac_control_sensor(state, ac_id, status, now))
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
            specs.extend(self._restore_group_setpoint(state, group_id, status, now))
            specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_ac_mode(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:mode", status, now)

    def _restore_ac_setpoint(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:setpoint", status, now)

    def _restore_ac_control_sensor(self, state: dict[str, Any], ac_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"ac:{ac_id}:control_sensor", status, now)

    def _restore_group_setpoint(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:setpoint", status, now)

    def _restore_group_power(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:power", status, now)

    def _restore_group_sensor_control(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:sensor_control", status, now)

    def _record_restore(
        self,
        key: str,
        action: str,
        original: dict[str, Any],
        target: dict[str, Any],
        *,
        target_action: str | None = None,
    ) -> bool:
        if original == target:
            if key not in self._restore_records:
                return False
            self._restore_records.pop(key, None)
            return False
        record = self._restore_records.setdefault(key, {"action": action, "original": dict(original)})
        record["action"] = action
        record.setdefault("original", dict(original))
        record["target"] = dict(target)
        if target_action is not None:
            record["target_action"] = target_action
        else:
            record.pop("target_action", None)
        return True

    def _restore_dampers_for_ac(self, state: dict[str, Any], ac_id: int, ac: dict[str, Any], status: dict[str, Any], now: float) -> list[TransactionSpec]:
        specs: list[TransactionSpec] = []
        for group_id, _group in _groups_for_ac(state, ac_id, ac):
            specs.extend(self._restore_group_sensor_control(state, group_id, status, now))
            specs.extend(self._restore_group_percentage(state, group_id, status, now))
        return specs

    def _restore_group_percentage(self, state: dict[str, Any], group_id: int, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        return self._restore_record(state, f"group:{group_id}:percentage", status, now)

    def _restore_record(self, state: dict[str, Any], key: str, status: dict[str, Any], now: float) -> list[TransactionSpec]:
        record = self._restore_records.get(key)
        if record is None:
            return []
        action = str(record.get("action") or "")
        target_action = str(record.get("target_action") or action)
        original = record.get("original") if isinstance(record.get("original"), dict) else {}
        target = record.get("target") if isinstance(record.get("target"), dict) else {}
        current = self._restore_current_payload(state, target_action, target)
        if current != target:
            self._restore_records.pop(key, None)
            return []
        spec = self._send_restore_action(state, action, original, status, now)
        if spec is None:
            return []
        self._restore_records.pop(key, None)
        status["actions"].append(self._restore_action_text(state, action, original))
        return [spec]

    def _restore_current_payload(self, state: dict[str, Any], action: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        if action == "ac_status":
            ac_id = _optional_int(payload.get("ac"))
            ac = _indexed(state.get("acs") or {}, ac_id) if ac_id is not None else None
            ac_status = (ac.get("status") or {}) if isinstance(ac, dict) else {}
            current: dict[str, Any] = {"ac": ac_id}
            if "mode" in payload:
                current["mode"] = _optional_int(ac_status.get("mode"))
            if "setpoint" in payload:
                setpoint = _number(ac_status.get("setpoint"))
                current["setpoint"] = int(round(setpoint)) if setpoint is not None else None
            if "power_on" in payload:
                current["power_on"] = bool(ac_status.get("power_on"))
            return current
        if action in {"group_setpoint", "group_percentage", "group_power"}:
            group_id = _optional_int(payload.get("group"))
            group = _group_for_id(state, group_id) if group_id is not None else None
            group_status = (group.get("status") or {}) if isinstance(group, dict) else {}
            current = {"group": group_id}
            if action == "group_power":
                current["on"] = group_status.get("power_name") in {"on", "turbo"}
                current["sensor_control"] = group_status.get("sensor_control") is not False
                if "setpoint" in payload:
                    setpoint = _number(group_status.get("setpoint"))
                    current["setpoint"] = int(round(setpoint)) if setpoint is not None else None
                if "percentage" in payload:
                    percentage = _number(group_status.get("percentage"))
                    current["percentage"] = int(round(percentage)) if percentage is not None else None
            else:
                field = "setpoint" if action == "group_setpoint" else "percentage"
                value = _number(group_status.get(field))
                current[field] = int(round(value)) if value is not None else None
            return current
        if action == "ac_setting_new":
            ac_id = _optional_int(payload.get("ac"))
            record = _ac_setting_record_for(state, ac_id) if ac_id is not None else None
            return {
                "ac": ac_id,
                "ctrl_thermostat": _optional_int(record.get("ctrl_thermostat")) if isinstance(record, dict) else None,
            }
        return None

    def _send_restore_action(
        self,
        state: dict[str, Any],
        action: str,
        original: dict[str, Any],
        status: dict[str, Any],
        now: float,
    ) -> TransactionSpec | None:
        if action == "ac_status":
            key_suffix = "mode" if "mode" in original else "setpoint" if "setpoint" in original else "status"
            key = f"restore:ac:{original.get('ac')}:{key_suffix}"
            intent = AdaptiveCommandIntent("restore_state", original, "restore", "restore AC state", action, original, restore_key=key, expected_value=_command_value(original))
            return self._send_transaction(state, intent, key, status, now)
        if action == "group_setpoint":
            key = f"restore:group:{original.get('group')}:setpoint"
            intent = AdaptiveCommandIntent("restore_state", original, "restore", "restore zone setpoint", action, original, restore_key=key, expected_value=_command_value(original))
            return self._send_transaction(state, intent, key, status, now)
        if action == "group_percentage":
            key = f"restore:group:{original.get('group')}:percentage"
            intent = AdaptiveCommandIntent("restore_state", original, "restore", "restore zone damper", action, original, restore_key=key, expected_value=_command_value(original))
            return self._send_transaction(state, intent, key, status, now)
        if action == "group_power":
            key = f"restore:group:{original.get('group')}:power"
            intent = AdaptiveCommandIntent("restore_state", original, "restore", "restore zone power", action, original, restore_key=key, expected_value=_command_value(original))
            return self._send_transaction(state, intent, key, status, now)
        if action == "ac_setting_new":
            key = f"restore:ac:{original.get('ac')}:control_sensor"
            intent = AdaptiveCommandIntent("restore_state", original, "restore", "restore AC control sensor", action, original, restore_key=key, expected_value=_command_value(original))
            return self._send_transaction(state, intent, key, status, now)
        return None

    def _restore_action_text(self, state: dict[str, Any], action: str, original: dict[str, Any]) -> str:
        if action == "ac_status":
            ac_id = _optional_int(original.get("ac"))
            ac = _indexed(state.get("acs") or {}, ac_id) if ac_id is not None else {}
            if "mode" in original:
                return f"{_ac_name(ac_id or 0, ac or {})}: Restored Mode: {_mode_name(_optional_int(original.get('mode')))}"
            if "setpoint" in original:
                return f"{_ac_name(ac_id or 0, ac or {})}: Restored Setpoint: {original['setpoint']}°"
            return f"{_ac_name(ac_id or 0, ac or {})}: Restored AC State"
        group_id = _optional_int(original.get("group")) or 0
        group = _group_for_id(state, group_id)
        if action == "group_setpoint":
            return f"{_group_name(group_id, group)}: Restored Setpoint: {original['setpoint']}°"
        if action == "group_percentage":
            return f"{_group_name(group_id, group)}: Restored Damper: {original['percentage']}%"
        if action == "group_power":
            return f"{_group_name(group_id, group)}: Restored Power: {'On' if original.get('on') else 'Off'}"
        if action == "ac_setting_new":
            ac_id = _optional_int(original.get("ac")) or 0
            ac = _indexed(state.get("acs") or {}, ac_id) or {}
            return f"{_ac_name(ac_id, ac)}: Restored Control Sensor"
        return "Adaptive State Restored"
