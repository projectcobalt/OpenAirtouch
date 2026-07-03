import { clamp, finite } from "./format.js";
import { acName, splitGroupBitmap, bitmapFromGroups } from "./selectors.js";

export function checkedValues(card, selector) {
  return Array.from(card?.querySelectorAll(selector) || [])
    .filter((input) => input.checked)
    .map((input) => Number(input.value ?? input.dataset.group ?? input.dataset.favouriteGroup));
}

export function timerFromCard(card, prefix) {
  const value = card?.querySelector(`[data-field="${prefix}-time"]`)?.value || "00:00";
  const [hour, minute] = value.split(":").map((item) => Number(item));
  return {
    enabled: card?.querySelector(`[data-field="${prefix}-enabled"]`)?.value === "true",
    hour: Number.isFinite(hour) ? hour : 0,
    minute: Number.isFinite(minute) ? minute : 0
  };
}

export function programRecordsFromState(programs = {}) {
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

export function acTimerRecordsFromState(acEntries = []) {
  return acEntries.map(([id, ac]) => {
    const timer = ac?.timer || {};
    return {
      ac: Number(id),
      on_timer: timer.on_timer || timer.timer || {enabled: false, hour: 0, minute: 0},
      off_timer: timer.off_timer || {enabled: false, hour: 0, minute: 0}
    };
  });
}

export function favouritePayload(card, id) {
  return {
    favourite: Number(id),
    name: card?.querySelector('[data-field="favourite-name"]')?.value || "",
    groups: checkedValues(card, "[data-favourite-group]")
  };
}

export const clearFavouritePayload = (id) => ({favourite: Number(id), name: "", groups: []});

export function programPayload(card, id, programs, system = {}) {
  const records = programRecordsFromState(programs);
  const programNumber = Number(id);
  const record = records.find((item) => Number(item.program) === programNumber) || {program: programNumber};
  record.name = card?.querySelector('[data-field="program-name"]')?.value || "";
  record.enabled = card?.querySelector('[data-field="program-enabled"]')?.value === "true";
  record.days_bitmap = bitmapFromGroups(checkedValues(card, "[data-program-day]"));
  Object.assign(record, splitGroupBitmap(checkedValues(card, "[data-program-zone]")));
  record.active_ac_bitmap = bitmapFromGroups(checkedValues(card, "[data-program-ac]"));
  record.on_setpoint = Number(card?.querySelector('[data-field="program-on-setpoint"]')?.value || 26);
  record.on_timer = timerFromCard(card, "on");
  record.off_timer = timerFromCard(card, "off");
  if (!records.some((item) => Number(item.program) === programNumber)) records.push(record);
  return {
    program_count: Number(system.program_count ?? records.length),
    linked_ac: !!system.programs_linked_ac,
    records
  };
}

export function clearProgramPayload(id, programs, system = {}) {
  const records = programRecordsFromState(programs);
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
  return {
    program_count: Number(system.program_count ?? records.length),
    linked_ac: !!system.programs_linked_ac,
    records
  };
}

export function acTimerPayload(card, id, acEntries) {
  const records = acTimerRecordsFromState(acEntries);
  const ac = Number(id);
  const record = records.find((item) => Number(item.ac) === ac) || {ac};
  record.on_timer = timerFromCard(card, "on");
  record.off_timer = timerFromCard(card, "off");
  if (!records.some((item) => Number(item.ac) === ac)) records.push(record);
  return {records, ac_count: records.length || 4};
}

export function adaptiveConfigPayload(card) {
  return {
    mode: card?.querySelector("#adaptive-mode")?.value || "off",
    control_strategy: card?.querySelector("#adaptive-control-strategy")?.value || "weather_setpoint",
    cool_diff: Number(card?.querySelector("#adaptive-cool-diff")?.value || 4),
    cool_comfort_temp: Number(card?.querySelector("#adaptive-cool-comfort-temp")?.value || 24),
    heat_diff: Number(card?.querySelector("#adaptive-heat-diff")?.value || 4),
    heat_comfort_temp: Number(card?.querySelector("#adaptive-heat-comfort-temp")?.value || 20),
    check_interval: Number(card?.querySelector("#adaptive-check-interval")?.value || 60),
    command_cooldown: Number(card?.querySelector("#adaptive-command-cooldown")?.value || 300),
    mpc_horizon_hours: Number(card?.querySelector("#adaptive-mpc-horizon-hours")?.value || 6),
    compressor_min_run_time: Number(card?.querySelector("#adaptive-compressor-min-run-time")?.value || 0),
    compressor_min_off_time: Number(card?.querySelector("#adaptive-compressor-min-off-time")?.value || 0),
    control_zones: checkedValues(card, "[data-adaptive-control-zone]"),
    outside_air_zones: checkedValues(card, "[data-adaptive-outside-air-zone]")
  };
}

export function sensorTemperaturePayload(card, sensor) {
  const temperature = Number(card?.querySelector("[data-sensor-temperature]")?.value);
  return Number.isFinite(temperature) ? {sensor: Number(sensor), temperature} : null;
}

export function groupingPayload(card, id) {
  return {
    group: Number(id),
    zone_start: Number(card?.querySelector('[data-field="zone-start"]')?.value || 0),
    zone_count: Number(card?.querySelector('[data-field="zone-count"]')?.value || 1),
    min_percent: Number(card?.querySelector('[data-field="min-percent"]')?.value || 0),
    thermostat: Number(card?.querySelector('[data-field="thermostat"]')?.value || 255)
  };
}

export const groupNamePayload = (card, id) => ({group: Number(id), name: card?.querySelector('[data-field="group-name"]')?.value || ""});

export function spillPayload(card) {
  const ac_spill_types = Array.from(card?.querySelectorAll("[data-spill-ac]") || [])
    .sort((a, b) => Number(a.dataset.spillAc) - Number(b.dataset.spillAc))
    .map((select) => Number(select.value));
  return {spill_groups: checkedValues(card, "[data-spill-group]"), ac_spill_types};
}

export function balanceValuesFromPage(root = document) {
  const values = Array(16).fill(0);
  root.querySelectorAll("[data-balance-number]").forEach((input) => {
    const zone = Number(input.dataset.balanceNumber);
    const value = Number(input.value);
    if (zone >= 0 && zone < values.length) values[zone] = value > 0 ? clamp(value, 5, 100) : 0;
  });
  return values;
}

export function stepBalanceInput(card, delta) {
  const input = card?.querySelector("[data-balance-number]");
  if (!input) return;
  const current = Number(input.value || 0);
  const stepped = current <= 0 && delta > 0 ? 5 : current + delta;
  const next = stepped < 5 ? 0 : clamp(stepped, 5, 100);
  input.value = String(next);
  const display = card?.querySelector("[data-balance-display]");
  if (display) display.textContent = next > 0 ? `${next}%` : "Disabled";
}

export function preferencePayload(card, system = {}) {
  const selectBool = (field, fallback = false) => {
    const input = card?.querySelector(`[data-field="${field}"]`);
    return input ? input.value === "true" : !!fallback;
  };
  const numberValue = (field, fallback = 0) => {
    const input = card?.querySelector(`[data-field="${field}"]`);
    return input ? Number(input.value || fallback || 0) : Number(fallback || 0);
  };
  return {
    system_name: card?.querySelector("#system-name-input")?.value || system.system_name || "",
    show_ac_errors: selectBool("show-ac-errors", system.show_ac_errors),
    show_outside_temp: selectBool("pref-show-outside-temp", system.show_outside_temp),
    show_control_sensor: selectBool("pref-show-control-sensor", system.show_control_sensor),
    use_fahrenheit: selectBool("use-fahrenheit", system.use_fahrenheit),
    location: numberValue("location", system.location ?? system.address_or_location ?? 0),
    screensaver_enabled: selectBool("screensaver-enabled", system.screensaver_enabled),
    screensaver_timeout: numberValue("screensaver-timeout", system.screensaver_timeout ?? 0)
  };
}

export function parametersPayload(card, system = {}, groupEntries = []) {
  const selectBool = (field, fallback = false) => {
    const input = card?.querySelector(`[data-field="${field}"]`);
    return input ? input.value === "true" : !!fallback;
  };
  const numberValue = (field, fallback = 0) => {
    const input = card?.querySelector(`[data-field="${field}"]`);
    return input ? Number(input.value || fallback || 0) : Number(fallback || 0);
  };
  return {
    group_count: numberValue("group-count", system.group_count ?? groupEntries.length ?? 1),
    damper_rpm: numberValue("damper-rpm", system.damper_rpm ?? 100),
    touchpad_1_location: numberValue("touchpad-1-location", system.touchpad_1_location ?? 255),
    touchpad_2_location: numberValue("touchpad-2-location", system.touchpad_2_location ?? 255),
    ac_button_blocked: selectBool("ac-button-blocked", system.ac_button_blocked),
    show_outside_temp: selectBool("param-show-outside-temp", system.show_outside_temp),
    lock_to_temp_control: selectBool("lock-to-temp-control", system.lock_to_temp_control),
    show_control_sensor: selectBool("param-show-control-sensor", system.show_control_sensor)
  };
}

export function servicePayload(card) {
  return {
    company: card?.querySelector("#service-company-input")?.value || "",
    phone: card?.querySelector("#service-phone-input")?.value || "",
    show_service_due: card?.querySelector('[data-field="show-service-due"]')?.value === "true",
    service_due_locked: card?.querySelector('[data-field="service-due-locked"]')?.value === "true",
    filter_clean_due: card?.querySelector('[data-field="filter-clean-due"]')?.value === "true",
    maintenance_due: card?.querySelector('[data-field="maintenance-due"]')?.value === "true",
    months: Number(card?.querySelector('[data-field="service-months"]')?.value || 0),
    days: Number(card?.querySelector('[data-field="service-days"]')?.value || 0),
    runtime_hours: Number(card?.querySelector('[data-field="service-runtime-hours"]')?.value || 0)
  };
}

export function acBaseRecordsFromState(acEntries = []) {
  return acEntries.map(([id, ac]) => ({
    ac: Number(id),
    group_start: Number(ac?.base?.group_start ?? 0),
    group_count: Number(ac?.base?.group_count ?? 0),
    brand: Number(ac?.base?.brand ?? 0),
    name: ac?.base?.name || acName(id, ac)
  }));
}

export function acSettingRecordsFromState(acEntries = []) {
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

export function acBasePayload(card, id, acEntries, system = {}) {
  const records = acBaseRecordsFromState(acEntries);
  const record = records.find((item) => Number(item.ac) === Number(id));
  if (!record) return null;
  record.name = card?.querySelector('[data-field="ac-name"]')?.value || record.name;
  record.group_start = Number(card?.querySelector('[data-field="ac-group-start"]')?.value || 0);
  record.group_count = Number(card?.querySelector('[data-field="ac-group-count"]')?.value || 0);
  record.brand = Number(card?.querySelector('[data-field="ac-brand"]')?.value || record.brand || 0);
  return {one_duct_system: !!system.one_duct_system, ac_count: records.length, records};
}

export function applyAcSettingsCard(record, card) {
  const field = (name) => card?.querySelector(`[data-field="${name}"]`);
  record.hide_spill_group = card?.querySelector('[data-field="hide-spill"]')?.value === "true";
  record.ctrl_thermostat = Number(card?.querySelector('[data-field="ctrl-thermostat"]')?.value || record.ctrl_thermostat || 0);
  record.cool_adjust = Number(card?.querySelector('[data-field="cool-adjust"]')?.value || 0);
  record.heat_adjust = Number(card?.querySelector('[data-field="heat-adjust"]')?.value || 0);
  record.min_setpoint = Number(card?.querySelector('[data-field="min-setpoint"]')?.value || 16);
  record.max_setpoint = Number(card?.querySelector('[data-field="max-setpoint"]')?.value || 30);
  record.auto_off = card?.querySelector('[data-field="auto-off"]')?.value === "true";
  record.on_time_limit = Number(card?.querySelector('[data-field="on-time-limit"]')?.value || 0);
  if (field("mode-auto")) {
    record.modes = {
      auto: field("mode-auto")?.value === "true",
      cool: field("mode-cool")?.value === "true",
      heat: field("mode-heat")?.value === "true",
      dry: field("mode-dry")?.value === "true",
      fan: field("mode-fan")?.value === "true"
    };
  }
  if (field("fan-auto")) {
    record.fan_values = {
      auto: Number(field("fan-auto")?.value || 0),
      quiet: Number(field("fan-quiet")?.value || 0),
      low: Number(field("fan-low")?.value || 1),
      medium: Number(field("fan-medium")?.value || 2),
      high: Number(field("fan-high")?.value || 3),
      powerful: Number(field("fan-powerful")?.value || 0),
      turbo: Number(field("fan-turbo")?.value || 0)
    };
  }
  if (field("selector-auto")) {
    record.selector_visibility = {
      auto: field("selector-auto")?.value === "true",
      touchpad_1: field("selector-touchpad_1")?.value === "true",
      touchpad_2: field("selector-touchpad_2")?.value === "true",
      average: field("selector-average")?.value === "true",
      economy: field("selector-economy")?.value === "true",
      groups_1_8_bitmap: Number(field("selector-groups-1")?.value || 0),
      groups_9_16_bitmap: Number(field("selector-groups-2")?.value || 0)
    };
  }
  return record;
}

export function acSettingsPayload(card, id, acEntries) {
  const records = acSettingRecordsFromState(acEntries);
  const record = records.find((item) => Number(item.ac) === Number(id));
  if (!record) return null;
  applyAcSettingsCard(record, card);
  return {records};
}

export function resetTempOffsetInputs(card) {
  const cool = card?.querySelector('[data-field="cool-adjust"]');
  const heat = card?.querySelector('[data-field="heat-adjust"]');
  if (cool) cool.value = 0;
  if (heat) heat.value = 0;
}

export function turboGroupPayload(card, id, system = {}, acEntries = []) {
  const current_groups = [];
  for (const record of system.turbo_group?.records || []) {
    current_groups[Number(record.ac)] = record.group === null || record.group === undefined ? 255 : Number(record.group);
  }
  return {
    ac: Number(id),
    group: Number(card?.querySelector('[data-field="turbo-group"]')?.value || 255),
    current_groups,
    one_duct_system: !!system.one_duct_system,
    ac_count: Math.max(1, acEntries.length)
  };
}

export function zonePayload(id, group, on) {
  const status = group?.status || {};
  return {
    group: Number(id),
    on,
    sensor_control: status.sensor_control !== false,
    setpoint: finite(status.setpoint) ?? 24,
    percentage: finite(status.percentage) ?? 100
  };
}
