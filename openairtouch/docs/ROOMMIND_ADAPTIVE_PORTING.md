# RoomMind Adaptive Porting Progress

This document tracks how RoomMind concepts map into the AirTouch adaptive controller, what has already landed, and what still needs work.

RoomMind reference sources:

- Repository: https://github.com/snazzybean/roommind
- Coordinator: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/coordinator.py
- Thermal model: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/control/thermal_model.py
- MPC controller: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/control/mpc_controller.py
- MPC optimizer: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/control/mpc_optimizer.py
- Solar model: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/control/solar.py
- Weather manager: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/managers/weather_manager.py
- EKF training manager: https://raw.githubusercontent.com/snazzybean/roommind/main/custom_components/roommind/managers/ekf_training_manager.py

## Current AirTouch Adaptive Shape

The AirTouch controller now has three layers:

1. AirTouch translator
   - Converts AC/group runtime data into normalized adaptive devices and rooms.
   - `learn` is derived from temperature availability.
   - `configured_control` is driven by explicit `control_zones`.
   - `control_enabled` is asserted only when a configured zone is allowed to act in adaptive mode.

2. Adaptive policy authority
   - Owns modes: `off`, `recommend`, `auto_off`, `adaptive`.
   - Restores previous adaptive setpoints when disabled or unsafe.
   - Keeps existing adaptive mode as the final command authority.
   - Control only asserts against zones explicitly enabled for adaptive control.

3. Learning and MPC core
   - Per-zone first-order RC model.
   - EKF parameter learning.
   - MPC proposal path.
   - Compressor minimum run/off tracking.
   - Learning persistence.
   - Model reset and accelerated-learning flag.

## RoomMind Architecture Summary

RoomMind is a Home Assistant custom integration. Its major runtime pieces are:

- `RoomMindCoordinator`
  - Runs every `UPDATE_INTERVAL = 30` seconds.
  - Reads room sensors, schedules, weather, occupancy, windows, covers, and devices.
  - Computes current solar input once per cycle.
  - Processes each room and records history.
  - Persists thermal model data periodically.

- `RoomMindStore`
  - Persists room config, global settings, and thermal data through HA storage.

- `RoomModelManager`
  - Owns per-room `ThermalEKF` instances.
  - Provides model confidence, prediction uncertainty, mode counts, prediction, reset, and boost-learning operations.

- `ThermalEKF` and `RCModel`
  - EKF state: room temp, heat-loss rate, heat power, cool power, solar response, occupancy response.
  - Model uses exact 1R1C analytical prediction.
  - Confidence combines data readiness and prediction uncertainty.

- `MPCController`
  - Uses MPC only when the model is calibrated.
  - Falls back to bang-bang/hysteresis while learning.
  - Uses forecast, solar, residual heat, occupancy, and device capabilities.

- Manager modules
  - Weather forecast/cloud data.
  - Solar input.
  - EKF training accumulation.
  - Compressor groups.
  - Residual heat.
  - Covers/blinds.
  - Heat source orchestration.
  - Window pause.
  - Mold risk.
  - Valve protection.

AirTouch does not need RoomMind's HA room CRUD or websocket API wholesale because AirTouch already has native zones, ACs, runtime state, and command paths. The useful porting target is the control pipeline and model-management behavior.

## Key RoomMind Behaviors To Preserve

### Learning cadence

RoomMind coordinator ticks every 30 seconds, but EKF training is accumulated into roughly 3-minute observations via `EKF_UPDATE_MIN_DT = 3.0`.

MPC is blocked until the room has enough data:

- 60 idle observations, approximately 3 hours.
- 20 active observations for the usable mode, approximately 1 hour.
- Prediction uncertainty below 0.5 C for the operating point.

Rooms that rarely heat or cool can stay in learning for days.

### Confidence

RoomMind confidence is not only sample count. It combines:

- Data factor: progress toward idle and active sample gates.
- Accuracy factor: prediction standard deviation relative to the 0.5 C MPC gate.

Data alone gives limited confidence. Accurate prediction with enough data is what makes MPC trustworthy.

### Fallback while learning

RoomMind falls back to bang-bang/hysteresis while the model is learning. It does not wait idle or expose untrusted MPC actuation.

For AirTouch, the equivalent is:

- Continue rule-based adaptive target while MPC is warming up.
- Use MPC only when the zone model is ready for the current heat/cool mode.
- Keep adaptive mode and `control_zones` as final authority.
- Treat `control_zones` as stored room intent; only assert runtime `control_enabled` while adaptive mode is active.

### Solar

RoomMind actively feeds solar input into the EKF and MPC:

- Reads weather cloud cover.
- Computes normalized solar irradiance from latitude, longitude, time, and cloud cover.
- Feeds `q_solar` into EKF training and prediction.
- Records solar irradiance in analytics.
- Uses cloud forecast for cover/blind prediction.

AirTouch already has a solar parameter in the EKF, but it is not yet fed with real data.

### Accelerated learning

RoomMind boost-learning does not skip sample gates. It boosts EKF covariance, making the model relearn faster after room conditions change.

For AirTouch:

- Keep `accelerated_learning` as a persisted per-zone flag.
- When enabled, boost EKF covariance once on transition from off to on.
- Do not inflate confidence.
- Do not lower MPC readiness gates.
- Add a cooldown before repeated boosts.

## Porting Matrix

| RoomMind feature | AirTouch status | Notes |
| --- | --- | --- |
| Per-room normalized model | Partial | AirTouch has `AdaptiveRoom`/`AdaptiveDevice` translator. |
| Derived learn mode | Done | Zone learns when temperature/temp-enabled data exists. |
| Explicit control mode | Done | `control_zones` stores room intent; adaptive mode gates command assertion. |
| EKF RC model | Partial | Core exists; needs closer confidence and solar/occupancy parity. |
| MPC readiness gates | Partial | 3-minute cadence and 60/20 gates are now the intended direction; verify current constants before release. |
| MPC fallback while learning | Partial | AirTouch falls back to rule target, not RoomMind bang-bang. That is acceptable for ducted AC but should be explicit. |
| Prediction std gate | Partial | Threshold is 0.5 C; mode-specific prediction std should be refined. |
| Solar gain input | Not started | Add irradiance entity first, computed fallback second. |
| Weather forecast | Partial | Optional hourly weather forecast exists and current weather anchors now/current hour. |
| Cloud forecast | Not started | Needed for solar forecast and better MPC horizon. |
| Occupancy input | Not started | EKF supports occupancy term but no source is plumbed. |
| Residual heat | Not started | More relevant to hydronic/radiator systems, but ducted AC may still benefit from compressor/fan residual behavior. |
| Compressor groups | Partial | Shared compressor topology is configurable; min run/off guard is group-aware. Not yet full RoomMind master-device orchestration. |
| Ducted power fraction | Not started | Critical AirTouch-specific enhancement. Need zone percentage, active zone count, fan, mode, and setpoint gap. |
| Heat source orchestration | Mostly not applicable | AirTouch has one ducted plant per AC; use concepts for multi-AC routing later. |
| Covers/blinds | Not applicable for adaptive core | Solar analytics may support future cover recommendations, but do not port into AirTouch controller now. |
| Window pause | Not started | Could be HA entity based and should suspend control/learning for affected zones. |
| Mold risk | Not started | Out of scope for ducted AC adaptive core unless humidity/comfort features expand. |
| Analytics history | Partial | In-memory history exists; needs persisted actual-vs-predicted history and export/diagnostics. |
| Diagnostics export | Not started | Add backend diagnostic payload for model params, confidence, history, weather, and command decisions. |
| Model reset | Done | Zone and all-model reset exist. |
| Boost learning | Partial | Flag exists; should align exactly with RoomMind covariance boost plus cooldown. |

## Recommended Feature Phases

## Execution Jobs

These jobs are ordered so model inputs become trustworthy before actuation becomes more ambitious. Each job should keep adaptive mode and `control_zones` as final authority.

### RM-AIR-001 - Error surfacing contract

Status: in progress

Scope:

- Any adaptive, weather, forecast, solar, model-management, or diagnostics function that can fail should surface a concise error in the runtime snapshot.
- Main-page alert strip must display those errors without requiring the adaptive settings page.
- Existing surfaces:
  - `integrations.weather.error`
  - `integrations.indoor.error`
  - `integrations.forecast.error`
  - `integrations.adaptive.errors`
  - controller/runtime errors
  - MQTT/error-resolver/bus/AC fault alerts

Acceptance:

- Forecast fetch errors appear as `Forecast weather: ...` in the main alert strip.
- Solar/irradiance fetch errors, when added, appear as `Solar: ...`.
- Adaptive model exceptions appear as `Adaptive: ...`.

### RM-AIR-010 - RoomMind parity audit

Status: in progress

Progress:

- Confirmed 3-minute learning observations in `ZoneThermalModel`.
- Confirmed RoomMind-style 60 idle / 20 active sample gates.
- Added mode-specific readiness status:
  - `cooling_ready`
  - `heating_ready`
  - `idle_observations`
  - `cooling_observations`
  - `heating_observations`
- Confidence remains data-progress plus prediction-accuracy based.
- Accelerated learning remains covariance boost only; it does not inflate confidence or bypass gates.

Scope:

- Recheck current `AdaptiveMpcEngine` against RoomMind:
  - 3-minute learning observations.
  - 60 idle observations.
  - 20 active observations for the operating mode.
  - prediction std below 0.5 C.
  - confidence based on data progress plus accuracy, not sample count alone.
- Add mode-specific readiness:
  - `cooling_ready`
  - `heating_ready`
  - `idle_observations`
  - `cooling_observations`
  - `heating_observations`
- Keep accelerated learning as covariance boost only.

Acceptance:

- Tests prove low-sample models remain in learning even with `accelerated_learning=true`.
- Tests prove cooling MPC needs cooling observations, not only generic active observations.
- Status explains why a model is not ready.

### RM-AIR-020 - Solar and irradiance pipeline

Status: complete for current-hour solar signal

Progress:

- Backend config now includes optional `solar_irradiance_entity` and `cloud_cover_entity`, both defaulting empty.
- HA polling can read configured irradiance and cloud-cover sensors.
- HA polling reads `sun.sun` and `zone.home` when weather/solar polling is active.
- Adaptive status exposes `solar.source`, `solar.q_solar`, `solar.irradiance_w_m2`, `solar.cloud_cover`, and `solar.sun_elevation`.
- W/m2 and kW/m2 irradiance normalize into `q_solar`; cloud cover falls back through current sun elevation; no source falls back to zero.
- Solar read errors are surfaced through existing adaptive errors as `Solar: ...`.
- `q_solar` is fed into EKF observation, MPC proposal planning, and analytics history.
- No adaptive UI changes were made.
- Forecast-hour cloud/irradiance is still future work; the current implementation supplies the current-hour solar signal.

Scope:

- Add backend config:
  - `solar_irradiance_entity`, default empty.
  - optional `cloud_cover_entity`, default empty.
- Preferred source order:
  1. configured HA irradiance entity;
  2. forecast/weather irradiance or cloud cover;
  3. sun-position plus cloud-cover fallback;
  4. conservative sun-position-only fallback;
  5. `0.0`.
- Normalize irradiance to `q_solar`:
  - W/m2 -> `value / 1000`
  - kW/m2 -> `value`
  - clamp to safe range.
- Feed `q_solar` into EKF observe, MPC propose, and analytics.

Acceptance:

- Missing solar entity does not break adaptive.
- Bad solar entity produces `Solar: ...` in the main alert strip.
- Status reports solar source and `q_solar`.
- Tests cover W/m2, kW/m2, sun/cloud fallback, below-horizon zeroing, cloud diagnostic behavior, and no-source fallback.

### RM-AIR-030 - Outdoor/weather training guard

Status: complete

Progress:

- EKF learning now pauses when outdoor temperature is unavailable.
- The zone still appears as learning when it has temperature/temp-enabled data.
- Skipped observations are tracked with `skipped_observations` and `last_skip_reason`.
- Top-level learning status reports `learning_paused_reason`.
- Analytics records `skipped_outdoor` points for visibility.

Scope:

- Pause EKF training when outdoor temperature is unavailable.
- Do not train the heat-loss model with room temperature, null, or synthetic fallback outdoor temp.
- Continue safe restore/recommendation behavior as appropriate.

Acceptance:

- Status reports learning paused reason.
- Alert strip surfaces persistent weather-source failure via existing weather/forecast errors or adaptive errors.
- Tests prove model sample counts do not increase without outdoor temperature.

### RM-AIR-040 - Ducted AC power fraction foundation

Status: partial - foundation complete

Progress:

- Adaptive room translation now identifies active rooms and available zone `percentage`/damper-like fields.
- Rooms expose a diagnostic `power_fraction` estimate: equal share across active zones when damper data is missing, percentage-weighted share when supplied, and zero for inactive zones.
- Analytics exposes this as `estimated_power_fraction`.
- This signal is intentionally diagnostic-only for now and is not used to scale EKF or MPC behavior, so ducted AC learning remains conservative.
- No new actuation paths were added.

Scope:

- Identify and expose per-zone active power share inputs for ducted AC.
- Inputs:
  - AC mode;
  - active zone count;
  - zone percentage/damper;
  - turbo state;
  - fan mode;
  - setpoint gap;
  - compressor group state where useful.
- Add a conservative `estimated_power_fraction` diagnostic with equal-share fallback where safe.
- Keep the estimate diagnostic-only until runtime captures and tests prove weighted learning is conservative.
- Do not claim full power-fraction learning until real AirTouch fields and model impact are verified.

Acceptance:

- Equal-share fallback is visible when damper values are missing.
- Single-zone active estimate caps safely.
- Closed/off zones report zero estimated active share.
- Tests cover diagnostics and conservative fallback behavior.

### RM-AIR-050 - Persistent analytics and diagnostics

Status: complete

Progress:

- Persisted adaptive learning now keeps bounded per-zone analytics history with actual temperature, predicted temperature when available, mode, source, skipped flag/reason, `q_solar`, and `estimated_power_fraction`.
- Diagnostics expose mode-specific readiness reasons, confidence/progress, skipped observation counts, last skip reason, covariance summary, model params, compressor state, and last plans.
- History remains bounded by the existing 576-point per-zone deque and status exports only the latest 24 analytics points.
- Diagnostics are available through the existing adaptive snapshot/status plumbing; no new UI or actuation was added.

Scope:

- Persist actual-vs-predicted history.
- Track skipped observations and reasons.
- Track weather/forecast/solar source.
- Track model params, confidence, readiness, covariance summary, and last plans.
- Use the existing adaptive snapshot/status section as the diagnostics export surface.

Acceptance:

- Diagnostics include enough data to explain why a zone is learning, ready, or blocked.
- Any diagnostics generation error surfaces as `Adaptive: ...` or controller error.
- Tests cover history persistence and diagnostic redaction/sizing if needed.

### RM-AIR-060 - Rich AirTouch MPC strategy

Status: queued behind RM-AIR-040 and RM-AIR-050

Queue note:

- Assigned to autonomous backend job queue as recommendation/status-only work.
- Must not add new actuation paths without explicit UI/config consent.

Scope:

- Extend MPC output beyond setpoint:
  - estimated time to target;
  - comfort risk;
  - zone overshoot risk;
  - recommended zone strategy.
- Keep as recommendation/status first, not commands.

Acceptance:

- No new actuation without explicit UI/config consent.
- Adaptive mode and `control_zones` remain final authority.

### Phase 1 - Tighten RoomMind parity in backend

Goal: make learning behavior honest and diagnosable.

Tasks:

- Confirm accepted observation cadence is 3 minutes.
- Confirm readiness is:
  - idle observations >= 60
  - active observations >= 20 for current mode
  - prediction std < 0.5 C
- Make `confidence` match RoomMind formula more closely:
  - data factor from idle and current active mode progress
  - accuracy factor from weighted prediction std
  - no confidence boost from accelerated learning
- Add `readiness_reason` and `learning_progress` to status.
- Add mode-specific readiness fields:
  - `cooling_ready`
  - `heating_ready`
  - `idle_observations`
  - `cooling_observations`
  - `heating_observations`
- Add boost cooldown:
  - store `last_boost_ts`
  - ignore repeated boost requests for a configured interval.

### Phase 2 - Solar and weather enrichment

Goal: feed real solar/load signals into EKF and MPC.

Preferred source order:

1. Configured HA irradiance entity.
2. Open-Meteo/weather forecast irradiance or cloud cover if available.
3. Computed sun-position plus cloud-cover fallback.
4. Sun-position-only conservative fallback.
5. Zero solar if unavailable.

Tasks:

- Add config fields:
  - `solar_irradiance_entity`
  - optionally `cloud_cover_entity`
- Add HA read path for irradiance/cloud cover.
- Normalize irradiance:
  - W/m2 -> `value / 1000`
  - kW/m2 -> `value`
  - clamp to a safe range, e.g. `0.0..1.2`
- Add computed fallback using sun elevation and cloud coverage.
- Add `SolarSignal` to adaptive integration payload.
- Feed `q_solar` into:
  - `AdaptiveMpcEngine.observe`
  - `AdaptiveMpcEngine.propose`
  - analytics status/history.

### Phase 3 - Ducted AC power fraction

Goal: adapt RoomMind's abstract active power to ducted AirTouch behavior.

RoomMind uses active power/fraction per room. AirTouch needs a zone share estimate.

Inputs:

- AC mode.
- AC setpoint gap.
- Fan mode.
- Active zone count.
- Zone damper percentage.
- Zone turbo state.
- Optional supply air temp later.
- Optional compressor state if derivable.

Initial model:

- Determine total active power fraction from AC mode and setpoint gap.
- Split across active zones by damper percentage.
- Normalize shares so open zones sum to approximately 1.
- Feed per-zone share as EKF/MPC `power_fraction`.

Guardrails:

- If zone percentage is unknown, use equal share.
- If only one zone is open, cap at 1.0.
- Do not allow tiny fractional noise below a minimum active threshold.

### Phase 4 - Better AirTouch actuation strategy

Goal: move beyond setpoint-only MPC once models are trustworthy.

Near-term:

- Keep adaptive mode authority unchanged.
- Keep `control_zones` required for all commands.
- MPC may propose:
  - AC setpoint target
  - controlled zone setpoint target
  - expected action/power fraction

Later:

- Add strategy recommendation fields, not commands at first:
  - preferred zones to serve
  - zones likely to overshoot
  - estimated time to target
  - predicted comfort risk
- Only command richer zone strategy after enough runtime evidence.

Do not let MPC silently open/close zones until there is a clear safety model and UI consent.

### Phase 5 - Analytics and diagnostics

Goal: make model behavior inspectable without reading logs.

Backend tasks:

- Persist actual-vs-predicted history.
- Track skipped observations and reasons.
- Track outdoor source and solar source.
- Track confidence/readiness history.
- Add diagnostics export:
  - adaptive config
  - weather/forecast/solar signals
  - per-zone model params
  - per-zone covariance summary
  - recent history
  - last MPC plans
  - compressor guard state
  - last adaptive commands/recommendations.

UI tasks should be handed to the UI thread.

## Current Gaps To Resolve Before Calling It Complete

1. Solar input is not yet plumbed.
2. Ducted AC power fraction is not yet modeled.
3. Confidence/readiness should be audited against the latest RoomMind formula.
4. Accelerated learning needs cooldown and should remain covariance boost only.
5. Analytics should persist actual-vs-predicted history, not only short in-memory points.
6. Forecast should include humidity/cloud/irradiance where available.
7. Outdoor/weather unavailable handling should pause EKF learning rather than train on fallbacks.
8. Per-mode readiness should be visible in backend status.

## Proposed AirTouch-Specific Principle

RoomMind's flow should be preserved, but translated to AirTouch ownership:

- If a zone exists and has temperature, it learns.
- If a zone is not in `control_zones`, it never receives adaptive commands.
- If adaptive mode is not `adaptive`, MPC never asserts commands.
- If MPC is not ready, use the existing adaptive rule target as fallback.
- If required weather/outdoor inputs are missing, pause learning/control rather than training bad data.
- If the model is reset or boosted, keep the system conservative until readiness gates are satisfied again.

## Progress Log

- Added normalized adaptive model layer.
- Added AirTouch snapshot translator.
- Added derived learning from temperature-capable zones.
- Added explicit `control_zones`.
- Added EKF/RC model and MPC proposal path.
- Added learning persistence.
- Added model reset and accelerated-learning action.
- Added optional forecast weather entity with current-weather now anchor.
- Added humidity compensation that tolerates no humidity sensor.
- Added adaptive compressor topology:
  - blank config means every AC has an independent compressor;
  - configured groups such as `0,1;2,3` treat listed ACs as shared compressor plants;
  - min-run guard applies to the shared plant, not blindly to each AC.
- Started aligning learning gates with RoomMind:
  - 3-minute observation cadence.
  - 60 idle and 20 active observation targets.
  - 0.5 C prediction uncertainty gate.
- Remaining high-priority work:
  - finish confidence parity audit;
  - add solar signal pipeline;
  - add ducted power fraction;
  - add persistent analytics and diagnostics.
