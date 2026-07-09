"""Adaptive control configuration validation and projection."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


ADAPTIVE_MODES = ("off", "recommend", "adaptive")
ADAPTIVE_LEARNING_MODES = ("off", "control")
ADAPTIVE_CONTROL_STRATEGIES = ("weather", "zone", "hybrid")


@dataclass(frozen=True)
class AdaptiveConfig:
    mode: str = "off"
    cool_diff: int = 4
    cool_comfort_temp: int = 24
    heat_diff: int = 4
    heat_comfort_temp: int = 20
    check_interval: float = 60.0
    command_cooldown: float = 300.0
    learning_mode: str = "off"
    mpc_horizon_hours: int = 6
    compressor_min_run_time: float = 0.0
    compressor_min_off_time: float = 0.0
    compressor_groups: tuple[tuple[int, ...], ...] = ()
    control_zones: tuple[int, ...] = ()
    outside_air_zones: tuple[int, ...] = ()
    control_strategy: str = "weather"
    dry_humidity_threshold: int = 70
    co2_ventilation_threshold_ppm: int = 1000
    mpc_comfort_weight: int = 70
    hybrid_min_damper_percent: int = 10
    hybrid_max_damper_percent: int = 100
    hybrid_idle_damper_percent: int = 10


def validated_adaptive_config(config: AdaptiveConfig) -> AdaptiveConfig:
    mode = str(config.mode or "off").lower()
    if mode not in ADAPTIVE_MODES:
        raise ValueError(f"adaptive mode must be one of {', '.join(ADAPTIVE_MODES)}")
    learning_mode = str(config.learning_mode or "off").lower()
    if learning_mode not in ADAPTIVE_LEARNING_MODES:
        raise ValueError(f"adaptive learning mode must be one of {', '.join(ADAPTIVE_LEARNING_MODES)}")
    control_strategy = str(config.control_strategy or "weather").lower()
    if control_strategy not in ADAPTIVE_CONTROL_STRATEGIES:
        raise ValueError(f"adaptive control strategy must be one of {', '.join(ADAPTIVE_CONTROL_STRATEGIES)}")
    learning_mode = "control" if strategy_uses_mpc(control_strategy) else "off"
    min_damper = _int_range("hybrid_min_damper_percent", config.hybrid_min_damper_percent, 0, 100)
    max_damper = _int_range("hybrid_max_damper_percent", config.hybrid_max_damper_percent, 0, 100)
    if min_damper > max_damper:
        raise ValueError("hybrid_min_damper_percent must be less than or equal to hybrid_max_damper_percent")
    return replace(
        config,
        mode=mode,
        learning_mode=learning_mode,
        control_strategy=control_strategy,
        cool_diff=_int_range("cool_diff", config.cool_diff, 0, 15),
        cool_comfort_temp=_int_range("cool_comfort_temp", config.cool_comfort_temp, 16, 32),
        heat_diff=_int_range("heat_diff", config.heat_diff, 0, 15),
        heat_comfort_temp=_int_range("heat_comfort_temp", config.heat_comfort_temp, 16, 32),
        check_interval=max(5.0, float(config.check_interval)),
        command_cooldown=max(1.0, float(config.command_cooldown)),
        mpc_horizon_hours=_int_range("mpc_horizon_hours", config.mpc_horizon_hours, 1, 24),
        mpc_comfort_weight=_int_range("mpc_comfort_weight", config.mpc_comfort_weight, 0, 100),
        dry_humidity_threshold=_int_range("dry_humidity_threshold", config.dry_humidity_threshold, 30, 100),
        co2_ventilation_threshold_ppm=_int_range("co2_ventilation_threshold_ppm", config.co2_ventilation_threshold_ppm, 400, 5000),
        compressor_min_run_time=max(0.0, float(config.compressor_min_run_time)),
        compressor_min_off_time=max(0.0, float(config.compressor_min_off_time)),
        compressor_groups=validated_compressor_groups(config.compressor_groups),
        control_zones=_validated_control_zones(config.control_zones),
        outside_air_zones=_validated_outside_air_zones(config.outside_air_zones),
        hybrid_min_damper_percent=min_damper,
        hybrid_max_damper_percent=max_damper,
        hybrid_idle_damper_percent=_int_range("hybrid_idle_damper_percent", config.hybrid_idle_damper_percent, 0, 100),
    )


def adaptive_public_config(config: AdaptiveConfig) -> dict[str, Any]:
    return {
        "mode": config.mode,
        "cool_diff": config.cool_diff,
        "cool_comfort_temp": config.cool_comfort_temp,
        "heat_diff": config.heat_diff,
        "heat_comfort_temp": config.heat_comfort_temp,
        "check_interval": config.check_interval,
        "command_cooldown": config.command_cooldown,
        "learning_mode": config.learning_mode,
        "learning_control": config.learning_mode == "control",
        "mpc_horizon_hours": config.mpc_horizon_hours,
        "compressor_min_run_time": config.compressor_min_run_time,
        "compressor_min_off_time": config.compressor_min_off_time,
        "compressor_groups": [list(group) for group in config.compressor_groups],
        "control_zones": list(config.control_zones),
        "outside_air_zones": list(config.outside_air_zones),
        "control_strategy": config.control_strategy,
        "dry_humidity_threshold": config.dry_humidity_threshold,
        "co2_ventilation_threshold_ppm": config.co2_ventilation_threshold_ppm,
        "mpc_comfort_weight": config.mpc_comfort_weight,
        "hybrid_min_damper_percent": config.hybrid_min_damper_percent,
        "hybrid_max_damper_percent": config.hybrid_max_damper_percent,
        "hybrid_idle_damper_percent": config.hybrid_idle_damper_percent,
    }


def zone_id(value: Any) -> int:
    try:
        zone = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("zone must be an integer") from exc
    if zone < 0:
        raise ValueError("zone must be non-negative")
    return zone


def strategy_uses_mpc(control_strategy: str) -> bool:
    return control_strategy in {"zone", "hybrid"}


def _int_range(name: str, value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def _validated_control_zones(value: Any) -> tuple[int, ...]:
    return _validated_zone_ids("control_zones", value)


def _validated_outside_air_zones(value: Any) -> tuple[int, ...]:
    return _validated_zone_ids("outside_air_zones", value)


def _validated_zone_ids(name: str, value: Any) -> tuple[int, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        raise ValueError(f"{name} must be a list or comma-separated string")
    zones = []
    for item in items:
        try:
            zone = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must contain integer zone ids") from exc
        if zone < 0:
            raise ValueError(f"{name} must contain non-negative zone ids")
        zones.append(zone)
    return tuple(sorted(set(zones)))


def validated_compressor_groups(value: Any) -> tuple[tuple[int, ...], ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        groups = []
        for group_text in value.split(";"):
            members = [item.strip() for item in group_text.split(",") if item.strip()]
            if members:
                groups.append(members)
    elif isinstance(value, (list, tuple)):
        groups = list(value)
    else:
        raise ValueError("compressor_groups must be a list of lists or semicolon-separated string")
    result: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for group in groups:
        if isinstance(group, str):
            items = [item.strip() for item in group.split(",") if item.strip()]
        elif isinstance(group, (list, tuple, set)):
            items = list(group)
        else:
            raise ValueError("compressor_groups must contain lists of AC ids")
        members = []
        for item in items:
            try:
                ac_id = int(item)
            except (TypeError, ValueError) as exc:
                raise ValueError("compressor_groups must contain integer AC ids") from exc
            if ac_id < 0:
                raise ValueError("compressor_groups must contain non-negative AC ids")
            if ac_id in seen:
                raise ValueError("an AC can only belong to one compressor group")
            members.append(ac_id)
            seen.add(ac_id)
        group_tuple = tuple(sorted(set(members)))
        if len(group_tuple) >= 2:
            result.append(group_tuple)
    return tuple(result)
