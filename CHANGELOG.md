# Changelog

## Unreleased

- Split adaptive controller configuration, evaluation, persisted state, runtime-state helpers, MPC compressor tracking, and MPC status projection into focused modules.
- Retarget adaptive tests to public learning import/status APIs instead of reaching into controller MPC internals.
- Add a protocol profile boundary so runtime and command handling can delegate AirTouch-specific behavior while keeping higher service layers OpenAirTouch-oriented.
- Split the service controller into focused command queue, event log, config store, transport factory, runtime host, and runtime integration loop modules.
- Split the service API factory from static UI asset handling, HTTP routes, and WebSocket event streaming.
- Add adaptive input, UI, and command intent contracts, and move adaptive command construction out of the main adaptive controller.
- Remove controller integration compatibility shims and retarget tests to the modules that own datetime sync, Home Assistant polling, adaptive persistence, and event records.

## 0.8.6 - 2026-07-09

- Add a versioned adaptive UI contract with display-ready status metrics and analytics zone rows.
- Move Adaptive Status and Analytics rendering onto the backend contract so the frontend surfaces missing contract fields loudly instead of reconstructing adaptive meaning.
- Rename internal package and frontend helper paths from airtouch4 to openairtouch while keeping user-facing AirTouch protocol wording where it describes the actual bus.
- Remove add-on startup options for protocol selection, touchpad address overrides, touchpad temperature seed, heartbeat payload override, and UI theme.
- Keep runtime-owned touchpad temperature fallback and UI theme settings in the app, and always generate heartbeat payloads from the resolved runtime touchpad temperature.
- Refresh add-on field labels and descriptions, including entity-type and unit hints for AC telemetry sensors.

## 0.8.5 - 2026-07-07

- Clean the public release tree by moving local planning, research, screenshots, and operator tools out of tracked add-on paths.
- Keep only runtime scripts in the add-on script directory and neutralize public default transport settings.

## 0.8.4 - 2026-07-07

- Restore adaptive air quality configuration controls in the Svelte UI.
- Consolidate the add-on runtime around the Svelte UI and fail startup when the UI build is missing.
- Split service integration code into focused modules and remove legacy UI assets.
- Improve event diagnostics with richer APK-style command meanings and fallback labels.

## 0.8.3 - 2026-07-06

- Decode AirTouch mobile/server client traffic in live backend events without applying client echoes to replacement-touchscreen state.
- Surface readable client zone and AC messages in diagnostics, including spill-active status from client group status.
- Align internal AirTouch 4 temperature parsing with APK precision and preserve tenths in zone and AC temperature surfaces.
- Show spill groups on Control when AC settings allow them, using live balance/current opening for active spill while keeping normal off-zone bars closed.

## 0.6.3 - 2026-07-02

- Make adaptive heat/cool mode switching use comfort-band guards so satisfied rooms do not immediately call the opposite mode.
- Clarify adaptive model warm-up messages by reporting heating, cooling, or thermal model warm-up instead of implying selected zones are missing.

## 0.6.2 - 2026-07-02

- Add a zone tile control to resume sensor temperature control from damper mode without turning the zone off and back on.

## 0.6.1 - 2026-07-02

- Keep saved spill-zone configuration separate from live spill-open status in the service UI and clear stale spill configuration flags when new spill data arrives.

## 0.6.0 - 2026-07-01

- Replace deprecated FastAPI startup/shutdown event hooks with an application lifespan handler.
- Split adaptive control into focused signal, intent, restore, and strategy layers while preserving the existing control behavior and test coverage.

## 0.5.0 - 2026-07-01

- Feed adaptive room power-fraction estimates into the thermal prediction and EKF learning path instead of using full-power active observations for every zone.

## 0.4.0 - 2026-06-28

- Fix Home Assistant forecast ingestion to treat naive forecast timestamps as HA-local time, preserve the HA timezone on forecast snapshots, and use the current outside temperature as a live interpolation anchor.
- Drop the bridge-prepended current-weather row from forecast samples when real timestamped forecast entries are present, avoiding duplicate/current-hour forecast distortion in MPC control inputs.

## 0.3.3 - 2026-06-28

- Refresh listed sensor-info records after startup and keep resolved RF sensor rows populated with zone temperature while RF battery/signal telemetry is warming up.

## 0.3.2 - 2026-06-28

- Resolve group-local RF sensor slots to concrete sensor addresses in `/api/state`, exposing one-to-one sensor owner fields and zone-side `sensor_id` metadata for Home Assistant device placement.

## 0.3.1 - 2026-06-28

- Expose explicit sensor-to-zone mapping fields in `/api/state` sensor rows so Home Assistant integrations can attach RF sensors to the correct zone without address heuristics.

## 0.2.8 - 2026-06-27

- Add time-aware adaptive forecast ingestion for Home Assistant-style timestamped forecasts, including sorted UTC alignment, 5-minute control grids, and quality metadata.
- Separate MPC input parameters into a structured input object so forecast, solar, humidity, and quality metadata can evolve without expanding the solver call signature.
- Expose adaptive runtime forecast diagnostics, including expected AC runtime over the MPC horizon, per-zone runtime, action windows, forecast series points, and solver timing metrics.
