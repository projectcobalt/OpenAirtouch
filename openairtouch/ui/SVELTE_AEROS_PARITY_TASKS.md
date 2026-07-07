# Svelte Aeros Parity Tasks

Goal: build the Svelte frontend as the active product UI while keeping the FastAPI service contract thin and unchanged.

Work boundary: all new UI implementation, parity alignment, and frontend cleanup must happen inside `C:\Users\espar\OneDrive\Documents\OpenAirTouch\.worktrees\svelte-frontend`. The Aeros UI worktree is reference-only and should not be merged now that Svelte is the active UI stack.

Current design direction: do not treat Aeros as the visual target unless explicitly requested for comparison. The Svelte UI should feel like its own AC touchpanel product. Prefer flat controls and telemetry sitting directly on their card/panel backgrounds; avoid adding translucent boxes, borders, tints, or highlighted wrappers around every label/select/readout. Add visual treatment only where it provides a clear interaction affordance or accessibility cue.

## Source Material

- The retired embedded FastAPI UI is historical reference only; the Svelte source and built `service/web` assets are the active UI.
- Svelte feature parity should be verified against Svelte source/tests and the backend API/WebSocket contract, not the removed embedded UI.
- `openairtouch/docs/adaptive-control-flow.md` in the adaptive worktree defines adaptive mode/strategy behavior.
- `openairtouch/docs/adaptive-ui-surface.md` in the sensor-zone-mapping worktree defines adaptive copy, chart layers, ownership language, and structured fields.

## Parity Checklist

### Frontend Architecture

- [x] Split shared formatting, API client, AC mode labels, mode palettes, and layout tokens out of `App.svelte`.
- [x] Componentize the persistent shell, room panel, AC hero, metric cards, subnavs, and zone cards.
- [x] Extract the Control view into a composed Svelte view component.
- [x] Extract the Favourites/Programs, Adaptive, and Settings page bodies into Svelte view components.
- [x] Keep mode asset and palette changes as app-level reactive CSS variables.
- [x] Keep the fixed touchpanel layout dimensions tokenized for later visual tuning.
- [x] Use Lucide Svelte through semantic wrappers for app icons.
- [ ] Extract smaller repeated editor/card components inside the large views as visual parity stabilizes.

### Control View

- [x] Serve Svelte build from FastAPI root and `/ui` assets.
- [x] Websocket live state with slow polling fallback.
- [x] Mode-aware sidebar asset and palette switching.
- [x] AC selector and current AC state hydration.
- [x] Mode and fan selectors wired to `ac_status`.
- [x] Composite Aeros-style hero grid: primary controller, active zones, indoor, faults, damper summary.
- [x] Equal-width/equal-height zone cards with state-bound controls.
- [x] Zone paging support.
- [x] Restore Aeros hero setpoint/current split and temperature history strip.
- [x] Restore AC detail card content: runtime, source hints, spill pills.
- [x] Replace text placeholders like `R` with icon buttons/tooltips.
- [x] Add service filter/reminder fields where current backend state exposes them.
- [x] Verify desktop control alignment against Aeros sizing rules without issuing live commands.
- [ ] Verify tablet/mobile alignment against Aeros breakpoints.

### Favourites And Programs

- [x] Favourites subnav: Favourites / Programs / AC Timer.
- [x] Favourite cards with editable names, zone check rows, apply/save/clear actions.
- [x] Program cards with name/enabled/day/zone/AC/timer/setpoint controls.
- [x] AC timer cards with on/off timer controls.
- [ ] Preserve debug program option/summary payloads outside primary navigation.

### Adaptive

- [x] Adaptive subnav: Status / Config / Analytics.
- [x] Status cards: Authority, Learning, Control, Compressor, Live Inputs.
- [x] User language from `adaptive-ui-surface.md`: intent, reason, expected runtime, ownership.
- [x] Config controls: mode, strategy, thresholds, control zones, outside-air zones, compressor guards.
- [x] Model actions: reset all, accelerate zone, reset zone.
- [x] Analytics rows with history/forecast sparkline, readiness state, model badges.
- [x] Separate Environment, Zone, and Hybrid copy/visual treatment.
- [ ] Surface restore ownership and weather pause/resume lifecycle when available.

### Service / Settings

- [x] Service subnav: App / Sensors / Grouping / Spill / Balance / AC Setup / Parameters / System Info / Diagnostics.
- [x] App Appearance theme selector, preferences, and runtime cards.
- [x] Sensor rows with mapping, status, calibration slider, pair controls.
- [x] Grouping edit cards with sensor/min/zone fields.
- [x] Spill zone and AC spill mode cards with APK labels: None / Spill / Bypass.
- [x] Balance mode rows with max-opening steppers and start/stop commands.
- [x] AC setup cards: base info, settings, modes, fan mapping, selector masks, turbo group.
- [x] Parameters forms.
- [x] Diagnostics/runtime/system debug cards.
- [x] Add service reminder forms if current backend state exposes the reminder payload.
- [x] Add dedicated System Info subnav if it still proves useful beyond Diagnostics.

### Tests And Build

- [ ] Add Svelte/static parity tests that assert critical fragments in `App.svelte` and built `web/index.html`.
- [x] Keep generated assets tracked under `openairtouch/src/airtouch4/service/web`.
- [x] `python -m unittest discover -s openairtouch/tests` passes.
- [x] `pnpm run build` passes without Svelte warnings.
- [x] Browser smoke: control view, adaptive view, service view, System Info page, no console errors.

## Current Pass

- Latest pass removed the non-Aeros thermostat hero, restored the Aeros setpoint/current split, added the App Appearance System/Light/Dark selector, and kept service filter/reminder fields visible.
- Clean Aeros viewport references were captured under `C:\Users\espar\OneDrive\Documents\OpenAirTouch\aeros-reference-screenshots\2026-07-02-clean-viewport`.
- Screenshot comparison shows the remaining gap is mainly visual and structural rather than endpoint coverage: Svelte has most controls, but needs to converge on the exact Aeros product language before deeper adaptive/mobile work.
- Next focus:
  - Rebuild the Svelte top shell to match Aeros: brand row, centered pill navigation, isolated settings icon, thinner header divider, and no extra visible "Settings" text button.
  - Bring the left room panel back to Aeros proportions: taller fixed image panel, warm translucent overlay, large room typography, pill sensor label, compact indoor/outdoor/humidity rows, and top/bottom alignment with the control grid.
  - Retune the Control view cards: primary hero should use the same large setpoint/current hierarchy, orange circular power button placement, subtle history strip, and compact mode/fan pill row; metric cards should match Aeros sizing and typography.
  - Rework zone cards to Aeros density: two-column grid, circular zone power affordance, uppercase zone number, name/sensor/set/damper columns, compact damper bar, and less form-like styling.
  - Re-style subnavs: Service uses large oval/capsule tabs with the active App tab as a tall orange pill; other subnavs use the same rounded dark capsule treatment.
  - Re-style Service pages to match Aeros panels: one large bordered surface per page, nested cards only where Aeros uses them, uppercase field labels, darker translucent inputs, orange save pills, and tighter spacing.
  - Preserve the newly restored functional surfaces while doing visual parity: theme selector, filter/service reminder fields, AC setup mode/fan selectors, spill/bypass labels, and adaptive model actions.
  - After desktop visual parity, run tablet/mobile screenshot checks against the same reference pages and only then resume adaptive markdown enhancements.

## Consolidated Execution Plan

Target worktree: `C:\Users\espar\OneDrive\Documents\OpenAirTouch\.worktrees\svelte-frontend`.

The Aeros worktree is now reference-only. New UI implementation work should happen in Svelte source under `openairtouch/ui/src/App.svelte`, then be built into `openairtouch/src/airtouch4/service/web`.

### Local Service Launch

Use the Svelte worktree as the working directory. The reliable local validation path is to run the launcher in a foreground terminal:

```powershell
cd C:\Users\espar\OneDrive\Documents\OpenAirTouch\.worktrees\svelte-frontend
.\openairtouch\scripts\local_service.ps1 -Action run
```

For Codex/background validation while continuing to work:

```powershell
.\openairtouch\scripts\local_service.ps1 -Action run -Background -StopExisting
```

Before starting the service, verify port `8099` and stop any stale local listener:

```powershell
.\openairtouch\scripts\local_service.ps1 -Action status
.\openairtouch\scripts\local_service.ps1 -Action stop
```

After starting, verify `http://127.0.0.1:8099/api/health`, `http://127.0.0.1:8099/api/state`, `/api/events`, and `/ws`. If room temperatures still show whole numbers after decoder changes, restart this local service first; the running Python process keeps the old decoder until it is replaced. Avoid treating a Svelte asset rebuild as a service restart.

The launcher defaults to `--transport tcp_serial --tcp-host 192.168.30.56 --tcp-port 6638 --host 127.0.0.1 --http-port 8099 --protocol auto`. Use `-StopExisting` with `-Action run` only when replacing a known stale local listener. Background launches write `.codex-runlogs/local-service.log`.

### Phase 1: Desktop Visual Parity

- [ ] Top shell: match Aeros brand/header/navigation/settings structure.
- [ ] Room panel: match Aeros image treatment, typography, status rows, and panel dimensions.
- [ ] Control hero: match Aeros hero sizing, setpoint/current hierarchy, history strip, power/all-off placement, and mode/fan pills.
- [ ] Metric cards: match Aeros card sizing, copy hierarchy, damper bar, and spacing.
- [ ] Zone cards: match Aeros compact two-column product layout and remove form-like visual weight.

### Phase 2: Service Surface Parity

- [ ] Service subnav: match Aeros oval capsule rail and active tall orange pill.
- [ ] Service App: match Aeros Appearance/Display card composition and input styling.
- [ ] Service lower pages: match Sensors, Grouping, Spill, Balance, AC Setup, Parameters, System Info, and Diagnostics panel density.
- [ ] Preserve functional controls while restyling: theme selector, service reminders, AC mode/fan selector masks, spill/bypass labels, sensor mapping, and adaptive actions.

### Phase 3: Responsive And Regression Pass

- [ ] Rebuild Svelte assets with `pnpm run build`.
- [ ] Run `python -m unittest discover -s openairtouch/tests`.
- [ ] Capture desktop Svelte screenshots for the same 16 Aeros reference pages.
- [ ] Compare tablet/mobile breakpoints after desktop parity is close.
- [ ] Add static parity tests for critical Svelte fragments and built web index.
