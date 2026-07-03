# Svelte UI Plan

This is the active UI plan for the Svelte OpenAirTouch frontend. It keeps the useful adaptive UI intent from the older handoff document, but treats Svelte as the product surface and the shipped `0.7.x` add-on as the baseline.

## Product Language

Use natural control-room language. The UI should explain what adaptive thinks will happen, what it intends to do, and what it has already done without exposing implementation names as the primary experience.

Preferred phrases:

- `Nice Outside`
- `Outside Air Can Help`
- `AC Paused`
- `AC Resume Pending`
- `AC Resumed`
- `Waiting For Zones`
- `Recommended Target: 22°`
- `Expected Runtime: 1.5 h`
- `Fresh Air Recommended`
- `Fan And Outside Air Recommended`
- `Outside Air Recommended`
- `AirTouch Has Control`

Avoid primary labels like `MPC`, `Restore Ledger`, `Weather Strategy`, `Zone Strategy`, or `Hybrid Strategy`. Those can stay in diagnostics/debug surfaces.

## Current Svelte Baseline

- The Control hero has a compact temperature history/plan graph.
- The graph should remain simple: history, setpoint, plan, and AC call overlay.
- The UI already uses `°` for temperatures and `°/h` for model rates.
- Adaptive pages are split into `Status`, `Config`, and `Analytics`.
- Adaptive config owns `Control Zones` and `Outside Air Zones`.
- Favourites, programs, adaptive, and settings filter by selected AC / zone group.
- The Svelte app must remain Home Assistant ingress-safe: no absolute `/api`, `/ws`, `/assets`, or `/ui` browser paths.

## Settings Classification

Keep AirTouch controller settings separate from OpenAirTouch/Svelte-only behaviour.

Original APK reference:

- Decoded APK research lives at `C:\Users\espar\OneDrive\Documents\Airtouch-Temperature-Bridge\research\from-airtouch-decoding\research`.
- AirTouch 4 installer UI evidence is under `apk-decompile-full\jadx\sources\com\auto\aircondition\base\p001ui` and `apk-decompile-full\jadx\resources\res\layout`.
- AirTouch 5 installer UI evidence is under `apk-airtouch5-tab-v1.3.1\jadx\sources\au\com\polyaire\airtouch5\console\ui\settingpage\installer`.

AirTouch controller commands:

- `preference`: system name, AC error display, outside temperature display, control sensor display, Fahrenheit, touchpad location, screensaver settings.
- `service`: installer company, service phone, service due visibility/lock, filter clean due, maintenance due, service interval counters.
- `parameters`: group count, damper RPM, touchpad locations, AC button block, outside temperature display, lock to temp control, control sensor display.
- `grouping`, `spill`, `balance`, `ac_base_info`, `ac_setting_new`, `turbo_group`, `favourite`, `program_define_new`, `ac_timer_table`, `pair_sensor`, and `sensor_temperature` all write AirTouch state.

OpenAirTouch/Svelte-only behaviour:

- Theme selection.
- Show Support Diagnostics.
- Support table rendering and local event buffering.
- Adaptive configuration is OpenAirTouch behaviour, not native AirTouch controller configuration.

Page placement:

- `App` should contain OpenAirTouch/Svelte-only display behaviour and only the AirTouch preferences that were genuinely user-facing on the original UI.
- `Service` owns the AirTouch `service` command and should read as installer/service contact plus service reminder state.
- `General` owns AirTouch installation parameters and should be treated as installer/admin configuration, not daily user preferences.
- When a field appears in both `preference` and `parameters`, verify the original APK placement before duplicating it in Svelte.

Original APK installer split:

- AirTouch 4 System Settings top tabs: Date/Time, Sensors, Turbo Group, Group Name, Preferences, Installers. The `Installers` tab is password gated.
- AirTouch 4 installer sub-tabs: General, Balance, Grouping, Spill, Sensors, Service, AC Setup, System.
- AirTouch 4 `General` (`ParametersFragment` / `layout_sysset_install_parameters.xml`) exposes installer password, touchpad group assignment, display control sensor temp, lock groups to temp control, total groups, touchpad address, damper RPM, optional Zimi control, save/recover settings, and reset to factory.
- AirTouch 4 `Service` (`ServiceFragment` / `layout_sysset_install_service.xml`) exposes half-year/one-year/two-years service interval choices, installer name, phone number, display days, running days, pay lock, client number, and client logo.
- AirTouch 4 `System` (`SystemInfoFragment` / `layout_sysset_install_version.xml`) is read-only system/version info: console version(s), main module firmware, hardware version, boot version, and gateway update entry when supported.
- AirTouch 5 has a similar installer split but labels it more directly: `InstallerGeneralPage` owns total zones, installer password, lock zones to temp control, console role/address, and reset/manual functions; `InstallerServicePage` owns service/reminder contact style fields; `InstallerInfoPage` is read-only info for system ID, console, main module, extension module, and gateways.

## Settings Field Audit

Goal: preserve AirTouch configuration parity, move touchpad/app-only behaviour into `App`, and keep read-only APK fields read-only in Svelte.

Status terms:

- `Writable`: backed by an OpenAirTouch command and expected to modify AirTouch controller/main-module state.
- `Touchpad/App`: affects console/app/frontend behaviour, not normal aircon control state.
- `Read-only`: should display as information only unless APK evidence shows an edit path.
- `Unproven`: command support exists in OpenAirTouch, but original APK placement/visibility still needs confirmation.

Current Svelte field audit:

| Current page | Field/surface | Current command | APK evidence | Status | Recommended placement |
| --- | --- | --- | --- | --- | --- |
| App | Theme | Svelte local state | Not native AirTouch | Touchpad/App | App / Appearance |
| App | Show Support Diagnostics | Svelte local state | Not native AirTouch | Touchpad/App | App / Support toggle |
| App | Runtime metric tiles | None | System/version style fields are info-only | Read-only | App or System Info, display-only |
| App | System Name | `preference` | AT4 Preferences has `Owners Name`; AT5 has `System Name` string | Writable, user-facing | App / Display |
| App | Show AC Errors | `preference` | Not found on AT4 Preferences/Installer pages in current APK pass | Writable, Unproven | Keep available but mark for APK confirmation |
| App | Show Outside Temp | `preference` | AT4 string exists; exact page not confirmed | Writable, Unproven | App if display-only, otherwise General if controller parameter |
| App | Show Control Sensor | `preference` | AT4 Installer General has `Display control sensor temp` via parameters-style path | Writable | Prefer General unless proven as user preference |
| App | Fahrenheit | `preference` | Not found in AT4 pass; likely display preference | Writable, Unproven | App / Display |
| App | Screensaver | `preference` | Touchpad/screen behaviour, not aircon behaviour | Touchpad/App, Writable | App |
| App | Screen Timeout | `preference` | Touchpad/screen behaviour, not aircon behaviour | Touchpad/App, Writable | App |
| App | Location | `preference` | Protocol field; original page meaning not confirmed | Writable, Unproven | Hold until decoded to friendly meaning |
| Sensors | Pairing start/stop | `pair_sensor` | AT4 Sensors page has Scan/Stop Scan | Writable | Sensors |
| Sensors | Sensor address/temp/mapped groups | None | Sensor lists are informational | Read-only | Sensors display-only |
| Sensors | Revise Sensor Temperature | `sensor_temperature` | AT4 User Sensor Info can set sensor temp | Writable | Sensors, but show raw/decoded diagnostics later |
| Grouping | Group name | `group_name` | AT4 Group Name / Installer Grouping | Writable | Grouping |
| Grouping | First Damper, Damper Count, Min Open, Sensor | `grouping` | AT4 Installer Grouping | Writable | Grouping |
| Grouping | Status/min/sensor summary pills | None | Derived status/config summary | Read-only | Grouping display-only |
| Spill | Spill zones and AC spill mode | `spill` | AT4 Installer Spill | Writable | Spill |
| Balance | Balance start/stop, per-zone max opening | `balance_start`, `balance_stop` | AT4 Installer Balance | Writable | Balance |
| AC Setup | AC name, first zone, zone count, brand | `ac_base_info` | AT4 Installer AC Setup | Writable, but brand currently hidden | AC Setup |
| AC Setup | Cool/heat adjust, setpoint limits, auto off, time limit | `ac_setting_new` | AT4 Installer AC Detail Setting | Writable | AC Setup |
| AC Setup | Thermostat Byte | `ac_setting_new` | APK exposes friendly Control Sensor choices/help | Writable, poor UI | AC Setup with decoded selector, not byte |
| AC Setup | Show Spill | `ac_setting_new` | APK has hide spill group setting | Writable | AC Setup |
| AC Setup | Modes | `ac_setting_new` | APK AC detail supports mode availability | Writable | AC Setup |
| AC Setup | Fan Value Mapping | `ac_setting_new` | APK supports fan mapping/config, installer-level | Writable, advanced | AC Setup advanced |
| AC Setup | Selector Visibility and bitmaps | `ac_setting_new` | APK supports selector/control sensor choices, not raw bitmaps | Writable, poor UI | AC Setup advanced with friendly names |
| AC Setup | Turbo Zone | `turbo_group` | AT4 top-level Turbo Group plus installer AC setup context | Writable | Turbo Group or AC Setup, avoid duplication |
| General | Groups | `parameters` | AT4 Installer General `Total Groups`; AT5 Installer General `Total Zones` | Writable | Rename Parameters to General |
| General | Damper RPM | `parameters` | AT4 Installer General `Damper RPM` | Writable | General |
| General | Touchpad 1/2 Location | `parameters` | AT4 Installer General chooses current touchpad in group; AT5 has console address/role | Writable, poor UI | General, decoded as Touchpad/Console location |
| General | Block AC Button | `parameters` | Not confirmed in AT4 installer layout pass | Writable, Unproven | General advanced until APK placement confirmed |
| General | Outside Temp | `parameters` | Duplicates preference-like outside temp display | Writable, duplicate/unresolved | Hidden for now; preserve current value on save |
| General | Lock Temp Control | `parameters` | AT4 Installer General `Groups lock to temp control`; AT5 `Lock Zones to Temp Control` | Writable | General |
| General | Control Sensor | `parameters` | AT4 Installer General `Display control sensor temp` | Writable | General |
| Service | Company | `service` | AT4 Service `Installers`; AT5 service/contact style field | Writable | Service |
| Service | Phone | `service` | AT4 Service `Number`; AT5 `Phone` | Writable | Service |
| Service | Show/Lock Service Due, Filter Clean Due, Maintenance Due | `service` | Service/reminder concept exists; exact visible AT4 controls differ by interval/display days | Writable, partial parity | Service, but verify flags against live protocol |
| Service | Months, Days, Runtime Hours | `service` | AT4 Service has half/one/two-year, display days, running days | Writable, partial parity | Service, with friendlier reminder labels |
| Missing | Installer Password | Backend has `password_info` helper but Svelte does not expose installer password set | Writable in APK | Add only if we intend installer parity |
| Missing | Service interval presets | Not exposed directly | AT4 Service Half Year/One Year/Two Years | Writable in APK | Add/derive if protocol supports it |
| Missing | Display days / running days | Service payload may partially map days/runtime hours, but labels differ | AT4 Service visible fields | Writable in APK | Rename existing fields after protocol confirmation |
| Missing | Pay Lock | Not exposed | AT4 Service visible field | Writable in APK | Leave out unless protocol support is decoded and desired |
| Missing | Client number/logo | Not exposed | AT4 Service visible fields | Writable/app-service integration | Likely omit from OpenAirTouch unless protocol need appears |
| Missing | Save/recover settings, reset factory | Not exposed | AT4 Preferences and General | Writable/destructive | Do not add without explicit destructive-flow design |
| App | System Info | Runtime/state only | AT4 System and AT5 Installer Info are read-only | Read-only | Fold into App as compact read-only info |

Immediate placement corrections:

- Rename current `Installer Info` page to `Service`; it is not APK-style system info.
- Rename current `Parameters` page to `General`; it matches APK installer general/parameters behaviour.
- Fold read-only system info into `App` as a compact info group instead of adding another settings tab.
- Move or leave in `App` only fields that are genuinely app/touchpad display behaviour. `Theme`, `Show Support Diagnostics`, screensaver, screen timeout, Fahrenheit, and possibly system/display name belong here.
- Avoid duplicate display toggles until ownership is confirmed: `Show Outside Temp` and `Show Control Sensor` currently appear in both `preference` and `parameters` command paths.

## AC Hero Plan

The hero should show the active AC state first, then adaptive plan context without becoming a dense analytics panel.

Keep in hero:

- AC selector/name.
- Power, mode, and fan controls.
- Current active-zone aggregate room temperature.
- Zone-driven setpoint.
- Compact graph showing actual aggregate temperature and plan.
- AC call overlay when adaptive or thermal demand expects the AC to run.

Future hero text candidates:

- `AC Paused Until 3:30 PM`
- `Nice Outside: Open Windows`
- `Recommended Target: 22°`
- `Heating Expected`
- `Cooling Expected`
- `Dehumidification Recommended`
- `Fresh Air Recommended`
- `Waiting For Zones`

Do not put every forecast layer in the hero. Detailed forecast layers belong in Adaptive Analytics.

## Adaptive Status Surfaces

Keep the three-surface model:

- `Environment`: outdoor weather plus indoor air quality.
- `Zone`: room-level target and runtime intent.
- `Hybrid`: damper / airflow intent for heat-cool control only.

Environment should answer:

- Is outside air useful?
- Is the AC paused by weather?
- Is resume pending?
- Why is the recommendation being made?

Zone should answer:

- Which rooms are driving demand?
- What target is recommended?
- How long is the expected runtime?
- Are models ready or still learning?

Hybrid should answer:

- What zone airflow plan is proposed?
- Is AirTouch back in control?
- Is thermal mode active?

For Hybrid, keep thermal and air-quality previews visually separate:

- Heat/Cool can show `Recommended Target`, `Expected Runtime`, `Control Temperature`, and `Damper Plan`.
- Dry/Fan should show `Dehumidification Recommended` or `Fresh Air Recommended` with a direct zone plan only.
- Do not show `Damper Plan` or `Control Temperature` for Dry/Fan.

## Forecast And Plan Contract

The UI should consume backend forecast/plan data when present and fall back to UI-derived plan data only when needed.

Desired plan point fields:

- `timestamp`
- `offset_minutes`
- `average_indoor_temperature`
- `predicted_indoor_temperature`
- `target_temperature`
- `action`
- `power_fraction`
- `ac_running_predicted`
- `ac_running_observed`
- `control_temperature`
- `zone_temperatures`
- `zone_targets`
- `zone_runtime_fraction`

Useful action values:

- `idle`
- `heating`
- `cooling`
- `dry`
- `fan`
- `paused_by_weather`

Analytics can later add:

- Outdoor temperature forecast line.
- Predicted indoor temperature line.
- Target temperature dotted line.
- AC running/paused history.
- Cooling/heating demand shading.
- Weather pause window band.
- CO2 / ventilation marker or band.

## Restore And Ownership

Restore should be visible only when adaptive is unwinding its own temporary actuator changes.

Good user-facing strings:

- `Restoring Previous AC State`
- `Restored Mode: Cool`
- `Restored Target: 22°`
- `Zone Returned To Sensor Control`
- `AirTouch Has Control`

Ownership rules:

- Weather pause/resume is a strategy lifecycle, not restore.
- Restore is for temporary adaptive actuator changes.
- User or AirTouch changes should cancel ownership rather than be fought.
- Raw restore keys belong in diagnostics, not primary UI.

## Backlog

UI backlog:

- Replace placeholder Adaptive Analytics sparkline with real per-zone history / plan data.
- Make adaptive status copy more room-specific.
- Surface weather pause/resume lifecycle in the hero or adaptive status when active.
- Add clearer restore/ownership status only when adaptive is unwinding changes.
- Keep chart styling restrained and product-like.

Backend contract backlog:

- Expose consistent weather pause/resume lifecycle fields.
- Expose `nice_until` or equivalent time-window data.
- Add per-point forecast timestamps, not only offsets.
- Add observed AC running history from telemetry.
- Add zone-level predicted temperatures and targets.
- Add hybrid control temperature.
- Add outside-air actuator observed state and command result.
- Add clear ownership and cancel reasons.

## Svelte Refactor Workstream

Active rule: keep all implementation work in the Svelte worktree only. Do not commit or promote changes into root `main` while this workstream is active.

Verification rule: keep checking the work continuously against a running app. Prefer a live dev server or production build plus the Home Assistant ingress surface before treating UI work as done.

Now:

- [ ] Extract domain selectors from `App.svelte` into `src/lib/selectors.js`: AC selection, group filtering, thermostat selection, sensor rows, adaptive intent, chart paths, favourites/program bitmap helpers.
- [ ] Extract command and form payload builders from `App.svelte` into `src/lib/commands.js`: favourites, programs, timers, adaptive config, sensor calibration, grouping, spill, balance, AC setup, parameters, service.
- [ ] Add reusable form/control components for common controls: fields, toggles, number inputs, zone checkbox grids, action rows, timer editor patterns.
- [ ] Split `SettingsView.svelte` into focused subviews for app, sensors, grouping, spill, balance, AC setup, parameters, system, and diagnostics.

Return later:

- [ ] Improve AirTouch UX guardrails: hide byte-level fields behind advanced affordances and show decoded names for thermostat selectors, fan mappings, turbo groups, touchpad locations, and selector bitmaps.
- [ ] Add live raw/decoded temperature diagnostics for sensors, including `temperature_raw`, decoded temp, mapped group, and source kind side-by-side.
- [ ] Bring Favourites, Adaptive, and Settings up to the Control page polish level with fewer raw protocol labels and clearer save/apply states.
