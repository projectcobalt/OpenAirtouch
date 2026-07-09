<script>
  import Subnav from "../components/Subnav.svelte";
  import { validateAdaptiveUiContract } from "../lib/adaptiveUiContract.js";
  import { title } from "../lib/format.js";

  export let options = [];
  export let activeAdaptiveView = "status";
  export let adaptiveUi = {};
  export let adaptiveConfig = {};
  export let groupEntries = [];
  export let selectedZones = [];
  export let pendingKey = "";
  export let groupIsSpill = () => false;
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
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
      return {hasData: false, actualPath: "", forecastPath: ""};
    }
    const domain = [Math.min(...values), Math.max(...values)];
    const total = actual.length + forecastEntries.length;
    const actualPath = chartPath(actual, domain, 0, total);
    const forecastPath = chartPath(forecastEntries, domain, Math.max(0, actual.length - 1), total);
    return {
      hasData: !!(actualPath || forecastPath),
      actualPath,
      forecastPath
    };
  }
  const surfaceActive = (label, strategy) => (
    (label === "Environment" && strategy === "weather")
    || (label === "Zone" && strategy === "zone")
    || (label === "Hybrid" && strategy === "hybrid")
  );

  $: uiSummary = adaptiveUi.summary || {};
  $: uiSurfaces = adaptiveUi.surfaces || {};
  $: contractErrors = validateAdaptiveUiContract(adaptiveUi);
  $: contractReady = contractErrors.length === 0;
  $: zoneEntries = selectedZones.length ? selectedZones : groupEntries.filter(([_id, group]) => !groupIsSpill(group));
  $: activeMode = uiSummary.mode;
  $: activeStrategy = uiSummary.strategy;
  $: surfaceCards = [
    ["Environment", uiSurfaces.environment],
    ["Zone", uiSurfaces.zone],
    ["Hybrid", uiSurfaces.hybrid]
  ];
  $: statusItems = Array.isArray(adaptiveUi.metrics) ? adaptiveUi.metrics : [];
  $: analyticsZones = Array.isArray(adaptiveUi.analytics?.zones) ? adaptiveUi.analytics.zones : [];
</script>

<section class="cards-view">
  <Subnav {options} active={activeAdaptiveView} on:change={(event) => onView(event.detail)} />
  <div class="page-divider"></div>

  {#if activeAdaptiveView === "status"}
    <div class="page-kicker">Current Intent</div>
    {#if !contractReady}
      <div class="intent-card contract-error-card">
        <div>
          <strong>Adaptive UI Contract Missing</strong>
          <p>The backend did not provide the required adaptive.ui contract for this page.</p>
        </div>
        <div class="model-badge-grid compact">
          {#each contractErrors as issue}
            <span class="model-badge"><b>Missing</b>{issue}</span>
          {/each}
        </div>
      </div>
    {:else}
      <div class="intent-card">
        <div>
          <strong>{uiSummary.headline}</strong>
          <p>{uiSummary.detail}</p>
        </div>
        <div class="pill-row-inline">
          <span>{title(activeMode)}</span>
          <span>{title(activeStrategy)}</span>
          <span>{title(uiSummary.intent)}</span>
          <span>{title(uiSummary.authority)}</span>
        </div>
      </div>
      <div class="adaptive-surface-grid">
        {#each surfaceCards as [label, surface]}
          <article
            class="summary-card adaptive-surface-card"
            class:active-surface={surfaceActive(label, activeStrategy)}
            data-adaptive-surface={label}
          >
            <div class="card-head">
              <div>
                <div class="hero-kicker">{label}</div>
                <div class="card-title">{surface.headline}</div>
              </div>
              <span class:selected-pill={surfaceActive(label, activeStrategy)}>{label}</span>
            </div>
            <div class="hero-detail">{surface.detail}</div>
            <div class="model-badge-grid compact">
              {#each surface.fields as field}
                <span class="model-badge"><b>{field.label}</b>{field.value}</span>
              {/each}
            </div>
          </article>
        {/each}
      </div>
      <div class="summary-grid adaptive-status-strip">
        {#each statusItems as item}
          <article class="summary-card metric-card"><span>{item.label}</span><strong>{item.value}</strong></article>
        {/each}
      </div>
    {/if}
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
          <label class="field">Dry Humidity Threshold<input id="adaptive-dry-humidity-threshold" type="number" min="30" max="100" value={adaptiveConfig.dry_humidity_threshold ?? 70} /></label>
          <label class="field">CO2 Ventilation Threshold<input id="adaptive-co2-ventilation-threshold" type="number" min="400" max="5000" step="50" value={adaptiveConfig.co2_ventilation_threshold_ppm ?? 1000} /></label>
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
    {#if !contractReady}
      <div class="intent-card contract-error-card">
        <div>
          <strong>Adaptive UI Contract Missing</strong>
          <p>The backend did not provide the required adaptive.ui analytics contract for this page.</p>
        </div>
        <div class="model-badge-grid compact">
          {#each contractErrors as issue}
            <span class="model-badge"><b>Missing</b>{issue}</span>
          {/each}
        </div>
      </div>
    {:else}
      <div class="analytics-list">
      {#each analyticsZones as zone}
        {@const id = zone.id}
        {@const sparkline = adaptiveSparklineData(zone.series.history, zone.series.forecast)}
        <article class="summary-card analytics-row" class:ready={zone.ready} class:learning={zone.learning}>
          <div class="analytics-row-status">
            <div>
              <div class="card-title">{zoneName(id)}</div>
              <div class="hero-detail">{zone.state}</div>
            </div>
            <div class="pill-row-inline">
              {#each zone.flags as flag}
                <span>{flag}</span>
              {/each}
            </div>
          </div>
          <div class="analytics-sparkline">
            <svg class="temp-line" viewBox="0 0 160 44" preserveAspectRatio="none" aria-hidden="true">
              <line class="axis" x1="0" y1="28" x2="160" y2="28"></line>
              <line class="now-line" x1="62" y1="4" x2="62" y2="40"></line>
              {#if sparkline.actualPath}<path d={sparkline.actualPath}></path>{/if}
              {#if sparkline.forecastPath}<path class="prediction-line" d={sparkline.forecastPath}></path>{/if}
            </svg>
            <div class="analytics-sparkline-meta"><span>{zone.series.meta}</span><span>{sparkline.hasData ? zone.series.label : "No chart data"}</span></div>
          </div>
          <div class="model-badge-grid">
            {#each zone.badges.slice(0, 6) as badge}
              <span class="model-badge"><b>{badge.label}</b>{badge.value}</span>
            {/each}
          </div>
          <div class="service-actions">
            <button type="button" disabled={pendingKey === `adaptive-model-accelerate_zone-${id}`} on:click={() => onModelAction("accelerate_zone", Number(id))}>{zone.accelerated_learning ? "Normal" : "Fast"}</button>
            <button type="button" class="action-danger" disabled={pendingKey === `adaptive-model-reset_zone-${id}`} on:click={() => onModelAction("reset_zone", Number(id))}>Reset</button>
          </div>
        </article>
      {/each}
    </div>
    {/if}
  {/if}
</section>
