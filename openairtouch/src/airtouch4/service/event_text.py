"""Plain-English summaries for runtime events exposed through the API."""

from __future__ import annotations

from typing import Any


MODE_NAMES = {
    0: "Auto",
    1: "Heat",
    2: "Dry",
    3: "Fan",
    4: "Cool",
}

FAN_NAMES = {
    0: "Auto",
    1: "Low",
    2: "Medium",
    3: "High",
    7: "Unchanged",
}

CATEGORY_LABELS = {
    "ac_command": "AC Command",
    "ac_config": "AC Config",
    "ac_status": "AC Status",
    "bus": "Bus",
    "client_command": "Client Command",
    "client_status": "Client Status",
    "controller": "Controller",
    "decode": "Decode",
    "event": "Event",
    "favourite": "Favourite",
    "runtime": "Runtime",
    "sensor": "Sensor",
    "touchpad": "Touchpad",
    "transaction": "Transaction",
    "zone_command": "Zone Command",
    "zone_config": "Zone Config",
    "zone_status": "Zone Status",
}

COMMAND_MEANINGS = {
    "CMD_EXPANDED": "Carries An Expanded System Payload, Usually Touchpad Presence Or Debug Information.",
    "SET_GROUP_STATUS": "Requests A Zone Power, Damper, Or Temperature Control Change.",
    "RESPONSE_GROUP_STATUS": "Reports Current Zone Power, Damper, Temperature, Spill, And Sensor Flags.",
    "SET_AC_STATUS": "Requests An AC Power, Mode, Fan, Or Setpoint Change.",
    "RESPONSE_AC_STATUS": "Reports Current AC Power, Mode, Fan, Setpoint, Temperature, And Error State.",
    "EXPANSION_DAMPER_STATUS": "Reports Expansion Damper State.",
    "SET_TEMPERATURE": "Sends A Temperature Value To The Main Board.",
    "RESPONSE_LED": "Reports Touchpad LED State.",
    "SET_GROUP_CONTROL_MOBILE": "Client API Request To Change A Zone.",
    "GROUP_STATUS_MOBILE": "Client API Zone Status Update.",
    "SET_AC_CONTROL_MOBILE": "Client API Request To Change An AC.",
    "AC_STATUS_MOBILE": "Client API AC Status Update.",
    "CLIENT_BULK_INFO": "Client API Request Or Reply For Bulk System Information.",
    "SET_ACTIVE_FAVOURITE": "Requests The Active Favourite To Change.",
    "RESPONSE_ACTIVE_FAVOURITE": "Reports The Active Favourite.",
    "SET_FAVOURITE": "Updates Favourite Configuration.",
    "RESPONSE_FAVOURITE": "Reports Favourite Configuration.",
    "RESPONSE_PROGRAM_DEFINE": "Reports Program Schedule Configuration.",
    "SET_AC_TIMER": "Updates AC Timer Configuration.",
    "RESPONSE_AC_TIMER": "Reports AC Timer Configuration.",
    "SET_PROGRAM_DEFINE_NEW": "Updates Newer Program Schedule Configuration.",
    "RESPONSE_PROGRAM_DEFINE_NEW": "Reports Newer Program Schedule Configuration.",
    "SET_DATETIME": "Sets The AirTouch Clock.",
    "DATETIME_STATUS": "Reports The AirTouch Clock.",
    "RESPONSE_AC_RUNTIME_STATUS": "Reports AC Runtime State.",
    "SET_TURBO_GROUP": "Updates Turbo Zone Configuration.",
    "RESPONSE_TURBO_GROUP": "Reports Turbo Zone Configuration.",
    "SET_GROUP_NAME": "Updates Zone Names.",
    "RESPONSE_GROUP_NAME": "Reports Zone Names.",
    "SET_PREFERENCE": "Updates User Or System Preferences.",
    "RESPONSE_PREFERENCE": "Reports User Or System Preferences.",
    "RESPONSE_MAIN_DISPLAY_NEW": "Reports Main Display State For Newer Firmware.",
    "RESPONSE_MAIN_DISPLAY": "Reports Main Display State.",
    "RESPONSE_SETTING_DATA": "Reports System Setting Data.",
    "SET_PARAMETERS": "Updates System Parameters.",
    "RESPONSE_PARAMETERS": "Reports System Parameters.",
    "START_BALANCE": "Starts Airflow Balancing.",
    "RESPONSE_BALANCE": "Reports Airflow Balancing State.",
    "STOP_BALANCE": "Stops Airflow Balancing.",
    "SET_GROUPING": "Updates Zone-To-Damper Grouping.",
    "RESPONSE_GROUPING": "Reports Zone-To-Damper Grouping.",
    "SET_SPILL": "Updates Spill Configuration.",
    "RESPONSE_SPILL": "Reports Spill Configuration.",
    "SET_SERVICE": "Updates Service Configuration.",
    "RESPONSE_SERVICE": "Reports Service Configuration.",
    "SET_PASSWORD_INFO": "Updates Password Or PIN Information.",
    "RESPONSE_PASSWORD_INFO": "Reports Password Or PIN Information.",
    "CLEAR_NOTIFICATION": "Clears A Notification.",
    "RESPONSE_DIALOG_MESSAGE": "Reports A Touchpad Dialog Message.",
    "SET_PAIR_SENSOR": "Pairs Or Configures An RF Sensor.",
    "RESPONSE_SENSOR_LIST": "Reports Known RF Sensors And Touchpads.",
    "SET_SENSOR_TEMP": "Updates A Sensor Temperature Value.",
    "RESPONSE_SENSOR_INFO": "Reports RF Sensor Temperature, Battery, And Signal Information.",
    "SET_AC_BASE_INFO": "Updates AC Base Configuration.",
    "RESPONSE_AC_BASE_INFO": "Reports AC Base Configuration.",
    "RESPONSE_AC_SETTING": "Reports AC Capability And Setting Data.",
    "SET_AC_SETTING_NEW": "Updates Newer AC Setting Data.",
    "RESPONSE_AC_SETTING_NEW": "Reports Newer AC Setting Data.",
    "RESPONSE_DEBUG_INFO": "Reports Debug Information.",
    "RESPONSE_GATEWAY_INFO": "Reports Gateway Information.",
}


def describe_event(record: dict[str, Any]) -> dict[str, Any]:
    """Return a stable human-readable companion for a structured event record."""
    event = record.get("event")
    if event == "transaction":
        return _describe_transaction(record.get("transaction") or {})
    if event == "status":
        return _plain("runtime", _display_text(record.get("message") or "Runtime Status Update"))
    if event == "controller":
        return _plain("controller", _display_text(record.get("message") or "Controller Reported An Error"), severity="warning")

    decoded = record.get("decoded")
    if isinstance(decoded, dict):
        described = _describe_decoded(decoded, direction=str(record.get("direction") or event or "event"))
        if described is not None:
            return described

    cmd = record.get("cmd_name") or record.get("cmd")
    direction = str(record.get("direction") or event or "event").upper()
    if cmd:
        return _describe_command(direction, cmd)
    return _plain("event", _display_text(record.get("message") or event or "Runtime Event"))


def _describe_decoded(decoded: dict[str, Any], *, direction: str) -> dict[str, Any] | None:
    kind = decoded.get("type")
    prefix = direction.upper()
    if kind == "ac_status_internal":
        records = [_describe_ac_status(record) for record in decoded.get("records", []) if isinstance(record, dict)]
        return _record_list("ac_status", f"{prefix} AC Status", records)
    if kind == "set_ac_status_internal":
        return _plain("ac_command", f"{prefix} {_describe_ac_command(decoded)}")
    if kind == "group_status_internal":
        records = [_describe_group_status(record) for record in decoded.get("records", []) if isinstance(record, dict)]
        return _record_list("zone_status", f"{prefix} Zone Status", records)
    if kind == "set_group_status_internal":
        return _plain("zone_command", f"{prefix} {_describe_group_command(decoded)}")
    if kind == "group_status_client":
        records = [
            _describe_client_group_status(record)
            for record in decoded.get("records", [])
            if isinstance(record, dict)
        ]
        return _record_list("client_status", f"{prefix} Client Zone Status", records)
    if kind == "group_status_client_request":
        return _plain("client_status", f"{prefix} Client Zone Status Request")
    if kind == "group_control_client":
        return _plain("client_command", f"{prefix} {_describe_client_group_command(decoded)}")
    if kind == "ac_status_client":
        records = [
            _describe_ac_status(record)
            for record in decoded.get("records", [])
            if isinstance(record, dict)
        ]
        return _record_list("client_status", f"{prefix} Client AC Status", records)
    if kind == "ac_status_client_request":
        return _plain("client_status", f"{prefix} Client AC Status Request")
    if kind == "ac_control_client":
        return _plain("client_command", f"{prefix} {_describe_client_ac_command(decoded)}")
    if kind == "bulk_info_client":
        return _plain("client_status", f"{prefix} Client Bulk Info")
    if kind == "group_name":
        records = []
        for record in decoded.get("records", []):
            if isinstance(record, dict):
                records.append(f"Zone {_one_based(record.get('group'))} Is Named {_text(record.get('name'), '-')}")
        return _record_list("zone_config", f"{prefix} Zone Names", records)
    if kind in {"grouping", "set_grouping"}:
        records = decoded.get("records") if isinstance(decoded.get("records"), list) else [decoded]
        lines = [_describe_grouping(record) for record in records if isinstance(record, dict)]
        return _record_list("zone_config", f"{prefix} Zone Grouping", lines)
    if kind in {"ac_base_info", "set_ac_base_info"}:
        records = decoded.get("records") if isinstance(decoded.get("records"), list) else []
        lines = []
        for record in records:
            if isinstance(record, dict):
                lines.append(
                    f"AC {_one_based(record.get('ac'))}: {_text(record.get('name'), '-')} "
                    f"Zones {_one_based(record.get('group_start'))}-{_zone_end(record)}"
                )
        return _record_list("ac_config", f"{prefix} AC Base Info", lines)
    if kind in {"ac_setting", "ac_setting_new", "set_ac_setting_new"}:
        records = decoded.get("records") if isinstance(decoded.get("records"), list) else []
        lines = []
        for record in records:
            if isinstance(record, dict):
                lines.append(
                    f"AC {_one_based(record.get('ac'))} settings: "
                    f"Setpoint Range {_text(record.get('min_setpoint'), '-')}-{_text(record.get('max_setpoint'), '-')} C"
                )
        return _record_list("ac_config", f"{prefix} AC Settings", lines)
    if kind == "sensor_info":
        records = decoded.get("records")
        if isinstance(records, list):
            lines = [_describe_sensor_info(record) for record in records if isinstance(record, dict)]
            return _record_list("sensor", f"{prefix} Sensor Info", lines)
        sensor = decoded.get("sensor")
        return _plain("sensor", f"{prefix} Sensor {_hex_or_text(sensor)} Reports {_temp(decoded.get('temperature'))}")
    if kind == "sensor_list":
        sensor_count = len(decoded.get("sensor_addresses") or [])
        touchpad_count = len(decoded.get("touchpad_addresses") or [])
        return _plain("sensor", f"{prefix} Sensor List: {sensor_count} RF Sensors, {touchpad_count} Touchpads")
    if kind == "touchpad_temperature":
        return _plain("touchpad", f"{prefix} Touchpad Heartbeat {_temp(decoded.get('temperature'))}")
    if kind == "led_response":
        return _plain("touchpad", f"{prefix} LED State {_title(decoded.get('led_name'))}")
    if kind == "active_favourite":
        return _plain("favourite", f"{prefix} Active Favourite {_text(decoded.get('active_favourite'), '-')}")
    if kind == "set_active_favourite":
        return _plain("favourite", f"{prefix} Set Active Favourite {_text(decoded.get('favourite'), '-')}")
    if kind in {"decode_error", "unknown"}:
        return _plain("decode", f"{prefix} {_title(kind)}: {_text(decoded.get('error') or decoded.get('raw'), '-')}", severity="warning")
    return None


def _describe_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    name = transaction.get("name") or f"command 0x{int(transaction.get('command', 0)):02X}"
    event = transaction.get("transaction_event") or transaction.get("event")
    attempts = transaction.get("attempts")
    detail = f" after {attempts} attempt(s)" if attempts else ""
    if event == "complete":
        return _plain("transaction", f"Command {_display_text(name)} Completed{_display_text(detail)}")
    if event == "failed":
        reason = transaction.get("reason")
        return _plain("transaction", f"Command {_display_text(name)} Failed{_display_text(detail)}: {_display_text(_text(reason, 'No Response'))}", severity="warning")
    if event == "request":
        return _plain("transaction", f"Command {_display_text(name)} Sent{_display_text(detail)}")
    return _plain("transaction", f"Command {_display_text(name)}: {_display_text(_text(event, 'Transaction Update'))}")


def _describe_ac_status(record: dict[str, Any]) -> str:
    if record.get("available") is False:
        return f"AC {_one_based(record.get('ac'))} Unavailable"
    parts = [
        f"AC {_one_based(record.get('ac'))}",
        "On" if record.get("power_on") else "Off",
        _mode(record.get("mode")),
        f"Fan {_fan(record.get('fan'))}",
    ]
    if record.get("setpoint") is not None:
        parts.append(f"Setpoint {_temp(record.get('setpoint'))}")
    if record.get("sensor_temp") is not None:
        parts.append(f"Sensor {_temp(record.get('sensor_temp'))}")
    if record.get("error_code") not in (None, 0):
        parts.append(f"Error {record.get('error_code')}")
    return ", ".join(parts)


def _describe_ac_command(decoded: dict[str, Any]) -> str:
    parts = [f"Set AC {_one_based(decoded.get('ac'))}"]
    power = decoded.get("power_name")
    if power and power != "unchanged":
        parts.append(_title(power))
    mode = decoded.get("mode")
    if mode is not None:
        parts.append(f"Mode {_mode(mode)}")
    fan = decoded.get("fan")
    if fan is not None:
        parts.append(f"Fan {_fan(fan)}")
    if decoded.get("setpoint") is not None:
        parts.append(f"Setpoint {_temp(decoded.get('setpoint'))}")
    return ", ".join(parts)


def _describe_group_status(record: dict[str, Any]) -> str:
    parts = [
        f"Zone {_one_based(record.get('group'))}",
        _title(record.get("power_name") or "unknown"),
    ]
    if record.get("sensor_control"):
        parts.append("Temperature Control")
        parts.append(f"Setpoint {_temp(record.get('setpoint'))}")
    else:
        parts.append(f"Open {_text(record.get('percentage'), '-')}%")
    if record.get("temperature") is not None:
        parts.append(f"Room {_temp(record.get('temperature'))}")
    if record.get("spill_on"):
        parts.append("Spill Active")
    if record.get("low_battery"):
        parts.append("Sensor Battery Low")
    return ", ".join(parts)


def _describe_group_command(decoded: dict[str, Any]) -> str:
    parts = [f"Set Zone {_one_based(decoded.get('group'))}"]
    power = decoded.get("power_name")
    if power and power != "value_change":
        parts.append(_title(power))
    if decoded.get("sensor_control"):
        parts.append(f"Setpoint {_temp(decoded.get('setpoint'))}")
    elif decoded.get("percentage") is not None:
        parts.append(f"Open {_text(decoded.get('percentage'), '-')}%")
    return ", ".join(parts)


def _describe_client_group_status(record: dict[str, Any]) -> str:
    parts = [
        f"Zone {_one_based(record.get('group'))}",
        _title(record.get("power_name") or "unknown"),
    ]
    if record.get("control_method") == "temperature":
        parts.append("Temperature Control")
        if record.get("setpoint") is not None:
            parts.append(f"Setpoint {_temp(record.get('setpoint'))}")
    else:
        parts.append(f"Open {_text(record.get('percentage'), '-')}%")
    if record.get("temperature") is not None:
        parts.append(f"Room {_temp(record.get('temperature'))}")
    if record.get("spill_on"):
        parts.append("Spill Active")
    if record.get("low_battery"):
        parts.append("Sensor Battery Low")
    return ", ".join(parts)


def _describe_client_group_command(decoded: dict[str, Any]) -> str:
    parts = [f"Client Set Zone {_one_based(decoded.get('group'))}"]
    power = decoded.get("power_name")
    if power and power != "unchanged":
        parts.append(_title(power))
    method = decoded.get("control_method")
    if method and method != "unchanged":
        parts.append(_title(method))
    setting = decoded.get("setting")
    if isinstance(setting, dict):
        if setting.get("setpoint") is not None:
            parts.append(f"Setpoint {_temp(setting.get('setpoint'))}")
        if setting.get("damper_percentage") is not None:
            parts.append(f"Open {_text(setting.get('damper_percentage'), '-')}%")
        if setting.get("action") is not None:
            parts.append(_title(setting.get("action")))
    return ", ".join(parts)


def _describe_client_ac_command(decoded: dict[str, Any]) -> str:
    parts = [f"Client Set AC {_one_based(decoded.get('ac'))}"]
    power = decoded.get("power_name")
    if power and power != "unchanged":
        parts.append(_title(power))
    if decoded.get("mode") is not None:
        parts.append(f"Mode {_mode(decoded.get('mode'))}")
    if decoded.get("fan") is not None:
        parts.append(f"Fan {_fan(decoded.get('fan'))}")
    if decoded.get("setpoint") is not None:
        parts.append(f"Setpoint {_temp(decoded.get('setpoint'))}")
    return ", ".join(parts)


def _describe_grouping(record: dict[str, Any]) -> str:
    start = record.get("zone_start")
    count = record.get("zone_count")
    end = None
    if isinstance(start, int) and isinstance(count, int):
        end = start + max(count, 1) - 1
    return (
        f"Zone {_one_based(record.get('group'))}: Dampers {_one_based(start)}-{_one_based(end)}, "
        f"Minimum {_text(record.get('min_percent'), '-')}%, Thermostat {_hex_or_text(record.get('thermostat'))}"
    )


def _describe_sensor_info(record: dict[str, Any]) -> str:
    parts = [
        f"Sensor {_hex_or_text(record.get('sensor'))}",
        f"{_temp(record.get('temperature'))}",
    ]
    kind = record.get("kind") or record.get("sensor_kind")
    if kind:
        parts.append(_title(kind))
    if record.get("battery") is not None:
        parts.append(f"Battery {_text(record.get('battery'), '-')}%")
    if record.get("low_battery"):
        parts.append("Battery Low")
    if record.get("signal") is not None:
        parts.append(f"Signal {_text(record.get('signal'), '-')} dBm")
    status = record.get("status")
    if status:
        parts.append(_display_text(status))
    return ", ".join(parts)


def _record_list(category: str, headline: str, records: list[str]) -> dict[str, Any]:
    if not records:
        return _plain(category, headline)
    detail = "; ".join(records[:4])
    extra = len(records) - 4
    if extra > 0:
        detail = f"{detail}; {extra} more"
    return {
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, _display_text(category)),
        "severity": "info",
        "headline": headline,
        "detail": detail,
        "text": f"{headline}: {detail}",
    }


def _plain(category: str, text: str, *, severity: str = "info") -> dict[str, Any]:
    return {
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, _display_text(category)),
        "severity": severity,
        "headline": text,
        "detail": "",
        "text": text,
    }


def _mode(value: Any) -> str:
    return MODE_NAMES.get(_int_or_none(value), _text(value, "-"))


def _fan(value: Any) -> str:
    return FAN_NAMES.get(_int_or_none(value), _text(value, "-"))


def _temp(value: Any) -> str:
    if value is None:
        return "-"
    return f"{value} C"


def _one_based(value: Any) -> str:
    number = _int_or_none(value)
    if number is None:
        return "-"
    return str(number + 1)


def _zone_end(record: dict[str, Any]) -> str:
    start = _int_or_none(record.get("group_start"))
    count = _int_or_none(record.get("group_count"))
    if start is None or count is None:
        return "-"
    return str(start + max(count, 1))


def _hex_or_text(value: Any) -> str:
    number = _int_or_none(value)
    if number is None:
        return _text(value, "-")
    return f"0x{number:02X}"


def _describe_command(direction: str, value: Any) -> dict[str, Any]:
    key = _text(value, "")
    label = _command_label(key)
    meaning = COMMAND_MEANINGS.get(key)
    if meaning is None:
        meaning = _generic_command_meaning(key)
    if meaning:
        return _plain("bus", f"{direction} {label}: {meaning}")
    return _plain("bus", f"{direction} {label}")


def _command_label(value: Any) -> str:
    text = _text(value, "Unknown Command")
    if text == "UNKNOWN":
        return "Unknown Command"
    if text.startswith("CMD_"):
        text = text[4:]
    text = text.lower()
    return _display_text(text)


def _generic_command_meaning(value: str) -> str:
    if value == "UNKNOWN":
        return "Command Meaning Is Not Known Yet."
    if value.startswith("SET_"):
        return "Sends A Control Or Configuration Change."
    if value.startswith("RESPONSE_"):
        return "Carries A Status Or Configuration Reply."
    if value.endswith("_MOBILE") or value.startswith("CLIENT_"):
        return "Carries Client API Traffic."
    return ""


def _title(value: Any) -> str:
    text = _text(value, "-").replace("_", " ")
    return _display_text(text)


def _display_text(value: Any) -> str:
    text = _text(value, "")
    words = []
    for word in text.replace("_", " ").split(" "):
        if not word:
            words.append(word)
        elif word.upper() in {"AC", "RF", "RX", "TX", "LED", "API"}:
            words.append(word.upper())
        elif word.startswith("0x"):
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def _text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    return str(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
