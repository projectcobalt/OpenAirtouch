<script>
  import { onDestroy, onMount } from "svelte";
  import Shell from "./components/Shell.svelte";
  import RoomPanel from "./components/RoomPanel.svelte";
  import Subnav from "./components/Subnav.svelte";
  import ViewHeading from "./components/ViewHeading.svelte";
  import ControlView from "./views/ControlView.svelte";
  import AdaptiveView from "./views/AdaptiveView.svelte";
  import FavouritesView from "./views/FavouritesView.svelte";
  import SettingsView from "./views/SettingsView.svelte";
  import { MODE_OPTIONS, fanName, modeKey, modeName } from "./lib/airtouch.js";
  import { apiPath, fetchJson, postCommand, wsPath } from "./lib/client.js";
  import { clamp, finite, percentText, tempText, title } from "./lib/format.js";
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
  let selectedTheme = "system";
  let socket = null;
  let reconnectTimer = null;
  let pollTimer = null;

  const PROGRAM_VIEWS = [["favourites", "Favourites"], ["programs", "Programs"], ["timers", "AC Timer"]];
  const ADAPTIVE_VIEWS = [["status", "Status"], ["config", "Config"], ["analytics", "Analytics"]];
  const SERVICE_VIEWS = [["app", "App"], ["sensors", "Sensors"], ["grouping", "Grouping"], ["spill", "Spill"], ["balance", "Balance"], ["ac-setup", "AC Setup"], ["parameters", "Parameters"], ["system", "System Info"], ["diagnostics", "Diagnostics"]];

  async function load() {
    error = "";
    try {
      [health, snapshot] = await Promise.all([
        fetchJson("health"),
        fetchJson("state")
      ]);
      keepSelectedAcValid();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    }
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
    const flags = settings?.modes || {};
    const configured = MODE_OPTIONS.filter(([_value, _label, key]) => flags[key] === true);
    return configured.length ? configured : MODE_OPTIONS;
  }

  function configuredFans(settings) {
    const values = settings?.fan_values || {};
    const hasValues = Object.keys(values).length > 0;
    const candidates = [
      ["auto", "Auto", 0],
      ["quiet", "Quiet", null],
      ["low", "Low", 1],
      ["medium", "Med", 2],
      ["high", "High", 3],
      ["powerful", "Powerful", null],
      ["turbo", "Turbo", null]
    ];
    const seen = new Set();
    const options = [];
    for (const [key, label, fallback] of candidates) {
      const raw = finite(values[key]);
      const value = raw ?? fallback;
      if (raw === null && hasValues) continue;
      if (value === null || value < 0 || value > 6 || seen.has(value)) continue;
      seen.add(value);
      options.push([value, label, key]);
    }
    return options.length ? options : [[0, "Auto"], [1, "Low"], [2, "Med"], [3, "High"]];
  }

  function acName(id, ac) {
    return ac?.base?.name || `AC ${Number(id) + 1}`;
  }

  function configuredAcEntries(entries) {
    const declaredCount = finite(system.ac_count);
    const filtered = entries.filter(([id, ac]) => {
      const numeric = finite(id);
      if (numeric === null) return false;
      if (declaredCount !== null && declaredCount > 0) {
        return numeric >= 0 && numeric < declaredCount;
      }
      const groupCount = finite(ac?.base?.group_count);
      return groupCount === null || groupCount > 0;
    });
    return filtered.length ? filtered : entries;
  }

  function groupIsConfigured(group) {
    return !!(group?.status || group?.name || group?.name_record || group?.grouping);
  }

  function groupIsSpill(group) {
    return group?.spill_configured === true || String(group?.name || "").toLowerCase() === "spill" || group?.status?.spill_on === true;
  }

  function groupIsOn(group) {
    const status = group?.status || {};
    return status.power_name === "on" || status.power_name === "turbo" || status.power_code === 1;
  }

  function groupBadges(group) {
    const status = group?.status || {};
    const badges = [];
    if (groupIsSpill(group)) badges.push("Spill");
    if (status.low_battery) badges.push("Battery");
    if (status.timer_on) badges.push("Program");
    if (status.power_name === "turbo") badges.push("Turbo");
    return badges.slice(0, 3);
  }

  function zoneName(id, group) {
    return group?.name || group?.name_record?.name || `Zone ${Number(id) + 1}`;
  }

  function groupEntriesForAc(ac, {includeSpill = false} = {}) {
    const base = ac?.base || {};
    const start = finite(base.group_start) ?? 0;
    const count = finite(base.group_count);
    const includeGroup = (group) => groupIsConfigured(group) && (includeSpill || !groupIsSpill(group));
    if (count === null) {
      return groupEntries.filter(([_id, group]) => includeGroup(group));
    }
    const end = start + count;
    return groupEntries.filter(([id, group]) => {
      const numeric = Number(id);
      return numeric >= start && numeric < end && includeGroup(group);
    });
  }

  function activeZoneEntriesForAc(ac) {
    return groupEntriesForAc(ac, {includeSpill: false});
  }

  function average(values) {
    const clean = values.map(finite).filter((value) => value !== null);
    return clean.length ? clean.reduce((total, value) => total + value, 0) / clean.length : null;
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
    const status = group?.status || {};
    return firstFinite(status.temperature, status.current_temp, status.sensor_temp);
  }

  function firstSensorName(zones) {
    const withSensor = zones.find(([_id, group]) => group?.status?.has_sensor);
    return withSensor?.[1]?.grouping?.thermostat_name || (withSensor ? `${zoneName(withSensor[0], withSensor[1])} Sensor` : "Room Sensor");
  }

  function activeRoomName(zones) {
    const active = zones.find(([_id, group]) => groupIsOn(group));
    return active ? zoneName(active[0], active[1]) : zoneName(zones[0]?.[0] ?? 0, zones[0]?.[1] || {});
  }

  function thermostatFor(ac, zones) {
    const status = ac?.status || {};
    const settings = ac?.settings || {};
    const sensorZones = zones.map(([_id, group]) => group?.status || {}).filter((item) => item.has_sensor);
    const activeSensorZones = sensorZones.filter((item) => item.sensor_control && (item.power_code === 1 || item.power_name === "on"));
    const current = finite(status.sensor_temp) ?? average(sensorZones.map((item) => item.temperature));
    const setpoint = average(activeSensorZones.map((item) => item.setpoint)) ?? finite(status.setpoint);
    return {
      min: finite(settings.min_setpoint) ?? 16,
      max: finite(settings.max_setpoint) ?? 30,
      current,
      setpoint
    };
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
    const activeZoneCount = zones.filter(([_id, group]) => groupIsOn(group)).length;
    const historyEntries = aggregateTemperatureHistory(zones, thermostat);
    const suppliedPlan = availableTemperaturePlan(adaptiveState, acId, zones);
    const fallbackPlanEntries = plannedTemperatureEntries(historyEntries, thermostat, status, activeZoneCount);
    const planEntries = suppliedPlan?.entries?.length ? suppliedPlan.entries : fallbackPlanEntries;
    const planSeries = historyEntries.length && planEntries.length ? [historyEntries.at(-1), ...planEntries] : [];
    const current = finite(historyEntries.at(-1)?.temperature) ?? finite(thermostat?.current);
    const callActive = suppliedPlan?.entries?.length ? suppliedPlan.callActive : thermalCallActive(current, finite(thermostat?.setpoint), status);
    const values = [...historyEntries, ...planEntries].map((entry) => finite(entry?.temperature)).filter((value) => value !== null);
    const setpoint = firstFinite(suppliedPlan?.setpoint, thermostat?.setpoint);
    if (setpoint !== null) values.push(setpoint);
    if (!values.length) {
      return {historyEntries, planEntries, historyPath: "", planPath: "", setpointPath: "", callAreaPath: "", callLabel: "No active zone demand"};
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const pad = Math.max(0.4, (max - min) * 0.18);
    const domain = {min: min - pad, max: max + pad};
    const total = historyEntries.length + planEntries.length;
    const historyPath = temperatureChartPath(historyEntries, domain, 0, total);
    const planPath = temperatureChartPath(planSeries, domain, Math.max(0, historyEntries.length - 1), total);
    const setpointY = setpoint === null ? null : 24 - ((setpoint - domain.min) / Math.max(1, domain.max - domain.min)) * 18;
    const setpointPath = setpointY === null ? "" : `M0 ${setpointY.toFixed(1)} L120 ${setpointY.toFixed(1)}`;
    const callStart = callActive && planEntries.length ? ((Math.max(0, historyEntries.length - 1) / Math.max(1, total - 1)) * 120) : null;
    const callAreaPath = callStart === null ? "" : `M${callStart.toFixed(1)} 3 L120 3 L120 27 L${callStart.toFixed(1)} 27 Z`;
    const callLabel = suppliedPlan?.label || (callActive ? "AC call plan" : activeZoneCount ? "Zone plan" : "No active zone demand");
    return {historyEntries, planEntries, historyPath, planPath, setpointPath, callAreaPath, callLabel};
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

  function adaptiveMetric(label, value) {
    return {label, value: value === undefined || value === null || value === "" ? "-" : String(value)};
  }

  function groupsFromBitmap(low = 0, high = 0) {
    const groups = [];
    for (let index = 0; index < 8; index += 1) {
      if (Number(low) & (1 << index)) groups.push(index);
    }
    for (let index = 0; index < 8; index += 1) {
      if (Number(high) & (1 << index)) groups.push(index + 8);
    }
    return groups;
  }

  function bitmapFromGroups(groupIds) {
    return groupIds.reduce((mask, group) => mask | (1 << Number(group)), 0);
  }

  function splitGroupBitmap(groupIds) {
    const low = [];
    const high = [];
    groupIds.forEach((group) => {
      if (group < 8) low.push(group);
      else high.push(group - 8);
    });
    return {
      groups_1_8_bitmap: bitmapFromGroups(low),
      groups_9_16_bitmap: bitmapFromGroups(high)
    };
  }

  function checkedValues(card, selector) {
    return Array.from(card.querySelectorAll(selector))
      .filter((input) => input.checked)
      .map((input) => Number(input.value ?? input.dataset.group ?? input.dataset.favouriteGroup));
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
    const value = card.querySelector(`[data-field="${prefix}-time"]`)?.value || "00:00";
    const [hour, minute] = value.split(":").map((item) => Number(item));
    return {
      enabled: card.querySelector(`[data-field="${prefix}-enabled"]`)?.value === "true",
      hour: Number.isFinite(hour) ? hour : 0,
      minute: Number.isFinite(minute) ? minute : 0
    };
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
    const groups = checkedValues(card, "[data-favourite-group]");
    const name = card.querySelector('[data-field="favourite-name"]')?.value || "";
    sendCommand("favourite", {favourite: Number(id), name, groups}, `favourite-save-${id}`);
  }

  function clearFavourite(id) {
    sendCommand("favourite", {favourite: Number(id), name: "", groups: []}, `favourite-clear-${id}`);
  }

  function applyFavourite(id) {
    sendCommand("active_favourite", {favourite: Number(id)}, `favourite-apply-${id}`);
  }

  function saveProgram(event, id) {
    const card = event.currentTarget.closest("[data-program]");
    const records = programRecordsFromState();
    const programNumber = Number(id);
    const record = records.find((item) => Number(item.program) === programNumber) || {program: programNumber};
    record.name = card.querySelector('[data-field="program-name"]')?.value || "";
    record.enabled = card.querySelector('[data-field="program-enabled"]')?.value === "true";
    record.days_bitmap = bitmapFromGroups(checkedValues(card, "[data-program-day]"));
    Object.assign(record, splitGroupBitmap(checkedValues(card, "[data-program-zone]")));
    record.active_ac_bitmap = bitmapFromGroups(checkedValues(card, "[data-program-ac]"));
    record.on_setpoint = Number(card.querySelector('[data-field="program-on-setpoint"]')?.value || 26);
    record.on_timer = timerFromCard(card, "on");
    record.off_timer = timerFromCard(card, "off");
    if (!records.some((item) => Number(item.program) === programNumber)) records.push(record);
    sendCommand("program_define_new", {
      program_count: Number(system.program_count ?? records.length),
      linked_ac: !!system.programs_linked_ac,
      records
    }, `program-save-${id}`);
  }

  function clearProgram(id) {
    const records = programRecordsFromState();
    const programNumber = Number(id);
    const index = records.findIndex((item) => Number(item.program) === programNumber);
    const cleared = {
      program: programNumber,
      enabled: false,
      days_bitmap: 0,
      name: "",
      groups_1_8_bitmap: 0,
      groups_9_16_bitmap: 0,
      active_ac_bitmap: 0,
      on_timer: {enabled: false, hour: 0, minute: 0},
      on_setpoint: 26,
      off_timer: {enabled: false, hour: 0, minute: 0}
    };
    if (index >= 0) records[index] = cleared;
    else records.push(cleared);
    sendCommand("program_define_new", {
      program_count: Number(system.program_count ?? records.length),
      linked_ac: !!system.programs_linked_ac,
      records
    }, `program-clear-${id}`);
  }

  function saveAcTimer(event, id) {
    const card = event.currentTarget.closest("[data-ac-timer]");
    const records = acTimerRecordsFromState();
    const ac = Number(id);
    const record = records.find((item) => Number(item.ac) === ac) || {ac};
    record.on_timer = timerFromCard(card, "on");
    record.off_timer = timerFromCard(card, "off");
    if (!records.some((item) => Number(item.ac) === ac)) records.push(record);
    sendCommand("ac_timer_table", {records, ac_count: records.length || 4}, `ac-timer-${id}`);
  }

  async function sendAdaptiveConfig(event) {
    const card = event.currentTarget.closest("[data-adaptive-config]");
    const controlZones = checkedValues(card, "[data-adaptive-control-zone]");
    const outsideAirZones = checkedValues(card, "[data-adaptive-outside-air-zone]");
    const payload = {
      mode: card.querySelector("#adaptive-mode")?.value || "off",
      control_strategy: card.querySelector("#adaptive-control-strategy")?.value || "weather_setpoint",
      cool_diff: Number(card.querySelector("#adaptive-cool-diff")?.value || 4),
      cool_comfort_temp: Number(card.querySelector("#adaptive-cool-comfort-temp")?.value || 24),
      heat_diff: Number(card.querySelector("#adaptive-heat-diff")?.value || 4),
      heat_comfort_temp: Number(card.querySelector("#adaptive-heat-comfort-temp")?.value || 20),
      check_interval: Number(card.querySelector("#adaptive-check-interval")?.value || 60),
      command_cooldown: Number(card.querySelector("#adaptive-command-cooldown")?.value || 300),
      mpc_horizon_hours: Number(card.querySelector("#adaptive-mpc-horizon-hours")?.value || 6),
      compressor_min_run_time: Number(card.querySelector("#adaptive-compressor-min-run-time")?.value || 0),
      compressor_min_off_time: Number(card.querySelector("#adaptive-compressor-min-off-time")?.value || 0),
      control_zones: controlZones,
      outside_air_zones: outsideAirZones
    };
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

  function adaptiveHeadline() {
    const weather = adaptive.weather_intent || {};
    const modeIntent = adaptive.mode_intent || {};
    if (weather.headline) return weather.headline;
    if (weather.pause_active) return "AC Paused";
    if (weather.resume_pending) return "AC Resume Pending";
    if (modeIntent.name) return title(modeIntent.name);
    if (adaptive.recommended_target !== undefined && adaptive.recommended_target !== null) return `Recommended Target: ${tempText(adaptive.recommended_target)}`;
    if ((adaptive.mode || adaptiveConfig.mode) === "off") return "AirTouch Has Control";
    if (adaptiveReadyCount === 0) return "Model Learning";
    return "Adaptive Ready";
  }

  function adaptiveReason() {
    const weather = adaptive.weather_intent || {};
    const modeIntent = adaptive.mode_intent || {};
    return weather.summary || weather.reason || modeIntent.reason || modeIntent.ventilation_reason || adaptive.recommendations?.[0] || "Waiting for clearer adaptive intent";
  }

  function adaptiveOwnership() {
    const weather = adaptive.weather_intent || {};
    if (!runtime.connected) return "Runtime disconnected: adaptive commands and restores are held";
    if (weather.pause_active) return "Environment owns the current AC pause";
    if (weather.resume_pending) return "Environment resume pending";
    if ((adaptive.mode || adaptiveConfig.mode) === "off") return "Adaptive off: restore only, no new control";
    if ((adaptive.mode || adaptiveConfig.mode) === "recommend") return "Recommend only: no commands";
    return "Adaptive may control selected zones";
  }

  function adaptiveHours(value) {
    const hours = finite(value);
    return hours === null ? "-" : `${hours.toFixed(hours < 10 ? 1 : 0)} h`;
  }

  function adaptiveUntil(value) {
    if (!value) return "";
    const timestamp = Number(value) > 10000000000 ? Number(value) : Number(value) * 1000;
    if (!Number.isFinite(timestamp)) return String(value);
    return new Date(timestamp).toLocaleTimeString([], {hour: "numeric", minute: "2-digit"});
  }

  function environmentIntent() {
    const weather = adaptive.weather_intent || {};
    const quality = adaptive.air_quality || {};
    const outside = finite(weather.outside_temperature) ?? finite(adaptive.outside_temperature);
    const windowMinutes = finite(weather.favourable_window_minutes);
    const headline = weather.headline || (weather.pause_active ? "AC Paused" : weather.nice_outside ? "Nice Outside" : quality.co2_high ? "Outside Air Recommended" : "Environment Watching");
    const summary = weather.summary || weather.reason || quality.ventilation_reason || (windowMinutes !== null ? `Forecast Looks Helpful For ${(windowMinutes / 60).toFixed(1)} H` : "Outdoor and air quality inputs are being watched");
    return {
      headline,
      summary,
      fields: [
        adaptiveMetric("Outside", outside === null ? "-" : tempText(outside, 1)),
        adaptiveMetric("Nice Until", weather.nice_until ? adaptiveUntil(weather.nice_until) : "-"),
        adaptiveMetric("Pause", weather.pause_active ? "Active" : weather.pause_recommended ? "Recommended" : "Clear"),
        adaptiveMetric("Fresh Air", weather.outside_air_intent || quality.fan_recommended ? "Recommended" : "Not Requested")
      ]
    };
  }

  function zoneIntent() {
    const modeIntent = adaptive.mode_intent || {};
    const target = finite(adaptive.recommended_target ?? modeIntent.target ?? modeIntent.setpoint);
    const runtime = finite(adaptive.runtime_hours ?? adaptive.projected_runtime_hours ?? modeIntent.projected_runtime_hours);
    const headline = modeIntent.name ? title(modeIntent.name) : target !== null ? `Recommended Target: ${target.toFixed(0)}°` : adaptiveReadyCount ? "Zone Models Ready" : "Waiting For Zones";
    const summary = modeIntent.reason || adaptive.recommendations?.[0] || (adaptiveReadyCount ? `${adaptiveReadyCount} zone models are ready` : "Model Learning: Waiting For More Samples");
    return {
      headline,
      summary,
      fields: [
        adaptiveMetric("Target", target === null ? "-" : tempText(target)),
        adaptiveMetric("Expected Runtime", runtime === null ? "-" : adaptiveHours(runtime)),
        adaptiveMetric("Learning", `${adaptiveReadyCount} ready / ${adaptiveLearningCount} learning`),
        adaptiveMetric("Active Zones", (adaptive.active_groups || []).length || activeZoneCount)
      ]
    };
  }

  function hybridIntent() {
    const strategy = adaptiveConfig.control_strategy || "weather_setpoint";
    const dampers = adaptive.active_dampers || {};
    const activePlan = Object.entries(dampers).length
      ? Object.entries(dampers).slice(0, 4).map(([id, value]) => `${zoneName(id, groups[String(id)] || {})} ${Math.round(Number(value))}%`).join(", ")
      : selectedZones.filter(([_id, group]) => groupIsOn(group)).slice(0, 4).map(([id, group]) => `${zoneName(id, group)} ${Math.round(finite(group?.status?.percentage) ?? 0)}%`).join(", ");
    const heatCool = ["heat", "cool", "auto"].includes(currentModeKey);
    return {
      headline: strategy === "hybrid_damper_mpc" && heatCool ? "Damper Plan" : "AirTouch Has Control",
      summary: activePlan || (heatCool ? "Zone airflow preview will appear when adaptive has a plan" : "Dry and Fan keep thermal and air-quality previews separate"),
      fields: [
        adaptiveMetric("Control Temperature", heatCool && selectedThermostat.current !== null ? tempText(selectedThermostat.current, 1) : "-"),
        adaptiveMetric("Zone Airflow", activePlan || "-"),
        adaptiveMetric("Strategy", title(strategy)),
        adaptiveMetric("Outside Air Zones", (adaptiveConfig.outside_air_zones || []).length || "-")
      ]
    };
  }

  function modelBadges(zone = {}) {
    return [
      adaptiveMetric("Progress", zone.learning_progress === undefined ? "-" : percentText(Number(zone.learning_progress) * 100)),
      adaptiveMetric("Samples", `${zone.passive_samples || zone.idle_samples || 0}/${zone.active_samples || 0}`),
      adaptiveMetric("Updates", zone.ekf_updates ?? "-"),
      adaptiveMetric("Confidence", zone.confidence === undefined ? "-" : percentText(Number(zone.confidence) * 100)),
      adaptiveMetric("Error", zone.prediction_std === undefined ? "-" : tempText(zone.prediction_std, 2)),
      adaptiveMetric("Drift", zone.passive_drift_per_hour === undefined ? "-" : `${Number(zone.passive_drift_per_hour).toFixed(2)}°/h`),
      adaptiveMetric("Response", zone.active_response_per_hour === undefined ? "-" : `${Number(zone.active_response_per_hour).toFixed(2)}°/h`),
      adaptiveMetric("Outside", zone.outside_coupling_per_hour === undefined ? "-" : `${Number(zone.outside_coupling_per_hour).toFixed(2)}°/h`)
    ];
  }

  function sensorRowsFromState() {
    const stateRows = sensorViewRows();
    if (stateRows.length) return stateRows;

    const rows = [];
    const sensorList = system.sensor_list || {};
    const addresses = sensorList.sensor_addresses || system.sensor_addresses || [];
    for (const address of addresses) {
      const mappedGroups = groupEntries
        .filter(([_id, group]) => Number(group?.grouping?.thermostat) === Number(address) || group?.grouping?.thermostat_name === `rf_sensor_${address}`)
        .map(([id]) => Number(id) + 1);
      const matchingGroup = groupEntries.find(([_id, group]) => Number(group?.grouping?.thermostat) === Number(address));
      rows.push({
        id: address,
        address: typeof address === "number" ? `0x${Number(address).toString(16).toUpperCase()}` : String(address),
        name: typeof address === "number" && address >= 144 ? `Touchpad ${address - 143}` : `Sensor ${address}`,
        kind: typeof address === "number" && address >= 144 ? "touchpad" : "rf",
        temperature: matchingGroup?.[1]?.status?.temperature,
        mapped_groups: mappedGroups,
        present: true
      });
    }
    for (const supply of system.supply_air || []) {
      rows.push({
        id: `supply-${supply.ac}`,
        address: `AC ${Number(supply.ac) + 1}`,
        name: `Supply Air ${Number(supply.ac) + 1}`,
        kind: "supply_air",
        temperature: supply.temperature,
        present: supply.status !== "disabled"
      });
    }
    return rows;
  }

  function sensorKindLabel(kind) {
    return {rf: "RF Sensor", touchpad: "Touchpad", supply_air: "Supply Air"}[kind] || title(kind || "sensor");
  }

  function saveSensorTemperature(event, sensor) {
    const card = event.currentTarget.closest("[data-sensor-row]");
    const temperature = Number(card.querySelector("[data-sensor-temperature]")?.value);
    if (!Number.isFinite(temperature)) return;
    sendCommand("sensor_temperature", {sensor: Number(sensor), temperature}, `sensor-temperature-${sensor}`);
  }

  function pairSensor(pairing) {
    sendCommand("pair_sensor", {pairing}, `pair-sensor-${pairing}`);
  }

  function saveGrouping(event, id) {
    const card = event.currentTarget.closest("[data-service-group]");
    sendCommand("grouping", {
      group: Number(id),
      zone_start: Number(card.querySelector('[data-field="zone-start"]')?.value || 0),
      zone_count: Number(card.querySelector('[data-field="zone-count"]')?.value || 1),
      min_percent: Number(card.querySelector('[data-field="min-percent"]')?.value || 0),
      thermostat: Number(card.querySelector('[data-field="thermostat"]')?.value || 255)
    }, `grouping-${id}`);
  }

  function saveGroupName(event, id) {
    const card = event.currentTarget.closest("[data-service-group]");
    sendCommand("group_name", {
      group: Number(id),
      name: card.querySelector('[data-field="group-name"]')?.value || ""
    }, `group-name-${id}`);
  }

  function saveSpill(event) {
    const card = event.currentTarget.closest("[data-spill-card]");
    const spill_groups = checkedValues(card, "[data-spill-group]");
    const ac_spill_types = Array.from(card.querySelectorAll("[data-spill-ac]"))
      .sort((a, b) => Number(a.dataset.spillAc) - Number(b.dataset.spillAc))
      .map((select) => Number(select.value));
    sendCommand("spill", {spill_groups, ac_spill_types}, "spill");
  }

  function balanceValuesFromPage() {
    const values = Array(16).fill(0);
    document.querySelectorAll("[data-balance-number]").forEach((input) => {
      const zone = Number(input.dataset.balanceNumber);
      if (zone >= 0 && zone < values.length) values[zone] = Number(input.value);
    });
    return values;
  }

  function balanceAction(action) {
    sendCommand(action, {current_values: balanceValuesFromPage()}, action);
  }

  function stepBalance(event, id, delta) {
    const card = event.currentTarget.closest("[data-balance-zone]");
    const input = card.querySelector("[data-balance-number]");
    input.value = String(clamp(Number(input.value || 0) + delta, 0, 255));
  }

  function savePreference(event) {
    const card = event.currentTarget.closest("[data-preference-card]");
    sendCommand("preference", {
      system_name: card.querySelector("#system-name-input")?.value || system.system_name || "",
      show_ac_errors: card.querySelector('[data-field="show-ac-errors"]')?.value === "true",
      show_outside_temp: card.querySelector('[data-field="pref-show-outside-temp"]')?.value === "true",
      show_control_sensor: card.querySelector('[data-field="pref-show-control-sensor"]')?.value === "true",
      use_fahrenheit: card.querySelector('[data-field="use-fahrenheit"]')?.value === "true",
      location: Number(card.querySelector('[data-field="location"]')?.value || system.address_or_location || 0),
      screensaver_enabled: card.querySelector('[data-field="screensaver-enabled"]')?.value === "true",
      screensaver_timeout: Number(card.querySelector('[data-field="screensaver-timeout"]')?.value || 0)
    }, "preference");
  }

  function saveParameters(event) {
    const card = event.currentTarget.closest("[data-parameters-card]");
    sendCommand("parameters", {
      group_count: Number(card.querySelector('[data-field="group-count"]')?.value || groupEntries.length || 1),
      damper_rpm: Number(card.querySelector('[data-field="damper-rpm"]')?.value || system.damper_rpm || 100),
      touchpad_1_location: Number(card.querySelector('[data-field="touchpad-1-location"]')?.value || 255),
      touchpad_2_location: Number(card.querySelector('[data-field="touchpad-2-location"]')?.value || 255),
      ac_button_blocked: card.querySelector('[data-field="ac-button-blocked"]')?.value === "true",
      show_outside_temp: card.querySelector('[data-field="param-show-outside-temp"]')?.value === "true",
      lock_to_temp_control: card.querySelector('[data-field="lock-to-temp-control"]')?.value === "true",
      show_control_sensor: card.querySelector('[data-field="param-show-control-sensor"]')?.value === "true"
    }, "parameters");
  }

  function saveService(event) {
    const card = event.currentTarget.closest("[data-service-system]");
    sendCommand("service", {
      company: card.querySelector("#service-company-input")?.value || "",
      phone: card.querySelector("#service-phone-input")?.value || "",
      show_service_due: card.querySelector('[data-field="show-service-due"]')?.value === "true",
      service_due_locked: card.querySelector('[data-field="service-due-locked"]')?.value === "true",
      filter_clean_due: card.querySelector('[data-field="filter-clean-due"]')?.value === "true",
      maintenance_due: card.querySelector('[data-field="maintenance-due"]')?.value === "true",
      months: Number(card.querySelector('[data-field="service-months"]')?.value || 0),
      days: Number(card.querySelector('[data-field="service-days"]')?.value || 0),
      runtime_hours: Number(card.querySelector('[data-field="service-runtime-hours"]')?.value || 0)
    }, "service");
  }

  function applyThemePreference(theme = selectedTheme) {
    if (typeof document === "undefined") return;
    const requested = ["system", "light", "dark"].includes(theme) ? theme : "system";
    const systemDark = window.matchMedia?.("(prefers-color-scheme: dark)")?.matches === true;
    document.body.dataset.theme = requested === "system" ? (systemDark ? "dark" : "light") : requested;
  }

  function setTheme(theme) {
    selectedTheme = ["system", "light", "dark"].includes(theme) ? theme : "system";
    localStorage.setItem("airtouch4.uiTheme", selectedTheme);
    applyThemePreference(selectedTheme);
  }

  function acBaseRecordsFromState() {
    return acEntries.map(([id, ac]) => ({
      ac: Number(id),
      group_start: Number(ac?.base?.group_start ?? 0),
      group_count: Number(ac?.base?.group_count ?? 0),
      brand: Number(ac?.base?.brand ?? 0),
      name: ac?.base?.name || `AC ${Number(id) + 1}`
    }));
  }

  function acSettingRecordsFromState() {
    return acEntries.map(([id, ac]) => {
      const settings = ac?.settings || {};
      return {
        ac: Number(id),
        hide_spill_group: !!settings.hide_spill_group,
        ctrl_thermostat: Number(settings.ctrl_thermostat ?? 0),
        cool_adjust: Number(settings.cool_adjust ?? 0),
        heat_adjust: Number(settings.heat_adjust ?? 0),
        modes: settings.modes || {},
        fan_values: settings.fan_values || {},
        auto_off: !!settings.auto_off,
        on_time_limit: Number(settings.on_time_limit ?? 0),
        max_setpoint: Number(settings.max_setpoint ?? 30),
        min_setpoint: Number(settings.min_setpoint ?? 16),
        selector_visibility: settings.selector_visibility || {}
      };
    });
  }

  function saveAcBase(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    const records = acBaseRecordsFromState();
    const record = records.find((item) => Number(item.ac) === Number(id));
    if (!record) return;
    record.name = card.querySelector('[data-field="ac-name"]')?.value || record.name;
    record.group_start = Number(card.querySelector('[data-field="ac-group-start"]')?.value || 0);
    record.group_count = Number(card.querySelector('[data-field="ac-group-count"]')?.value || 0);
    record.brand = Number(card.querySelector('[data-field="ac-brand"]')?.value || record.brand || 0);
    sendCommand("ac_base_info", {
      one_duct_system: !!system.one_duct_system,
      ac_count: records.length,
      records
    }, `ac-base-${id}`);
  }

  function applyAcSettingsCard(record, card) {
    record.hide_spill_group = card.querySelector('[data-field="hide-spill"]')?.value === "true";
    record.ctrl_thermostat = Number(card.querySelector('[data-field="ctrl-thermostat"]')?.value || record.ctrl_thermostat || 0);
    record.cool_adjust = Number(card.querySelector('[data-field="cool-adjust"]')?.value || 0);
    record.heat_adjust = Number(card.querySelector('[data-field="heat-adjust"]')?.value || 0);
    record.min_setpoint = Number(card.querySelector('[data-field="min-setpoint"]')?.value || 16);
    record.max_setpoint = Number(card.querySelector('[data-field="max-setpoint"]')?.value || 30);
    record.auto_off = card.querySelector('[data-field="auto-off"]')?.value === "true";
    record.on_time_limit = Number(card.querySelector('[data-field="on-time-limit"]')?.value || 0);
    record.modes = {
      auto: card.querySelector('[data-field="mode-auto"]')?.value === "true",
      cool: card.querySelector('[data-field="mode-cool"]')?.value === "true",
      heat: card.querySelector('[data-field="mode-heat"]')?.value === "true",
      dry: card.querySelector('[data-field="mode-dry"]')?.value === "true",
      fan: card.querySelector('[data-field="mode-fan"]')?.value === "true"
    };
    record.fan_values = {
      auto: Number(card.querySelector('[data-field="fan-auto"]')?.value || 0),
      quiet: Number(card.querySelector('[data-field="fan-quiet"]')?.value || 0),
      low: Number(card.querySelector('[data-field="fan-low"]')?.value || 1),
      medium: Number(card.querySelector('[data-field="fan-medium"]')?.value || 2),
      high: Number(card.querySelector('[data-field="fan-high"]')?.value || 3),
      powerful: Number(card.querySelector('[data-field="fan-powerful"]')?.value || 0),
      turbo: Number(card.querySelector('[data-field="fan-turbo"]')?.value || 0)
    };
    record.selector_visibility = {
      auto: card.querySelector('[data-field="selector-auto"]')?.value === "true",
      touchpad_1: card.querySelector('[data-field="selector-touchpad_1"]')?.value === "true",
      touchpad_2: card.querySelector('[data-field="selector-touchpad_2"]')?.value === "true",
      average: card.querySelector('[data-field="selector-average"]')?.value === "true",
      economy: card.querySelector('[data-field="selector-economy"]')?.value === "true",
      groups_1_8_bitmap: Number(card.querySelector('[data-field="selector-groups-1"]')?.value || 0),
      groups_9_16_bitmap: Number(card.querySelector('[data-field="selector-groups-2"]')?.value || 0)
    };
    return record;
  }

  function saveAcSettings(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    const records = acSettingRecordsFromState();
    const record = records.find((item) => Number(item.ac) === Number(id));
    if (!record) return;
    applyAcSettingsCard(record, card);
    sendCommand("ac_setting_new", {records}, `ac-settings-${id}`);
  }

  function resetTempOffsets(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    const cool = card.querySelector('[data-field="cool-adjust"]');
    const heat = card.querySelector('[data-field="heat-adjust"]');
    if (cool) cool.value = 0;
    if (heat) heat.value = 0;
    saveAcSettings(event, id);
  }

  function saveTurboGroup(event, id) {
    const card = event.currentTarget.closest("[data-service-ac]");
    const current_groups = [];
    for (const record of system.turbo_group?.records || []) {
      current_groups[Number(record.ac)] = record.group === null || record.group === undefined ? 255 : Number(record.group);
    }
    sendCommand("turbo_group", {
      ac: Number(id),
      group: Number(card.querySelector('[data-field="turbo-group"]')?.value || 255),
      current_groups,
      one_duct_system: !!system.one_duct_system,
      ac_count: Math.max(1, acEntries.length)
    }, `turbo-group-${id}`);
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
    const status = group?.status || {};
    return {
      group: Number(id),
      on,
      sensor_control: status.sensor_control !== false,
      setpoint: finite(status.setpoint) ?? 24,
      percentage: finite(status.percentage) ?? 100
    };
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
    selectedTheme = localStorage.getItem("airtouch4.uiTheme") || controller.config?.ui_theme || "system";
    applyThemePreference(selectedTheme);
    load();
    connectSocket();
    pollTimer = setInterval(() => {
      if (socketState !== "live") load();
    }, 15000);
    window.matchMedia?.("(prefers-color-scheme: dark)")?.addEventListener?.("change", () => applyThemePreference(selectedTheme));
  });

  onDestroy(() => {
    if (socket) socket.close();
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (pollTimer) clearInterval(pollTimer);
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
  $: selectedThermostat = thermostatFor(selectedAc, selectedZones);
  $: selectedSensorName = firstSensorName(selectedZones);
  $: selectedRoomName = activeRoomName(selectedZones);
  $: selectedSourceHint = acSourceHint(selectedAc, selectedZones, selectedThermostat);
  $: currentModeKey = modeKey(selectedStatus.mode);
  $: selectedTemperatureChart = temperatureChart(selectedZones, selectedThermostat, selectedStatus, integrations.adaptive || {}, selectedAcId);
  $: selectedHistoryEntries = selectedTemperatureChart.historyEntries;
  $: modeStyle = modeStyleFor(currentModeKey);
  $: activeZoneCount = selectedZones.filter(([_id, group]) => groupIsOn(group)).length;
  $: averageDamper = average(selectedZones.map(([_id, group]) => group?.status?.percentage));
  $: sensorRows = (system, groupEntries, sensorRowsFromState());
  $: balanceRows = Object.fromEntries(((system.balance?.zones || [])).map((zone) => [String(zone.zone), zone]));
  $: alerts = (snapshot, acEntries, collectAlerts());
  $: adaptive = integrations.adaptive || {};
  $: adaptiveConfig = controller.config?.adaptive || {};
  $: adaptiveLearningZones = adaptive.learning?.zones || {};
  $: adaptiveReadyCount = Object.values(adaptiveLearningZones).filter((zone) => zone?.mpc_ready === true).length;
  $: adaptiveLearningCount = Object.values(adaptiveLearningZones).filter((zone) => zone?.learn === true).length;
  $: adaptiveEnvironment = environmentIntent();
  $: adaptiveZoneIntent = zoneIntent();
  $: adaptiveHybridIntent = hybridIntent();
  $: runtimeMetrics = [
    adaptiveMetric("Protocol", runtime.protocol_name || title(runtime.protocol || "at4")),
    adaptiveMetric("Service", title(controller.status || "unknown")),
    adaptiveMetric("Transport", title(controller.config?.transport || "-")),
    adaptiveMetric("Endpoint", controller.config?.transport === "tcp_serial" ? `${controller.config?.tcp_host}:${controller.config?.tcp_port}` : controller.config?.port),
    adaptiveMetric("Address", runtime.src),
    adaptiveMetric("Boot", runtime.boot_complete ? "Complete" : "Pending"),
    adaptiveMetric("RX / TX", `${runtime.rx_count || 0} / ${runtime.tx_count || 0}`),
    adaptiveMetric("Transactions", `${transactions.completed?.length || 0} OK, ${transactions.failed?.length || 0} Fail`)
  ];
</script>

<main class="touch-shell" style={modeStyle} data-mode={currentModeKey} data-view={activeView}>
  <Shell {activeView} on:view={(event) => activeView = event.detail} />

  <RoomPanel
    {controller}
    {integrations}
    {selectedRoomName}
    {selectedThermostat}
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
        {selectedHistoryEntries}
        selectedHistoryPath={selectedTemperatureChart.historyPath}
        selectedPlanPath={selectedTemperatureChart.planPath}
        selectedSetpointPath={selectedTemperatureChart.setpointPath}
        selectedCallAreaPath={selectedTemperatureChart.callAreaPath}
        selectedPlanEntries={selectedTemperatureChart.planEntries}
        selectedCallLabel={selectedTemperatureChart.callLabel}
        {selectedModeOptions}
        {selectedFanOptions}
        {selectedSensorName}
        {selectedZones}
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
        {adaptive}
        {adaptiveConfig}
        {adaptiveEnvironment}
        {adaptiveZoneIntent}
        {adaptiveHybridIntent}
        {adaptiveReadyCount}
        {adaptiveLearningCount}
        {adaptiveLearningZones}
        {groupEntries}
        {selectedZones}
        {pendingKey}
        {adaptiveHeadline}
        {adaptiveReason}
        {adaptiveMetric}
        {adaptiveOwnership}
        {groupIsSpill}
        {zoneName}
        {modelBadges}
        onView={(view) => activeAdaptiveView = view}
        onSaveConfig={sendAdaptiveConfig}
        onModelAction={sendAdaptiveModelAction}
      />
    {:else}
      <SettingsView
        options={SERVICE_VIEWS}
        {activeServiceView}
        {runtime}
        {selectedTheme}
        {system}
        {runtimeMetrics}
        {sensorRows}
        {groupEntries}
        {selectedGroupEntries}
        {acEntries}
        {balanceRows}
        {rootState}
        {setTheme}
        {savePreference}
        {pairSensor}
        {sensorKindLabel}
        {saveSensorTemperature}
        {zoneName}
        {groupIsOn}
        {saveGroupName}
        {saveGrouping}
        {saveSpill}
        {stepBalance}
        {balanceAction}
        {acName}
        {saveAcBase}
        {saveAcSettings}
        {resetTempOffsets}
        {saveTurboGroup}
        {saveParameters}
        {saveService}
        onView={(view) => activeServiceView = view}
      />
    {/if}
  </section>
</main>
