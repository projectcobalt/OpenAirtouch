<script>
  import Subnav from "../components/Subnav.svelte";
  import { tempText, title } from "../lib/format.js";

  export let options = [];
  export let activeAdaptiveView = "status";
  export let adaptive = {};
  export let adaptiveConfig = {};
  export let adaptiveEnvironment = {};
  export let adaptiveZoneIntent = {};
  export let adaptiveHybridIntent = {};
  export let adaptiveReadyCount = 0;
  export let adaptiveLearningCount = 0;
  export let adaptiveLearningZones = {};
  export let groupEntries = [];
  export let selectedZones = [];
  export let pendingKey = "";
  export let adaptiveHeadline = () => "Adaptive";
  export let adaptiveReason = () => "";
  export let adaptiveMetric = (label, value) => ({label, value});
  export let adaptiveOwnership = () => "-";
  export let groupIsSpill = () => false;
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let modelBadges = () => [];
  export let onView = () => {};
  export let onSaveConfig = () => {};
  export let onModelAction = () => {};

  const finite = (value) => {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  };
  const pointValue = (point, keys) => {
    if (typeof point === "number") return keys.includes("actual") || keys.includes("forecast") ? finite(point) : null;
    if (!point || typeof point !== "object") return null;
    for (const key of keys) {
      const value = finite(point[key]);
      if (value !== null) return value;
    }
    return null;
  };
  const chartEntries = (items = [], keys, limit = 96) => (Array.isArray(items) ? items : [])
    .map((point, index) => ({x: finite(point?.ts) ?? index, value: pointValue(point, keys)}))
    .filter((point) => point.value !== null)
    .slice(-limit);
  const chartPath = (entries, domain, offset = 0, total = entries.length) => {
    if (entries.length < 2) return "";
    const [min, max] = domain;
    const spread = Math.max(1, max - min);
    return entries.map((entry, index) => {
      const x = ((index + offset) / Math.max(1, total - 1)) * 160;
      const y = 40 - (((entry.value - min) / spread) * 32);
      return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ");
  };
  function adaptiveSparklineData(history = [], forecast = []) {
    const actual = chartEntries(history, ["temperature", "room_temperature", "actual", "value"], 48);
    const inferredForecast = chartEntries(history, ["prediction", "predicted_temperature", "predicted"], 48);
    const future = chartEntries(forecast, ["prediction", "predicted_temperature", "predicted", "temperature", "value"], 96);
    const forecastEntries = future.length ? future : inferredForecast.map((point) => ({...point}));
    const values = [...actual, ...forecastEntries].map((point) => point.value);
    if (values.length < 2) {
      return {hasData: false, actualPath: "", forecastPath: "", label: `${actual.length + forecastEntries.length} points`};
    }
    const domain = [Math.min(...values), Math.max(...values)];
    const total = actual.length + forecastEntries.length;
    const actualPath = chartPath(actual, domain, 0, total);
    const forecastPath = chartPath(forecastEntries, domain, Math.max(0, actual.length - 1), total);
    const latestActual = actual.at(-1)?.value;
    const latestForecast = forecastEntries.at(-1)?.value;
    return {
      hasData: !!(actualPath || forecastPath),
      actualPath,
      forecastPath,
      label: `${latestActual === undefined ? "-" : tempText(latestActual)} -> ${latestForecast === undefined ? "-" : tempText(latestForecast)}`
    };
  }
  const zoneIdSet = (value) => {
    if (Array.isArray(value)) return new Set(value.map(Number).filter(Number.isFinite));
    if (value && typeof value === "object") return new Set(Object.keys(value).map(Number).filter(Number.isFinite));
    return new Set();
  };
  const zoneInSet = (set, id) => set.has(Number(id));
  function analyticsZoneVisible(id, group) {
    const hasSensor = group.status?.has_sensor === true;
    if (hasSensor) return true;
    if (activeStrategy === "hybrid") return zoneInSet(controlZoneIds, id) || zoneInSet(activeDamperZoneIds, id);
    if (activeStrategy === "zone") return zoneInSet(controlZoneIds, id) || zoneInSet(activeSetpointZoneIds, id);
    return false;
  }
  function analyticsZoneState(id, group, learningZone = {}) {
    if (learningZone.last_skip_reason) return title(learningZone.last_skip_reason);
    if (learningZone.mpc_ready) return "Ready";
    if (group.status?.has_sensor) return "Learning";
    if (activeStrategy === "hybrid" && zoneInSet(activeDamperZoneIds, id)) return "Damper Active";
    if (zoneInSet(controlZoneIds, id)) return "Control Zone";
    return "No Temperature Sensor";
  }

  $: zoneEntries = selectedZones.length ? selectedZones : groupEntries.filter(([_id, group]) => !groupIsSpill(group));
  $: activeMode = adaptive.mode || adaptiveConfig.mode || "off";
  $: activeStrategy = adaptiveConfig.control_strategy || "weather";
  $: controlZoneIds = zoneIdSet(adaptiveConfig.control_zones || []);
  $: activeSetpointZoneIds = zoneIdSet(adaptive.active_groups || []);
  $: activeDamperZoneIds = zoneIdSet(adaptive.active_dampers || []);
  $: analyticsZoneEntries = zoneEntries.filter(([id, group]) => analyticsZoneVisible(id, group));
  $: activeControlCount = (adaptive.active_groups || []).length || (adaptive.active_dampers || []).length;
</script>

<section class="cards-view">
  <Subnav {options} active={activeAdaptiveView} on:change={(event) => onView(event.detail)} />
  <div class="page-divider"></div>

  {#if activeAdaptiveView === "status"}
    <div class="page-kicker">Current Intent</div>
    <div class="intent-card">
      <div>
        <strong>{adaptiveHeadline()}</strong>
        <p>{adaptiveReason()}</p>
      </div>
      <div class="pill-row-inline">
        <span>{title(activeMode)}</span>
        <span>{title(activeStrategy)}</span>
        {#if adaptive.weather_intent?.outside_air_intent || adaptive.mode_intent?.outside_air_intent}<span>Fresh Air</span>{/if}
        {#if adaptive.weather_intent?.pause_active}<span>Paused</span>{/if}
      </div>
    </div>
    <div class="adaptive-surface-grid">
      {#each [["Environment", adaptiveEnvironment], ["Zone", adaptiveZoneIntent], ["Hybrid", adaptiveHybridIntent]] as [label, surface]}
        <article
          class="summary-card adaptive-surface-card"
          class:active-surface={(label === "Environment" && activeStrategy === "weather") || (label === "Zone" && activeStrategy === "zone") || (label === "Hybrid" && activeStrategy === "hybrid")}
          data-adaptive-surface={label}
        >
          <div class="card-head">
            <div>
              <div class="hero-kicker">{label}</div>
              <div class="card-title">{surface.headline}</div>
            </div>
            <span class:selected-pill={(label === "Environment" && activeStrategy === "weather") || (label === "Zone" && activeStrategy === "zone") || (label === "Hybrid" && activeStrategy === "hybrid")}>{label}</span>
          </div>
          <div class="hero-detail">{surface.summary}</div>
          <div class="model-badge-grid compact">
            {#each surface.fields as field}
              <span class="model-badge"><b>{field.label}</b>{field.value}</span>
            {/each}
          </div>
        </article>
      {/each}
    </div>
    <div class="summary-grid adaptive-status-strip">
      {#each [
        adaptiveMetric("Authority", title(activeMode)),
        adaptiveMetric("Learning", `${adaptiveReadyCount} ready / ${adaptiveLearningCount} learning`),
        adaptiveMetric("Control", activeControlCount ? `${activeControlCount} active changes` : "Idle"),
        adaptiveMetric("Compressor", adaptive.compressor?.guard || adaptive.compressor?.state || "Idle"),
        adaptiveMetric("Ownership", adaptiveOwnership())
      ] as item}
        <article class="summary-card metric-card"><span>{item.label}</span><strong>{item.value}</strong></article>
      {/each}
    </div>
  {:else if activeAdaptiveView === "config"}
    <div class="card-grid" data-adaptive-config>
      <article class="summary-card editor-card adaptive-config-card">
        <div class="card-title">Authority</div>
        <div class="field-grid">
          <label class="field">Mode<select id="adaptive-mode"><option value="off" selected={(adaptiveConfig.mode || "off") === "off"}>Off</option><option value="recommend" selected={adaptiveConfig.mode === "recommend"}>Recommend</option><option value="adaptive" selected={adaptiveConfig.mode === "adaptive"}>Adaptive</option></select></label>
          <label class="field">Strategy<select id="adaptive-control-strategy"><option value="weather" selected={(adaptiveConfig.control_strategy || "weather") === "weather"}>Environment</option><option value="zone" selected={adaptiveConfig.control_strategy === "zone"}>Zone</option><option value="hybrid" selected={adaptiveConfig.control_strategy === "hybrid"}>Hybrid</option></select></label>
          <label class="field">Cooling Margin<input id="adaptive-cool-diff" type="number" min="0" max="15" value={adaptiveConfig.cool_diff ?? 4} /></label>
          <label class="field">Cooling Comfort<input id="adaptive-cool-comfort-temp" type="number" min="16" max="32" value={adaptiveConfig.cool_comfort_temp ?? 24} /></label>
          <label class="field">Heating Margin<input id="adaptive-heat-diff" type="number" min="0" max="15" value={adaptiveConfig.heat_diff ?? 4} /></label>
          <label class="field">Heating Comfort<input id="adaptive-heat-comfort-temp" type="number" min="16" max="32" value={adaptiveConfig.heat_comfort_temp ?? 20} /></label>
        </div>
      </article>
      <article class="summary-card editor-card adaptive-config-card">
        <div class="card-title">Control Zones</div>
        <div class="chip-grid">
          {#each zoneEntries as [id, group]}
            <label class="check-row"><input type="checkbox" data-adaptive-control-zone value={Number(id)} checked={(adaptiveConfig.control_zones || []).map(Number).includes(Number(id))} /><span>{zoneName(id, group)}</span></label>
          {/each}
        </div>
      </article>
      <article class="summary-card editor-card adaptive-config-card">
        <div class="card-title">Outside Air Zones</div>
        <div class="hero-detail">Fresh-air actuator selection lives here, not in spill configuration.</div>
        <div class="chip-grid">
          {#each zoneEntries as [id, group]}
            <label class="check-row"><input type="checkbox" data-adaptive-outside-air-zone value={Number(id)} checked={(adaptiveConfig.outside_air_zones || []).map(Number).includes(Number(id))} /><span>{zoneName(id, group)}</span></label>
          {/each}
        </div>
      </article>
      <article class="summary-card editor-card adaptive-config-card">
        <details class="advanced-panel">
          <summary>Timing And Model Tuning</summary>
          <div class="field-grid">
            <label class="field">Check Interval<input id="adaptive-check-interval" type="number" min="5" max="3600" value={adaptiveConfig.check_interval ?? 60} /></label>
            <label class="field">Command Cooldown<input id="adaptive-command-cooldown" type="number" min="1" max="7200" value={adaptiveConfig.command_cooldown ?? 300} /></label>
            <label class="field">Model Horizon<input id="adaptive-mpc-horizon-hours" type="number" min="1" max="24" value={adaptiveConfig.mpc_horizon_hours ?? 6} /></label>
            <label class="field">Minimum Run<input id="adaptive-compressor-min-run-time" type="number" min="0" value={adaptiveConfig.compressor_min_run_time ?? 0} /></label>
            <label class="field">Minimum Off<input id="adaptive-compressor-min-off-time" type="number" min="0" value={adaptiveConfig.compressor_min_off_time ?? 0} /></label>
          </div>
        </details>
        <div class="service-actions">
          <button type="button" class="action-primary" disabled={pendingKey === "adaptive-save"} on:click={onSaveConfig}>Save Adaptive</button>
          <button type="button" disabled={pendingKey === "adaptive-model-reset_all-all"} on:click={() => onModelAction("reset_all")}>Reset Models</button>
        </div>
      </article>
    </div>
  {:else}
    <div class="analytics-list">
      {#each analyticsZoneEntries as [id, group]}
        {@const learningZone = adaptiveLearningZones[String(id)] || {}}
        {@const history = adaptive.learning?.analytics?.[String(id)] || adaptive.learning?.analytics?.[Number(id)] || []}
        {@const forecast = adaptive.learning?.forecasts?.[String(id)] || adaptive.learning?.forecasts?.[Number(id)] || []}
        {@const sparkline = adaptiveSparklineData(history, forecast)}
        <article class="summary-card analytics-row" class:ready={learningZone.mpc_ready} class:learning={learningZone.learn}>
          <div class="analytics-row-status">
            <div>
              <div class="card-title">{zoneName(id, group)}</div>
              <div class="hero-detail">{analyticsZoneState(id, group, learningZone)}</div>
            </div>
            <div class="pill-row-inline">
              {#if zoneInSet(controlZoneIds, id)}<span>Control</span>{/if}
              {#if zoneInSet(activeDamperZoneIds, id)}<span>Damper</span>{/if}
              {#if learningZone.mpc_ready}<span>Ready</span>{/if}
              {#if learningZone.learn}<span>Learning</span>{/if}
            </div>
          </div>
          <div class="analytics-sparkline">
            <svg class="temp-line" viewBox="0 0 160 44" preserveAspectRatio="none" aria-hidden="true">
              <line class="axis" x1="0" y1="28" x2="160" y2="28"></line>
              <line class="now-line" x1="62" y1="4" x2="62" y2="40"></line>
              {#if sparkline.actualPath}<path d={sparkline.actualPath}></path>{/if}
              {#if sparkline.forecastPath}<path class="prediction-line" d={sparkline.forecastPath}></path>{/if}
            </svg>
            <div class="analytics-sparkline-meta"><span>History / Now / Forecast</span><span>{sparkline.hasData ? sparkline.label : "No chart data"}</span></div>
          </div>
          <div class="model-badge-grid">
            {#each modelBadges(learningZone).slice(0, 6) as badge}
              <span class="model-badge"><b>{badge.label}</b>{badge.value}</span>
            {/each}
          </div>
          <div class="service-actions">
            <button type="button" disabled={pendingKey === `adaptive-model-accelerate_zone-${id}`} on:click={() => onModelAction("accelerate_zone", Number(id))}>{learningZone.accelerated_learning ? "Normal" : "Fast"}</button>
            <button type="button" class="action-danger" disabled={pendingKey === `adaptive-model-reset_zone-${id}`} on:click={() => onModelAction("reset_zone", Number(id))}>Reset</button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>
