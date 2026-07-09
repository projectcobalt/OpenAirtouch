"""Adaptive command intent dispatch and semantic command helpers."""

from __future__ import annotations

from typing import Any

from ..session.queue import TransactionSpec
from .adaptive_contracts import AdaptiveCommandIntent
from .adaptive_restore import _ac_setting_records_from_state, _group_for_id, _indexed, _number, _optional_int
from .commands import CommandRequestError, build_transaction


class AdaptiveCommandMixin:
    def _set_ac_setpoint(self, state: dict[str, Any], ac_id: int, setpoint: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        ac = _indexed(state.get("acs") or {}, ac_id) or {}
        current = _number((ac.get("status") or {}).get("setpoint")) if isinstance(ac, dict) else None
        if current is None or int(round(current)) == setpoint:
            return None
        key = f"ac:{ac_id}:setpoint"
        payload = {"ac": ac_id, "setpoint": setpoint}
        self._record_restore(key, "ac_status", {"ac": ac_id, "setpoint": int(round(current))}, payload)
        intent = AdaptiveCommandIntent("ac_status", payload, "ac", "set ac setpoint", restore_key=key, expected_value=setpoint)
        return self._send_transaction(state, intent, key, status, now)

    def _set_ac_mode(self, state: dict[str, Any], ac_id: int, mode_intent: Any, status: dict[str, Any], now: float) -> TransactionSpec | None:
        if mode_intent.mode is None or mode_intent.mode == mode_intent.current_mode:
            return None
        key = f"ac:{ac_id}:mode"
        payload = {"ac": ac_id, "mode": mode_intent.mode}
        self._record_restore(key, "ac_status", {"ac": ac_id, "mode": mode_intent.current_mode}, payload)
        intent = AdaptiveCommandIntent("ac_status", payload, "ac", mode_intent.reason, restore_key=key, expected_value=mode_intent.mode)
        return self._send_transaction(state, intent, key, status, now)

    def _set_ac_control_sensor(self, state: dict[str, Any], ac_id: int, sensor: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        records = _ac_setting_records_from_state(state)
        record = next((item for item in records if item.get("ac") == ac_id), None)
        if record is None:
            status["errors"].append(f"missing AC setting record for AC {ac_id + 1}")
            return None
        current = _optional_int(record.get("ctrl_thermostat"))
        if current is None or current == sensor:
            return None
        target_records = [dict(item) for item in records]
        target = next(item for item in target_records if item.get("ac") == ac_id)
        target["ctrl_thermostat"] = sensor
        payload = {"ac": ac_id, "ctrl_thermostat": sensor, "records": target_records}
        original_records = [dict(item) for item in records]
        original_payload = {"ac": ac_id, "ctrl_thermostat": current, "records": original_records}
        key = f"ac:{ac_id}:control_sensor"
        self._record_restore(key, "ac_setting_new", original_payload, {"ac": ac_id, "ctrl_thermostat": sensor})
        intent = AdaptiveCommandIntent("ac_setting_new", payload, "touchpad", "set AC control sensor", restore_key=key, expected_value=sensor)
        return self._send_transaction(state, intent, key, status, now)

    def _set_touchpad_temperature(self, state: dict[str, Any], sensor: int, temperature: float, status: dict[str, Any], now: float) -> TransactionSpec | None:
        rounded = int(round(temperature))
        payload = {"sensor": sensor, "temperature": rounded}
        intent = AdaptiveCommandIntent("sensor_temperature", payload, "touchpad", "update synthetic control temperature", expected_value=rounded)
        return self._send_transaction(state, intent, f"sensor:{sensor}:temperature", status, now)

    def _set_group_setpoint(self, state: dict[str, Any], group_id: int, setpoint: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        group = _group_for_id(state, group_id)
        current = _number((group.get("status") or {}).get("setpoint")) if isinstance(group, dict) else None
        if current is None or int(round(current)) == setpoint:
            return None
        key = f"group:{group_id}:setpoint"
        payload = {"group": group_id, "setpoint": setpoint}
        self._record_restore(key, "group_setpoint", {"group": group_id, "setpoint": int(round(current))}, payload)
        intent = AdaptiveCommandIntent("group_setpoint", payload, "zone", "set zone setpoint", restore_key=key, expected_value=setpoint)
        return self._send_transaction(state, intent, key, status, now)

    def _set_group_percentage(self, state: dict[str, Any], group_id: int, percentage: int, status: dict[str, Any], now: float) -> TransactionSpec | None:
        group = _group_for_id(state, group_id)
        group_status = (group.get("status") or {}) if isinstance(group, dict) else {}
        current = _number(group_status.get("percentage"))
        if current is None or int(round(current)) == percentage:
            return None
        payload = {"group": group_id, "percentage": percentage}
        if group_status.get("sensor_control") is True:
            setpoint = _number(group_status.get("setpoint"))
            if setpoint is None:
                return None
            key = f"group:{group_id}:sensor_control"
            self._record_restore(
                key,
                "group_setpoint",
                {"group": group_id, "setpoint": int(round(setpoint))},
                payload,
                target_action="group_percentage",
            )
        else:
            key = f"group:{group_id}:percentage"
            self._record_restore(key, "group_percentage", {"group": group_id, "percentage": int(round(current))}, payload)
        intent = AdaptiveCommandIntent("group_percentage", payload, "zone", "set zone damper", restore_key=key, expected_value=percentage)
        return self._send_transaction(state, intent, key, status, now)

    def _send_ac_power(
        self,
        state: dict[str, Any],
        ac_id: int,
        power_on: bool,
        status: dict[str, Any],
        now: float,
        *,
        key_prefix: str,
    ) -> TransactionSpec | None:
        payload = {"ac": ac_id, "power_on": power_on}
        key = f"{key_prefix}:ac:{ac_id}:power"
        intent = AdaptiveCommandIntent("ac_status", payload, "ac", key_prefix.replace("_", " "), restore_key=key, expected_value=power_on)
        return self._send_transaction(state, intent, key, status, now)

    def _send_transaction(
        self,
        state: dict[str, Any],
        intent: AdaptiveCommandIntent,
        throttle_key: str,
        status: dict[str, Any],
        now: float,
    ) -> TransactionSpec | None:
        throttle_value = intent.expected_value if intent.expected_value is not None else _command_value(intent.data)
        if throttle_value is not None and not self._should_send(throttle_key, throttle_value, now):
            return None
        try:
            request = intent.as_transaction_request()
            spec = build_transaction(str(request["action"]), request["data"], state=state)
            status.setdefault("command_intents", []).append(intent.as_status())
            return spec
        except CommandRequestError as exc:
            status.setdefault("errors", []).append(str(exc))
            return None

    def _should_send(self, key: str, value: int | bool, now: float) -> bool:
        last = self._last_command.get(key)
        if last is not None and last[0] == value and now - last[1] < max(1.0, self.config.command_cooldown):
            return False
        self._last_command[key] = (value, now)
        return True


def _command_value(payload: dict[str, Any]) -> int | bool | None:
    for key in ("mode", "setpoint", "percentage", "temperature", "ctrl_thermostat", "power_on"):
        if key in payload:
            value = payload[key]
            if isinstance(value, bool):
                return value
            return _optional_int(value)
    return None
