import { MODE_OPTIONS, modeKey } from "./openairtouch.js";
import { finite, percentText, tempText, title } from "./format.js";

export function configuredModes(settings) {
  const flags = settings?.modes || {};
  const configured = MODE_OPTIONS.filter(([_value, _label, key]) => flags[key] === true);
  return configured.length ? configured : MODE_OPTIONS;
}

export function configuredFans(settings) {
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

export const acName = (id, ac) => ac?.base?.name || `AC ${Number(id) + 1}`;

export function configuredAcEntries(entries, system = {}) {
  const declaredCount = finite(system.ac_count);
  const filtered = entries.filter(([id, ac]) => {
    const numeric = finite(id);
    if (numeric === null) return false;
    if (declaredCount !== null && declaredCount > 0) return numeric >= 0 && numeric < declaredCount;
    const groupCount = finite(ac?.base?.group_count);
    return groupCount === null || groupCount > 0;
  });
  return filtered.length ? filtered : entries;
}

export const groupIsConfigured = (group) => !!(group?.status || group?.name || group?.name_record || group?.grouping);

export const groupIsSpill = (group) => group?.spill_configured === true || String(group?.name || "").toLowerCase() === "spill" || group?.status?.spill_on === true;

export function groupIsOn(group) {
  const status = group?.status || {};
  return status.power_name === "on" || status.power_name === "turbo" || status.power_code === 1;
}

export function groupBadges(group) {
  const status = group?.status || {};
  const badges = [];
  if (groupIsSpill(group)) badges.push("Spill");
  if (status.low_battery) badges.push("Battery");
  if (status.timer_on) badges.push("Program");
  if (status.power_name === "turbo") badges.push("Turbo");
  return badges.slice(0, 3);
}

export const zoneName = (id, group) => group?.name || group?.name_record?.name || `Zone ${Number(id) + 1}`;

export function groupEntriesForAc(ac, groupEntries, {includeSpill = false} = {}) {
  const base = ac?.base || {};
  const start = finite(base.group_start) ?? 0;
  const count = finite(base.group_count);
  const includeGroup = (group) => groupIsConfigured(group) && (includeSpill || !groupIsSpill(group));
  if (count === null) return groupEntries.filter(([_id, group]) => includeGroup(group));
  const end = start + count;
  return groupEntries.filter(([id, group]) => {
    const numeric = Number(id);
    return numeric >= start && numeric < end && includeGroup(group);
  });
}

export const activeZoneEntriesForAc = (ac, groupEntries) => groupEntriesForAc(ac, groupEntries, {includeSpill: ac?.settings?.hide_spill_group === false});

export function average(values) {
  const clean = values.map(finite).filter((value) => value !== null);
  return clean.length ? clean.reduce((total, value) => total + value, 0) / clean.length : null;
}

export function firstFinite(...values) {
  for (const value of values) {
    const numeric = finite(value);
    if (numeric !== null) return numeric;
  }
  return null;
}

export function zoneRoomTemperature(_id, group) {
  const status = group?.status || {};
  return firstFinite(status.temperature, status.current_temp, status.sensor_temp);
}

function temperatureReading(value, label, source, extra = {}) {
  const sourceLabels = {
    ac_sensor: "AC sensor",
    ac_status: "AC status",
    ac_control_echo: "AC control echo",
    active_zone_average: "Active zone average",
    control_zone: "Control zone",
    ha_indoor: "HA indoor",
    zone_average: "Zone average"
  };
  return {value: finite(value), label, source, sourceLabel: sourceLabels[source] || title(source || "temperature"), ...extra};
}

function activeSensorZoneEntries(zones) {
  return zones.filter(([_id, group]) => {
    const status = group?.status || {};
    return groupIsOn(group) && status.has_sensor === true && status.sensor_control !== false;
  });
}

function mainDisplayControlZone(system, acId, zones) {
  const records = system?.main_display?.records;
  if (!Array.isArray(records)) return null;
  const acRecords = records
    .filter((record) => Number(record?.ac) === Number(acId) && record?.hidden !== true)
    .reverse();
  for (const record of acRecords) {
    const rawBytes = String(record?.raw || "").split(/\s+/).map((item) => Number.parseInt(item, 16)).filter(Number.isFinite);
    const sensor = finite(record?.sign_sensor) ?? finite(rawBytes[2]);
    const groupId = finite(record?.sign_group) ?? (sensor !== null && sensor >= 224 ? sensor - 224 : sensor);
    if (groupId === null || groupId < 0 || groupId > 15) continue;
    const entry = zones.find(([id]) => Number(id) === groupId);
    if (entry && groupIsOn(entry[1]) && zoneRoomTemperature(entry[0], entry[1]) !== null) return entry;
  }
  return null;
}

function selectedControlZone(ac, zones, system, acId) {
  const displayZone = mainDisplayControlZone(system, acId, zones);
  if (displayZone) return displayZone;

  const activeZones = activeSensorZoneEntries(zones);
  const controlTemperature = finite(ac?.status?.sensor_temp);
  if (controlTemperature !== null) {
    const matchingZones = activeZones.filter(([_id, group]) => zoneRoomTemperature(_id, group) === controlTemperature);
    if (matchingZones.length === 1) return matchingZones[0];
  }

  const selector = finite(ac?.settings?.ctrl_thermostat);
  if (selector !== null && selector < 253) {
    const mapped = zones.find(([_id, group]) => {
      const status = group?.status || {};
      return status.has_sensor === true && (
        Number(status.sensor_id) === selector ||
        Number(group?.grouping?.thermostat) === selector
      );
    });
    if (mapped && zoneRoomTemperature(mapped[0], mapped[1]) !== null) return mapped;
  }

  return activeZones.length === 1 ? activeZones[0] : null;
}

export function resolveTemperatureState({system = {}, ac = {}, acId = 0, zones = [], integrations = {}} = {}) {
  const status = ac?.status || {};
  const settings = ac?.settings || {};
  const activeZones = zones.filter(([_id, group]) => groupIsOn(group));
  const sensorZones = zones.filter(([_id, group]) => group?.status?.has_sensor === true);
  const controlZone = selectedControlZone(ac, zones, system, acId);
  const haIndoorTemperature = finite(integrations?.indoor?.state?.temperature);
  const activeZoneTemperature = average(activeZones.map(([id, group]) => zoneRoomTemperature(id, group)));
  const allZoneTemperature = average(sensorZones.map(([id, group]) => zoneRoomTemperature(id, group)));
  const indoor = haIndoorTemperature !== null
    ? temperatureReading(haIndoorTemperature, "Indoor", "ha_indoor")
    : activeZoneTemperature !== null
      ? temperatureReading(activeZoneTemperature, "Indoor", "active_zone_average")
      : temperatureReading(allZoneTemperature, "Indoor", "zone_average");
  const control = controlZone
    ? temperatureReading(status.sensor_temp, zoneName(controlZone[0], controlZone[1]), "ac_control_echo", {zoneId: Number(controlZone[0])})
    : temperatureReading(status.sensor_temp, "AC", "ac_sensor");
  const setpoint = temperatureReading(
    status.setpoint,
    "Setpoint",
    "ac_status"
  );
  return {
    indoor,
    control,
    setpoint,
    min: finite(settings.min_setpoint) ?? 16,
    max: finite(settings.max_setpoint) ?? 30
  };
}

export function firstSensorName(zones) {
  const withSensor = zones.find(([_id, group]) => group?.status?.has_sensor);
  return withSensor?.[1]?.grouping?.thermostat_name || (withSensor ? `${zoneName(withSensor[0], withSensor[1])} Sensor` : "Room Sensor");
}

export function activeRoomName(zones) {
  const active = zones.find(([_id, group]) => groupIsOn(group));
  return active ? zoneName(active[0], active[1]) : zoneName(zones[0]?.[0] ?? 0, zones[0]?.[1] || {});
}

export function controlRoomName(ac, zones) {
  const selector = finite(ac?.settings?.ctrl_thermostat);
  const activeSensorZones = zones.filter(([_id, group]) => {
    const status = group?.status || {};
    return groupIsOn(group) && status.has_sensor === true && status.sensor_control !== false;
  });
  const controlTemperature = finite(ac?.status?.sensor_temp);
  if (controlTemperature !== null) {
    const matchingZones = activeSensorZones.filter(([_id, group]) => finite(group?.status?.temperature) === controlTemperature);
    if (matchingZones.length === 1) return zoneName(matchingZones[0][0], matchingZones[0][1]);
  }

  if (selector !== null && selector < 253) {
    const mapped = zones.find(([_id, group]) => Number(group?.grouping?.thermostat) === selector);
    return mapped ? zoneName(mapped[0], mapped[1]) : `Sensor ${selector}`;
  }

  if (activeSensorZones.length === 1) return zoneName(activeSensorZones[0][0], activeSensorZones[0][1]);
  if (activeSensorZones.length > 1) return "AC";

  return "AC";
}

export function mainDisplayRoomName(system, ac, acId, zones) {
  const records = system?.main_display?.records;
  if (Array.isArray(records)) {
    const acRecords = records.filter((record) => Number(record?.ac) === Number(acId));
    const record = acRecords.at(-1);
    const rawBytes = String(record?.raw || "").split(/\s+/).map((item) => Number.parseInt(item, 16)).filter(Number.isFinite);
    const sensor = finite(record?.sign_sensor) ?? finite(rawBytes[2]);
    const groupId = finite(record?.sign_group) ?? (sensor !== null && sensor >= 224 ? sensor - 224 : sensor);
    if (groupId !== null && groupId >= 0 && groupId <= 15) {
      const group = zones.find(([id]) => Number(id) === groupId);
      if (group && groupIsOn(group[1])) return zoneName(group[0], group[1]);
      if (group) return controlRoomName(ac, zones);
      return `Zone ${groupId + 1}`;
    }
    if (sensor === 254) return "AC";
    if (sensor === 144) return "Touchpad 1";
    if (sensor === 145) return "Touchpad 2";
  }
  return controlRoomName(ac, zones);
}

export function thermostatFor(ac, zones, integrations = {}) {
  const temperatures = resolveTemperatureState({ac, zones, integrations});
  return {
    min: temperatures.min,
    max: temperatures.max,
    current: temperatures.indoor.value,
    setpoint: temperatures.setpoint.value,
    temperatures
  };
}

export function acSourceHint(ac, zones, thermostat) {
  const selector = finite(ac?.settings?.ctrl_thermostat);
  const activeSensorZones = zones.filter(([_id, group]) => groupIsOn(group) && group?.status?.has_sensor === true);
  if (selector !== null && selector !== 255) return `Thermostat selector ${selector}`;
  if (activeSensorZones.length > 1) return `${activeSensorZones.length} active room sensors averaged`;
  if (activeSensorZones.length === 1) return `${zoneName(activeSensorZones[0][0], activeSensorZones[0][1])} sensor`;
  return thermostat.current === null ? "No live room sensor" : "Current room temperature";
}

export function aggregateTemperatureHistory(zones, thermostat) {
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
  const current = finite(thermostat?.current);
  if (!entries.length && current !== null && activeZones.length) {
    entries.push({ts: Math.floor(Date.now() / 1000), temperature: current, zone_count: activeZones.length});
  }
  return entries;
}

export function thermalCallActive(current, setpoint, status) {
  const mode = modeKey(status?.mode);
  const tolerance = 0.15;
  if (mode === "fan" || current === null || setpoint === null || status?.power_on !== true) return false;
  if (mode === "cool" || mode === "dry") return current > setpoint + tolerance;
  if (mode === "heat") return current < setpoint - tolerance;
  return Math.abs(setpoint - current) > tolerance;
}

export function plannedTemperatureEntries(historyEntries, thermostat, status, activeZoneCount) {
  const setpoint = finite(thermostat?.setpoint);
  const current = finite(historyEntries.at(-1)?.temperature) ?? finite(thermostat?.current);
  if (setpoint === null || current === null || !activeZoneCount || status?.power_on !== true || modeKey(status?.mode) === "fan") return [];
  const delta = setpoint - current;
  const startTs = finite(historyEntries.at(-1)?.ts) ?? Math.floor(Date.now() / 1000);
  return Array.from({length: 6}, (_item, index) => {
    const progress = (index + 1) / 6;
    const eased = 1 - ((1 - progress) ** 2);
    return {ts: startTs + ((index + 1) * 300), temperature: current + (delta * eased), planned: true};
  });
}

export function planActionActive(entry) {
  const action = String(entry?.action || "").toLowerCase();
  const power = finite(entry?.power_fraction);
  return (action && !["idle", "off", "none", "0"].includes(action)) || (power !== null && power > 0.01);
}

export function runtimeForecastPlan(adaptiveState, acId) {
  const plans = adaptiveState?.learning?.plans || adaptiveState?.plans || {};
  const plan = plans?.[String(acId)] || plans?.[Number(acId)];
  const series = plan?.runtime_forecast?.series;
  if (!Array.isArray(series) || !series.length) return null;
  const entries = series.map((point) => {
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
  }).filter(Boolean);
  if (!entries.length) return null;
  return {entries, setpoint: firstFinite(entries[0]?.setpoint, plan.target), callActive: entries.some(planActionActive), label: "Runtime plan"};
}

export function zoneForecastPlan(adaptiveState, zones) {
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
  return {entries, setpoint: null, callActive: entries.some(planActionActive), label: "Zone plan"};
}

export const availableTemperaturePlan = (adaptiveState, acId, zones) => runtimeForecastPlan(adaptiveState, acId) || zoneForecastPlan(adaptiveState, zones);

export function temperatureChartPath(entries, domain, offset = 0, total = entries.length) {
  if (!entries.length) return "";
  const span = Math.max(1, domain.max - domain.min);
  const denominator = Math.max(1, total - 1);
  return entries.map((entry, index) => {
    const x = total === 1 ? 120 : ((index + offset) / denominator) * 120;
    const y = 24 - ((Number(entry.temperature) - domain.min) / span) * 18;
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

export function temperatureChart(zones, thermostat, status, adaptiveState, acId) {
  const activeZoneCount = zones.filter(([_id, group]) => groupIsOn(group)).length;
  const historyEntries = aggregateTemperatureHistory(zones, thermostat);
  const suppliedPlan = availableTemperaturePlan(adaptiveState, acId, zones);
  const planEntries = suppliedPlan?.entries?.length ? suppliedPlan.entries : [];
  const planSeries = historyEntries.length && planEntries.length ? [historyEntries.at(-1), ...planEntries] : [];
  const current = finite(historyEntries.at(-1)?.temperature) ?? finite(thermostat?.current);
  const callActive = suppliedPlan?.entries?.length ? suppliedPlan.callActive : thermalCallActive(current, finite(thermostat?.setpoint), status);
  const values = [...historyEntries, ...planEntries].map((entry) => finite(entry?.temperature)).filter((value) => value !== null);
  const setpoint = firstFinite(suppliedPlan?.setpoint, thermostat?.setpoint);
  if (setpoint !== null) values.push(setpoint);
  if (!values.length) return {historyEntries, planEntries, historyPath: "", planPath: "", setpointPath: "", callAreaPath: "", callLabel: "No active zone demand"};
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

export function groupsFromBitmap(low = 0, high = 0) {
  const groups = [];
  for (let index = 0; index < 8; index += 1) if (Number(low) & (1 << index)) groups.push(index);
  for (let index = 0; index < 8; index += 1) if (Number(high) & (1 << index)) groups.push(index + 8);
  return groups;
}

export const bitmapFromGroups = (groupIds) => groupIds.reduce((mask, group) => mask | (1 << Number(group)), 0);

export function splitGroupBitmap(groupIds) {
  const low = [];
  const high = [];
  groupIds.forEach((group) => {
    if (group < 8) low.push(group);
    else high.push(group - 8);
  });
  return {groups_1_8_bitmap: bitmapFromGroups(low), groups_9_16_bitmap: bitmapFromGroups(high)};
}

export function adaptiveMetric(label, value) {
  return {label, value: value === undefined || value === null || value === "" ? "-" : String(value)};
}

export function sensorRowsFromState({rootState = {}, system = {}, groupEntries = []} = {}) {
  const stateRows = Array.isArray(rootState.sensor_view) ? rootState.sensor_view : [];
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

export const sensorKindLabel = (kind) => ({rf: "RF Sensor", touchpad: "Touchpad", supply_air: "Supply Air"}[kind] || title(kind || "sensor"));
