# Adaptive Layer Contracts

The adaptive layer has three boundaries:

1. Inputs are normalized before strategy logic consumes them.
2. Adaptive decisions are expressed as protocol-neutral command intents.
3. The status API exposes a UI contract that does not require frontend parsing of strategy internals.

## Inputs

`AdaptiveInputContract` describes the shape adaptive consumes:

- `runtime_connected` and `runtime_reason` describe whether protocol state is usable.
- `airtouch_state` is the decoded protocol snapshot.
- `weather`, `indoor`, `forecast`, `solar`, and `ac_telemetry` are normalized integration inputs from Home Assistant or addon-side sensors.

`build_adaptive_input_contract()` is the adapter from the service runtime snapshot plus integration registry into that contract. This keeps protocol parsing, Home Assistant entity details, and adaptive strategy logic separated.

## Commands

`AdaptiveCommandIntent` describes what adaptive wants to do:

- `action` is a protocol-neutral command name such as `group_percentage` or `ac_status`.
- `data` is the semantic payload.
- `surface` identifies the adaptive surface that requested the command.
- `reason`, `restore_key`, and `expected_value` preserve audit and restore context.

`AdaptiveCommandMixin` owns the dispatch step from intent to `TransactionSpec`. The active `ProtocolProfile` remains responsible for translating `action` plus `data` into wire transactions. If the AirTouch protocol changes, the adaptive layer should keep emitting the same command intent wherever the meaning is unchanged.

## UI Status

`status["ui"]` is the frontend-facing contract. It is derived from the rich backend status and contains:

- `summary`: mode, strategy, authority, headline, detail, and intent.
- `surfaces.environment`: outside temperature, forecast quality, weather pause, and fresh-air status.
- `surfaces.zone`: target, expected runtime, learning readiness, and zone action.
- `surfaces.hybrid`: control temperature, damper airflow plan, touchpad sensor, and strategy.
- `metrics`: display-ready status-strip rows such as authority, learning, control temperature, active control count, and ownership/detail.
- `analytics`: display-ready zone rows with adaptive state labels, flags, model badges, accelerated-learning state, and chart series data.
- `plan`: machine-readable target, runtime, control temperature, damper percentages, power fractions, and runtime series.
- `inputs`: normalized sensor/source values and errors.
- `commands`: current recommendations, actions, and active restore/control surfaces.

The UI status and analytics pages should render this contract directly. If required fields are missing, they should surface a contract error rather than deriving replacement meaning from the older `evaluations`, `intents`, `learning`, or strategy-specific fields. Those older fields can remain available for diagnostics, but they should not be the primary frontend rendering contract.

The frontend may still perform presentation-only work such as drawing an SVG path from `analytics.zones[].series.history` and `analytics.zones[].series.forecast`. Semantic decisions such as which zones appear, whether a zone is ready/learning, what badges mean, and what status text to show belong in the backend contract.
