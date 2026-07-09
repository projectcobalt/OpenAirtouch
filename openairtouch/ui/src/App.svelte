<script>
  import { onDestroy, onMount } from "svelte";
  import Shell from "./components/Shell.svelte";
  import RoomPanel from "./components/RoomPanel.svelte";
  import Subnav from "./components/Subnav.svelte";
  import ViewHeading from "./components/ViewHeading.svelte";
  import ConfirmDialog from "./components/ConfirmDialog.svelte";
  import ControlView from "./views/ControlView.svelte";
  import AdaptiveView from "./views/AdaptiveView.svelte";
  import FavouritesView from "./views/FavouritesView.svelte";
  import SettingsView from "./views/SettingsView.svelte";
  import { MODE_OPTIONS, fanName, modeKey, modeName } from "./lib/openairtouch.js";
  import {
    acBasePayload,
    acSettingsPayload,
    acTimerPayload,
    adaptiveConfigPayload,
    balanceValuesFromPage as buildBalanceValuesFromPage,
    checkedValues as buildCheckedValues,
    clearFavouritePayload,
    clearProgramPayload,
    favouritePayload,
    groupNamePayload,
    groupingPayload,
    parametersPayload,
    preferencePayload,
    programPayload,
    runtimeConfigPayload,
    sensorTemperaturePayload,
    servicePayload,
    spillPayload,
    stepBalanceInput,
    timerFromCard as buildTimerFromCard,
    turboGroupPayload,
    zonePayload as buildZonePayload
  } from "./lib/commands.js";
  import { apiPath, fetchJson, postCommand, wsPath } from "./lib/client.js";
  import { clamp, finite, title } from "./lib/format.js";
  import {
    acName as selectAcName,
    activeZoneEntriesForAc as selectActiveZoneEntriesForAc,
    average as selectAverage,
    configuredAcEntries as selectConfiguredAcEntries,
    configuredFans as selectConfiguredFans,
    configuredModes as selectConfiguredModes,
    firstSensorName as selectFirstSensorName,
    groupBadges as selectGroupBadges,
    groupEntriesForAc as selectGroupEntriesForAc,
    groupIsConfigured as selectGroupIsConfigured,
    groupIsOn as selectGroupIsOn,
    groupIsSpill as selectGroupIsSpill,
    groupsFromBitmap as selectGroupsFromBitmap,
    mainDisplayRoomName as selectMainDisplayRoomName,
    resolveTemperatureState as selectResolveTemperatureState,
    sensorKindLabel as selectSensorKindLabel,
    sensorRowsFromState as selectSensorRowsFromState,
    splitGroupBitmap as selectSplitGroupBitmap,
    temperatureChart as selectTemperatureChart,
    thermostatFor as selectThermostatFor,
    zoneName as selectZoneName,
    zoneRoomTemperature as selectZoneRoomTemperature
  } from "./lib/selectors.js";
  import { modeStyleFor } from "./lib/tokens.js";

  let health = null;
  let snapshot = null;
  let error = "";
  let socketState = "offline";
  let pendingKey = "";
  let selectedAcId = 0;
  let activeView = "control";
  let activeProgramView = "favourites";
  let activeAdaptiveView = "status";
  let activeServiceView = "app";
  let balanceWasVisible = false;
  let selectedTheme = "system";
  let showSupportDiagnostics = false;
  let busEvents = [];
  let confirmDialog = null;
  let socket = null;
  let reconnectTimer = null;
  let pollTimer = null;
  let themeMediaQuery = null;
  let themeMediaHandler = null;
  const STORAGE_KEYS = {
    theme: "openairtouch.uiTheme",
    diagnostics: "openairtouch.showSupportDiagnostics"
  };

  const PROGRAM_VIEWS = [["favourites", "Favourites"], ["programs", "Programs"], ["timers", "AC Timer"]];
  const ADAPTIVE_VIEWS = [["status", "Status"], ["config", "Config"], ["analytics", "Analytics"]];
  const BASE_SERVICE_VIEWS = [["app", "App"], ["sensors", "Sensors"], ["grouping", "Grouping"], ["balance", "Balance"], ["ac-setup", "AC Setup"], ["service", "Service"]];
  const SUPPORT_SERVICE_VIEW = ["diagnostics", "Support"];

  async function load() {
    error = "";
    try {
      const [healthPayload, statePayload, eventsPayload] = await Promise.all([
        fetchJson("health"),
        fetchJson("state"),
        fetchJson("events").catch(() => ({events: []}))
      ]);
      health = healthPayload;
      snapshot = statePayload;
      if (Array.isArray(eventsPayload.events)) busEvents = eventsPayload.events.slice(-200);
      keepSelectedAcValid();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    }
  }

  function setBusEvents(events) {
    busEvents = Array.isArray(events) ? events.slice(-200) : [];
  }

  function appendBusEvents(events) {
    if (!Array.isArray(events) || !events.length) return;
    busEvents = [...busEvents, ...events].slice(-200);
  }

  function connectSocket() {
    if (socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(socket.readyState)) return;
    try {
      socket = new WebSocket(wsPath());
      socketState = "connecting";
    } catch (err) {
      socketState = "offline";
      error = err instanceof Error ? err.message : String(err);
      scheduleReconnect();
      return;
    }

    socket.addEventListener("open", () => {
      socketState = "live";
    });
    socket.addEventListener("message", (event) => {
      try {
        const message = JSON.parse(event.data);
        if ((message.type === "hello" || message.type === "state") && Array.isArray(message.events)) {
          setBusEvents(message.events);
        } else if (message.type === "events" && Array.isArray(message.events)) {
          appendBusEvents(message.events);
        } else if (message.type === "event" && message.event) {
          appendBusEvents([message.event]);
        }
        if (message.health) health = message.health;
        if (message.state) {
          snapshot = message.state;
          keepSelectedAcValid();
        }
      } catch (err) {
        error = err instanceof Error ? err.message : String(err);
      }
    });
    socket.addEventListener("close", () => {
      socketState = "offline";
      scheduleReconnect();
    });
    socket.addEventListener("error", () => {
      socketState = "offline";
    });
  }

  function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectSocket, 1500);
  }

  async function sendCommand(action, data, key = action) {
    pendingKey = key;
    error = "";
    try {
      await postCommand(action, data);
      setTimeout(load, 350);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      setTimeout(() => {
        pendingKey = "";
      }, 650);
    }
  }

  function configuredModes(settings) {
    return selectConfiguredModes(settings);
  }

  function confirmAction(options = {}) {
    return new Promise((resolve) => {
      confirmDialog = {...options, resolve};
    });
  }

  function resolveConfirmDialog(confirmed) {
    const activeDialog = confirmDialog;
    confirmDialog = null;
    activeDialog?.resolve?.(confirmed);
  }

  function configuredFans(settings) {
    return selectConfiguredFans(settings);
  }

  function acName(id, ac) {
    return selectAcName(id, ac);
  }

  function configuredAcEntries(entries) {
    return selectConfiguredAcEntries(entries, system);
  }

  function groupIsConfigured(group) {
    return selectGroupIsConfigured(group);
  }

  function groupIsSpill(group) {
    return selectGroupIsSpill(group);
  }

  function groupIsOn(group) {
    return selectGroupIsOn(group);
  }

  function groupBadges(group) {
    return selectGroupBadges(group);
  }

  function zoneName(id, group) {
    return selectZoneName(id, group);
  }

  function groupEntriesForAc(ac, {includeSpill = false} = {}) {
    return selectGroupEntriesForAc(ac, groupEntries, {includeSpill});
  }

  function activeZoneEntriesForAc(ac) {
    return selectActiveZoneEntriesForAc(ac, groupEntries);
  }

  function average(values) {
    return selectAverage(values);
  }

  function firstFinite(...values) {
    for (const value of values) {
      const numeric = finite(value);
      if (numeric !== null) return numeric;
    }
    return null;
  }

  function sensorViewRows() {
    return Array.isArray(rootState.sensor_view) ? rootState.sensor_view : [];
  }

  function zoneRoomTemperature(id, group) {
    return selectZoneRoomTemperature(id, group);
  }

  function firstSensorName(zones) {
    return selectFirstSensorName(zones);
  }

  function mainDisplayRoomName(ac, acId, zones) {
    return selectMainDisplayRoomName(system, ac, acId, zones);
  }

  function thermostatFor(ac, zones) {
    return selectThermostatFor(ac, zones, integrations);
  }

  function resolveTemperatureState(ac, acId, zones) {
    return selectResolveTemperatureState({system, ac, acId, zones, integrations});
  }

  function acSourceHint(ac, zones, thermostat) {
    const settings = ac?.settings || {};
    const selector = finite(settings.ctrl_thermostat);
    const activeSensorZones = zones.filter(([_id, group]) => {
      const status = group?.status || {};
      return groupIsOn(group) && status.has_sensor === true;
    });
    if (selector !== null && selector !== 255) return `Thermostat selector ${selector}`;
    if (activeSensorZones.length > 1) return `${activeSensorZones.length} active room sensors averaged`;
    if (activeSensorZones.length === 1) return `${zoneName(activeSensorZones[0][0], activeSensorZones[0][1])} sensor`;
    return thermostat.current === null ? "No live room sensor" : "Current room temperature";
  }

  function aggregateTemperatureHistory(zones, thermostat) {
    const activeZones = zones.filter(([_id, group]) => groupIsOn(group));
    const buckets = new Map();
    for (const [_id, group] of activeZones) {
      for (const entry of Array.isArray(group?.temperature_history) ? group.temperature_history : []) {
        const temperature = finite(entry?.temperature);
        const ts = finite(entry?.ts);
        if (temperature === null || ts === null) continue;
        const bucket = Math.floor(ts / 60) * 60;
        const item = buckets.get(bucket) || {ts: bucket, total: 0, count: 0};
        item.total += temperature;
        item.count += 1;
        buckets.set(bucket, item);
      }
    }
    const entries = [...buckets.values()]
      .filter((item) => item.count > 0)
      .map((item) => ({ts: item.ts, temperature: item.total / item.count, zone_count: item.count}))
      .sort((a, b) => a.ts - b.ts)
      .slice(-18);
    if (!entries.length) {
      const current = finite(thermostat?.current);
      if (current !== null && activeZones.length) {
        entries.push({ts: Math.floor(Date.now() / 1000), temperature: current, zone_count: activeZones.length});
      }
    }
    return entries;
  }

  function thermalCallActive(current, setpoint, status) {
    const mode = modeKey(status?.mode);
    const tolerance = 0.15;
    if (mode === "fan" || current === null || setpoint === null || status?.power_on !== true) return false;
    if (mode === "cool" || mode === "dry") return current > setpoint + tolerance;
    if (mode === "heat") return current < setpoint - tolerance;
    return Math.abs(setpoint - current) > tolerance;
  }

  function plannedTemperatureEntries(historyEntries, thermostat, status, activeZoneCount) {
    const setpoint = finite(thermostat?.setpoint);
    const current = finite(historyEntries.at(-1)?.temperature) ?? finite(thermostat?.current);
    if (setpoint === null || current === null || !activeZoneCount || status?.power_on !== true || modeKey(status?.mode) === "fan") return [];
    const delta = setpoint - current;
    const startTs = finite(historyEntries.at(-1)?.ts) ?? Math.floor(Date.now() / 1000);
    return Array.from({length: 6}, (_item, index) => {
      const progress = (index + 1) / 6;
      const eased = 1 - ((1 - progress) ** 2);
      return {
        ts: startTs + ((index + 1) * 300),
        temperature: current + (delta * eased),
        planned: true
      };
    });
  }

  function planActionActive(entry) {
    const action = String(entry?.action || "").toLowerCase();
    const power = finite(entry?.power_fraction);
    return (action && !["idle", "off", "none", "0"].includes(action)) || (power !== null && power > 0.01);
  }

  function runtimeForecastPlan(adaptiveState, acId) {
    const plans = adaptiveState?.learning?.plans || adaptiveState?.plans || {};
    const plan = plans?.[String(acId)] || plans?.[Number(acId)];
    const series = plan?.runtime_forecast?.series;
    if (!Array.isArray(series) || !series.length) return null;
    const entries = series
      .map((point) => {
        const temperature = firstFinite(point.average_indoor_temperature, point.control_temperature, point.temperature);
        if (temperature === null) return null;
        return {
          offset_minutes: finite(point.offset_minutes),
          temperature,
          setpoint: finite(point.target ?? plan.target),
          action: point.action,
          power_fraction: finite(point.power_fraction),
          source: "runtime"
        };
      })
      .filter(Boolean);
    if (!entries.length) return null;
    return {
      entries,
      setpoint: firstFinite(entries[0]?.setpoint, plan.target),
      callActive: entries.some(planActionActive),
      label: "Runtime plan"
    };
  }

  function zoneForecastPlan(adaptiveState, zones) {
    const forecasts = adaptiveState?.learning?.forecasts || adaptiveState?.forecasts || {};
    const activeIds = zones.filter(([_id, group]) => groupIsOn(group)).map(([id]) => String(id));
    if (!activeIds.length) return null;
    const buckets = new Map();
    for (const id of activeIds) {
      const points = forecasts?.[id] || forecasts?.[Number(id)];
      if (!Array.isArray(points)) continue;
      for (const point of points) {
        const temperature = finite(point?.temperature ?? point?.predicted_temperature ?? point?.prediction);
        if (temperature === null) continue;
        const offset = finite(point?.offset_minutes) ?? (buckets.size + 1) * 5;
        const bucket = buckets.get(offset) || {offset_minutes: offset, total: 0, count: 0, callActive: false};
        bucket.total += temperature;
        bucket.count += 1;
        bucket.callActive = bucket.callActive || planActionActive(point);
        buckets.set(offset, bucket);
      }
    }
    const entries = [...buckets.values()]
      .filter((bucket) => bucket.count > 0)
      .sort((a, b) => a.offset_minutes - b.offset_minutes)
      .map((bucket) => ({
        offset_minutes: bucket.offset_minutes,
        temperature: bucket.total / bucket.count,
        action: bucket.callActive ? "planned" : "idle",
        power_fraction: bucket.callActive ? 1 : 0,
        source: "zone"
      }));
    if (!entries.length) return null;
    return {
      entries,
      setpoint: null,
      callActive: entries.some(planActionActive),
      label: "Zone plan"
    };
  }

  function availableTemperaturePlan(adaptiveState, acId, zones) {
    return runtimeForecastPlan(adaptiveState, acId) || zoneForecastPlan(adaptiveState, zones);
  }

  function temperatureChartPath(entries, domain, offset = 0, total = entries.length) {
    if (!entries.length) return "";
    const span = Math.max(1, domain.max - domain.min);
    const denominator = Math.max(1, total - 1);
    return entries.map((entry, index) => {
      const x = total === 1 ? 120 : ((index + offset) / denominator) * 120;
      const y = 24 - ((Number(entry.temperature) - domain.min) / span) * 18;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ");
  }

  function temperatureChart(zones, thermostat, status, adaptiveState, acId) {
    return selectTemperatureChart(zones, thermostat, status, adaptiveState, acId);
  }

  function keepSelectedAcValid() {
    if (!acEntries.some(([id]) => Number(id) === Number(selectedAcId))) {
      selectedAcId = Number(acEntries[0]?.[0] || 0);
    }
  }

  function collectAlerts() {
    const alerts = [];
    const controller = snapshot?.controller || {};
    const integrations = snapshot?.integrations || {};
    const transactions = snapshot?.runtime?.transactions || {};
    if (controller.error) alerts.push(`Controller: ${controller.error}`);
    if (controller.status && !["running", "starting", "stopped"].includes(String(controller.status).toLowerCase()) && !controller.error) {
      alerts.push(`Service: ${title(controller.status)}`);
    }
    if (transactions.failed?.length) alerts.push(`${transactions.failed.length} failed transactions`);
    for (const [id, ac] of acEntries) {
      const status = ac?.status || {};
      if (status.error_code && status.error_code !== 0) alerts.push(`${acName(id, ac)} fault ${status.error_code}`);
    }
    for (const item of integrations.adaptive?.errors || []) alerts.push(`Adaptive: ${item}`);
    return alerts;
  }

  function favouriteName(id, favourite) {
    return favourite?.name || `Favourite ${Number(id) + 1}`;
  }

  function favouriteGroups(favourite) {
    if (Array.isArray(favourite?.groups)) return favourite.groups;
    const bitmapGroups = groupsFromBitmap(favourite?.groups_1_8_bitmap || 0, favourite?.groups_9_16_bitmap || 0);
    if (bitmapGroups.length) return bitmapGroups;
    const groupIds = [];
    for (const key of ["groups", "zones", "active_groups"]) {
      if (Array.isArray(favourite?.[key])) groupIds.push(...favourite[key]);
    }
    return [...new Set(groupIds.map(Number).filter(Number.isFinite))];
  }

  function groupsFromBitmap(low = 0, high = 0) {
    return selectGroupsFromBitmap(low, high);
  }

  function bitmapFromGroups(groupIds) {
    return groupIds.reduce((mask, group) => mask | (1 << Number(group)), 0);
  }

  function splitGroupBitmap(groupIds) {
    return selectSplitGroupBitmap(groupIds);
  }

  function checkedValues(card, selector) {
    return buildCheckedValues(card, selector);
  }

  function timeText(timer = {}) {
    if (!timer?.enabled) return "Off";
    const hour = String(timer.hour ?? 0).padStart(2, "0");
    const minute = String(timer.minute ?? 0).padStart(2, "0");
    return `${hour}:${minute}`;
  }

  function timeValue(timer = {}) {
    const hour = String(timer.hour ?? 0).padStart(2, "0");
    const minute = String(timer.minute ?? 0).padStart(2, "0");
    return `${hour}:${minute}`;
  }

  function timerFromCard(card, prefix) {
    return buildTimerFromCard(card, prefix);
  }

  function programRecordsFromState() {
    return Object.entries(programs || {})
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([id, program]) => ({
        ...program,
        program: Number(program.program ?? id),
        enabled: !!program.enabled,
        days_bitmap: Number(program.days_bitmap ?? 0),
        groups_1_8_bitmap: Number(program.groups_1_8_bitmap ?? 0),
        groups_9_16_bitmap: Number(program.groups_9_16_bitmap ?? 0),
        active_ac_bitmap: Number(program.active_ac_bitmap ?? 0),
        on_setpoint: Number(program.on_setpoint ?? 26),
        on_timer: program.on_timer || {enabled: false, hour: 0, minute: 0},
        off_timer: program.off_timer || {enabled: false, hour: 0, minute: 0}
      }));
  }

  function acTimerRecordsFromState() {
    return acEntries.map(([id, ac]) => {
      const timer = ac?.timer || {};
      return {
        ac: Number(id),
        on_timer: timer.on_timer || timer.timer || {enabled: false, hour: 0, minute: 0},
        off_timer: timer.off_timer || {enabled: false, hour: 0, minute: 0}
      };
    });
  }

  function saveFavourite(event, id) {
    const card = event.currentTarget.closest("[data-favourite-card]");
    sendCommand("favourite", favouritePayload(card, id), `favourite-save-${id}`);
  }

  function clearFavourite(id) {
    sendCommand("favourite", clearFavouritePayload(id), `favourite-clear-${id}`);
  }

  function applyFavourite(id) {
    sendCommand("active_favourite", {favourite: Number(id)}, `favourite-apply-${id}`);
  }

  function saveProgram(event, id) {
    const card = event.currentTarget.closest("[data-program]");
    sendCommand("program_define_new", programPayload(card, id, programs, system), `program-save-${id}`);
  }

  function clearProgram(id) {
    sendCommand("program_define_new", clearProgramPayload(id, programs, system), `program-clear-${id}`);
  }

  function saveAcTimer(event, id) {
    const card = event.currentTarget.closest("[data-ac-timer]");
    sendCommand("ac_timer_table", acTimerPayload(card, id, acEntries), `ac-timer-${id}`);
  }

  async function sendAdaptiveConfig(event) {
    const card = event.currentTarget.closest("[data-adaptive-config]");
    const payload = adaptiveConfigPayload(card);
    pendingKey = "adaptive-save";
    error = "";
    try {
      const response = await fetch(apiPath("adaptive"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Adaptive update failed: ${response.status}`);
      }
      setTimeout(load, 350);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      setTimeout(() => {
        pendingKey = "";
      }, 650);
    }
  }

  async function sendAdaptiveModelAction(action, zone = undefined) {
    if (action === "reset_all" || action === "reset_zone") {
      const confirmed = await confirmAction({
        title: action === "reset_all" ? "Reset Adaptive Models" : "Reset Zone Model",
        message: action === "reset_all" ? "This clears all adaptive learning data and restarts model learning." : "This clears adaptive learning data for this zone and restarts model learning.",
        confirmLabel: "Reset"
      });
      if (!confirmed) return;
    }
    pendingKey = `adaptive-model-${action}-${zone ?? "all"}`;
    error = "";
    try {
      const response = await fetch(apiPath("adaptive/model"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({action, zone})
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Adaptive model update failed: ${response.status}`);
      }
      setTimeout(load, 350);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      setTimeout(() => {
        pendingKey = "";
      }, 650);
    }
  }

  function sensorRowsFromState() {
    return selectSensorRowsFromState({rootState, system, groupEntries});
  }

  function sensorKindLabel(kind) {
    return selectSensorKindLabel(kind);
  }

  function saveSensorTemperature(event, sensor) {
    const target = event?.currentTarget || event;
    const card = target?.matches?.("[data-sensor-row]") ? target : target?.closest?.("[data-sensor-row]");
    const payload = sensorTemperaturePayload(card, sensor);
    if (!payload) return;
    sendCommand("sensor_temperature", payload, `sensor-temperature-${sensor}`);
  }

  function pairSensor(pairing) {
    sendCommand("pair_sensor", {pairing}, `pair-sensor-${pairing}`);
  }

  function saveGrouping(event, id) {
    const card = event.currentTarget.closest("[data-service-group]");
    sendCommand("grouping", groupingPayload(card, id), `grouping-${id}`);
  }

  function saveGroupName(event, id) {
    const card = event.currentTarget.closest("[data-service-group]");
    sendCommand("group_name", groupNamePayload(card, id), `group-name-${id}`);
  }

  function saveSpill(event) {
    const card = event.currentTarget.closest("[data-spill-card]");
    sendCommand("spill", spillPayload(card), "spill");
  }

  function balanceValuesFromPage() {
    return buildBalanceValuesFromPage(document);
  }

  function balanceAction(action) {
    sendCommand(action, {current_values: balanceValuesFromPage()}, action);
  }

  function stepBalance(event, id, delta) {
    const card = event.currentTarget.closest("[data-balance-zone]");
    stepBalanceInput(card, delta);
  }

  function savePreference(event) {
    const card = event.currentTarget.closest("[data-preference-card]");
    sendCommand("preference", preferencePayload(card, system), "preference");
  }

  async function saveRuntimeConfig(event) {
    const card = event.currentTarget.closest("[data-runtime-config-card]");
    pendingKey = "runtime-config";
    error = "";
    try {
      const response = await fetch(apiPath("runtime"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(runtimeConfigPayload(card, controller))
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Runtime update failed: ${response.status}`);
      }
      setTimeout(load, 350);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      setTimeout(() => {
        pendingKey = "";
      }, 650);
    }
  }

  function saveParameters(event) {
    const card = event.currentTarget.closest("[data-parameters-card]");
    sendCommand("parameters", parametersPayload(card, system, groupEntries), "parameters");
  }

  function saveService(event) {
    const card = event.currentTarget.closest("[data-service-system]");
    sendCommand("service", servicePayload(card), "service");
  }

  function resetServiceCounter(event) {
    const card = event.currentTarget.closest("[data-service-system]");
    sendCommand("service", {...servicePayload(card), days: 0}, "service-counter-reset");
  }

  function applyThemePreference(theme = selectedTheme) {
    if (typeof document === "undefined") return;
    const requested = ["system", "light", "dark"].includes(theme) ? theme : "system";
    const systemDark = themeMediaQuery?.matches ?? window.matchMedia?.("(prefers-color-scheme: dark)")?.matches === true;
    document.body.dataset.themePreference = requested;
    document.body.dataset.theme = requested === "system" ? (systemDark ? "dark" : "light") : requested;
  }

  function setTheme(theme) {
    selectedTheme = ["system", "light", "dark"].includes(theme) ? theme : "system";
    localStorage.setItem(STORAGE_KEYS.theme, selectedTheme);
    applyThemePreference(selectedTheme);
  }

  function applyModeStyleToBody(styleText) {
    if (typeof document === "undefined" || !styleText) return;
    for (const declaration of styleText.split(";")) {
      const [name, ...valueParts] = declaration.split(":");
      const value = valueParts.join(":").trim();
      if (name?.trim().startsWith("--") && value) document.body.style.setProperty(name.trim(), value);
    }
  }

  function setShowSupportDiagnostics(value) {
    showSupportDiagnostics = !!value;
    localStorage.setItem(STORAGE_KEYS.diagnostics, showSupportDiagnostics ? "true" : "false");
    if (!showSupportDiagnostics && activeServiceView === "diagnostics") activeServiceView = "app";
  }

  function saveAcBase(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    const payload = acBasePayload(card, id, acEntries, system);
    if (!payload) return;
    sendCommand("ac_base_info", payload, `ac-base-${id}`);
  }

  function saveAcSettings(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    const payload = acSettingsPayload(card, id, acEntries);
    if (!payload) return;
    sendCommand("ac_setting_new", payload, `ac-settings-${id}`);
  }

  function saveTurboGroup(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    sendCommand("turbo_group", turboGroupPayload(card, id, system, acEntries), `turbo-group-${id}`);
  }

  function setAcPower(on) {
    sendCommand("ac_status", {ac: selectedAcId, power_on: on}, `ac-power-${on}`);
  }

  function setAcMode(mode) {
    sendCommand("ac_status", {ac: selectedAcId, mode: Number(mode)}, `ac-mode-${mode}`);
  }

  function setAcFan(fan) {
    sendCommand("ac_status", {ac: selectedAcId, fan: Number(fan)}, `ac-fan-${fan}`);
  }

  function zonePayload(id, group, on) {
    return buildZonePayload(id, group, on);
  }

  function setZonePower(id, group, on) {
    sendCommand("group_power", zonePayload(id, group, on), `zone-power-${id}`);
  }

  function adjustZoneSetpoint(id, group, delta) {
    const status = group?.status || {};
    const next = clamp((finite(status.setpoint) ?? 24) + delta, 16, 32);
    sendCommand("group_setpoint", {group: Number(id), setpoint: next}, `zone-set-${id}-${delta}`);
  }

  function adjustZonePercent(id, group, delta) {
    const status = group?.status || {};
    const next = clamp((finite(status.percentage) ?? 0) + delta, 0, 100);
    sendCommand("group_percentage", {group: Number(id), percentage: next}, `zone-percent-${id}-${delta}`);
  }

  async function allOff() {
    const activeZones = selectedZones.filter(([_id, group]) => groupIsOn(group));
    await sendCommand("ac_status", {ac: selectedAcId, power_on: false}, "all-off");
    for (const [id, group] of activeZones) {
      await sendCommand("group_power", zonePayload(id, group, false), `all-off-zone-${id}`);
    }
  }

  onMount(() => {
    selectedTheme = localStorage.getItem(STORAGE_KEYS.theme) || "system";
    showSupportDiagnostics = localStorage.getItem(STORAGE_KEYS.diagnostics) === "true";
    applyThemePreference(selectedTheme);
    load();
    connectSocket();
    pollTimer = setInterval(() => {
      if (socketState !== "live") load();
    }, 15000);
    themeMediaQuery = window.matchMedia?.("(prefers-color-scheme: dark)") || null;
    themeMediaHandler = () => applyThemePreference(selectedTheme);
    themeMediaQuery?.addEventListener?.("change", themeMediaHandler);
  });

  onDestroy(() => {
    if (socket) socket.close();
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (pollTimer) clearInterval(pollTimer);
    if (themeMediaHandler) themeMediaQuery?.removeEventListener?.("change", themeMediaHandler);
  });

  $: runtime = snapshot?.runtime?.runtime || {};
  $: rootState = snapshot?.runtime?.state || {};
  $: system = rootState.system || {};
  $: service = rootState.service || {};
  $: controller = snapshot?.controller || {};
  $: integrations = snapshot?.integrations || {};
  $: transactions = snapshot?.runtime?.transactions || {};
  $: acs = rootState.acs || {};
  $: groups = rootState.groups || {};
  $: favourites = rootState.favourites || {};
  $: programs = rootState.programs || {};
  $: rawAcEntries = Object.entries(acs).filter(([_id, ac]) => ac?.status || ac?.base || ac?.settings).sort((a, b) => Number(a[0]) - Number(b[0]));
  $: acEntries = configuredAcEntries(rawAcEntries);
  $: groupEntries = Object.entries(groups).filter(([_id, group]) => groupIsConfigured(group)).sort((a, b) => {
    const az = finite(a[1]?.grouping?.ui_zone) ?? Number(a[0]) + 1;
    const bz = finite(b[1]?.grouping?.ui_zone) ?? Number(b[0]) + 1;
    return az - bz;
  });
  $: selectedAcId = Number(acEntries.find(([id]) => Number(id) === Number(selectedAcId))?.[0] ?? acEntries[0]?.[0] ?? selectedAcId);
  $: selectedAc = acEntries.find(([id]) => Number(id) === Number(selectedAcId))?.[1] || acEntries[0]?.[1] || {};
  $: selectedStatus = selectedAc?.status || {};
  $: selectedSettings = selectedAc?.settings || {};
  $: acOptions = acEntries.map(([id, ac]) => [id, acName(id, ac)]);
  $: selectedModeOptions = configuredModes(selectedSettings);
  $: selectedFanOptions = configuredFans(selectedSettings);
  $: selectedZones = (groupEntries, activeZoneEntriesForAc(selectedAc));
  $: selectedGroupEntries = (groupEntries, groupEntriesForAc(selectedAc, {includeSpill: true}));
  $: selectedTemperatureState = resolveTemperatureState(selectedAc, selectedAcId, selectedZones);
  $: selectedThermostat = {
    min: selectedTemperatureState.min,
    max: selectedTemperatureState.max,
    current: selectedTemperatureState.indoor.value,
    setpoint: selectedTemperatureState.setpoint.value,
    temperatures: selectedTemperatureState
  };
  $: selectedSensorName = firstSensorName(selectedZones);
  $: selectedRoomName = mainDisplayRoomName(selectedAc, selectedAcId, selectedZones);
  $: selectedSourceHint = acSourceHint(selectedAc, selectedZones, selectedThermostat);
  $: currentModeKey = modeKey(selectedStatus.mode);
  $: selectedTemperatureChart = temperatureChart(selectedZones, selectedThermostat, selectedStatus, integrations.adaptive || {}, selectedAcId);
  $: selectedHistoryEntries = selectedTemperatureChart.historyEntries;
  $: modeStyle = modeStyleFor(currentModeKey);
  $: applyModeStyleToBody(modeStyle);
  $: activeZoneCount = selectedZones.filter(([_id, group]) => groupIsOn(group)).length;
  $: averageDamper = average(selectedZones.map(([_id, group]) => groupIsOn(group) ? group?.status?.percentage : 0));
  $: sensorRows = (system, groupEntries, sensorRowsFromState());
  $: balanceRows = Object.fromEntries(((system.balance?.zones || [])).map((zone) => [String(zone.zone), zone]));
  $: alerts = (snapshot, acEntries, collectAlerts());
  $: adaptive = integrations.adaptive || {};
  $: adaptiveUi = adaptive.ui || {};
  $: adaptiveConfig = controller.config?.adaptive || {};
  $: serviceViews = showSupportDiagnostics ? [...BASE_SERVICE_VIEWS, SUPPORT_SERVICE_VIEW] : BASE_SERVICE_VIEWS;
  $: if (activeServiceView === "spill") activeServiceView = "ac-setup";
  $: if (activeServiceView === "general" || activeServiceView === "parameters") activeServiceView = "app";
  $: if (!showSupportDiagnostics && activeServiceView === "diagnostics") activeServiceView = "app";
  $: {
    const balanceVisible = activeView === "service" && activeServiceView === "balance";
    if (balanceWasVisible && !balanceVisible) balanceAction("balance_stop");
    balanceWasVisible = balanceVisible;
  }
</script>

<main class="touch-shell" style={modeStyle} data-mode={currentModeKey} data-view={activeView}>
  <Shell {activeView} on:view={(event) => activeView = event.detail} />

  <RoomPanel
    {controller}
    {integrations}
    {selectedThermostat}
    {selectedTemperatureState}
  />
<section class="control-stack">
    {#if error || alerts.length}
      <div class="error-strip">{error || alerts[0]}</div>
    {/if}

    {#if activeView === "control"}
      <ControlView
        {acOptions}
        {selectedAcId}
        {selectedStatus}
        {selectedThermostat}
        {selectedTemperatureState}
        {selectedHistoryEntries}
        selectedHistoryPath={selectedTemperatureChart.historyPath}
        selectedPlanPath={selectedTemperatureChart.planPath}
        selectedSetpointPath={selectedTemperatureChart.setpointPath}
        selectedCallAreaPath={selectedTemperatureChart.callAreaPath}
        selectedPlanEntries={selectedTemperatureChart.planEntries}
        selectedCallLabel={selectedTemperatureChart.callLabel}
        {selectedModeOptions}
        {selectedFanOptions}
        {selectedRoomName}
        {selectedSensorName}
        {selectedZones}
        {selectedGroupEntries}
        {activeZoneCount}
        {averageDamper}
        {alerts}
        {pendingKey}
        {groupIsOn}
        {groupIsSpill}
        {groupBadges}
        {zoneName}
        {zoneRoomTemperature}
        on:selectAc={(event) => selectedAcId = event.detail}
        on:power={(event) => setAcPower(event.detail)}
        on:allOff={allOff}
        on:mode={(event) => setAcMode(event.detail)}
        on:fan={(event) => setAcFan(event.detail)}
        on:zonePower={(event) => setZonePower(event.detail.id, event.detail.group, event.detail.powerOn)}
        on:zoneSetpoint={(event) => adjustZoneSetpoint(event.detail.id, event.detail.group, event.detail.delta)}
        on:zonePercent={(event) => adjustZonePercent(event.detail.id, event.detail.group, event.detail.delta)}
      />
    {:else if activeView === "favourites"}
      <FavouritesView
        options={PROGRAM_VIEWS}
        {activeProgramView}
        {favourites}
        {programs}
        {groups}
        {groupEntries}
        {selectedZones}
        {acEntries}
        {pendingKey}
        {favouriteGroups}
        {zoneName}
        {groupsFromBitmap}
        {groupIsSpill}
        {acName}
        {timeText}
        {timeValue}
        on:view={(event) => activeProgramView = event.detail}
        on:applyFavourite={(event) => applyFavourite(event.detail)}
        on:saveFavourite={(event) => saveFavourite(event.detail.event, event.detail.id)}
        on:clearFavourite={(event) => clearFavourite(event.detail)}
        on:saveProgram={(event) => saveProgram(event.detail.event, event.detail.id)}
        on:clearProgram={(event) => clearProgram(event.detail)}
        on:saveAcTimer={(event) => saveAcTimer(event.detail.event, event.detail.id)}
      />
    {:else if activeView === "adaptive"}
      <AdaptiveView
        options={ADAPTIVE_VIEWS}
        {activeAdaptiveView}
        {adaptiveUi}
        {adaptiveConfig}
        {groupEntries}
        {selectedZones}
        {pendingKey}
        {groupIsSpill}
        {zoneName}
        onView={(view) => activeAdaptiveView = view}
        onSaveConfig={sendAdaptiveConfig}
        onModelAction={sendAdaptiveModelAction}
      />
    {:else}
      <SettingsView
        options={serviceViews}
        {activeServiceView}
        {runtime}
        {socketState}
        {selectedTheme}
        {showSupportDiagnostics}
        {system}
        {service}
        {controller}
        {transactions}
        {busEvents}
        {sensorRows}
        {groupEntries}
        {selectedZones}
        {selectedGroupEntries}
        {acEntries}
        {balanceRows}
        {setTheme}
        {setShowSupportDiagnostics}
        {savePreference}
        {saveRuntimeConfig}
        {pairSensor}
        {sensorKindLabel}
        {saveSensorTemperature}
        {confirmAction}
        {zoneName}
        {saveGroupName}
        {saveGrouping}
        {saveSpill}
        {stepBalance}
        {balanceAction}
        {acName}
        {saveAcBase}
        {saveAcSettings}
        {saveTurboGroup}
        {saveParameters}
        {saveService}
        {resetServiceCounter}
        onView={(view) => activeServiceView = view}
      />
    {/if}
  </section>
  <ConfirmDialog dialog={confirmDialog} resolve={resolveConfirmDialog} />
</main>
