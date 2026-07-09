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
  const lineClass = (kind = "") => `chart-line chart-line-${kind || "actual"}`;
  const chartValues = (chart = {}) => [
    ...(Array.isArray(chart.lines) ? chart.lines.flatMap((line) => (line.points || []).map((point) => finite(point.y)).filter((value) => value !== null)) : []),
    ...(Array.isArray(chart.bands) ? chart.bands.flatMap((band) => [finite(band.min), finite(band.max)]).filter((value) => value !== null) : [])
  ];
  const chartXs = (chart = {}) => [
    ...(Array.isArray(chart.lines) ? chart.lines.flatMap((line) => (line.points || []).map((point) => finite(point.x)).filter((value) => value !== null)) : []),
    ...(Array.isArray(chart.windows) ? chart.windows.flatMap((window) => [finite(window.start), finite(window.end)]).filter((value) => value !== null) : [])
  ];
  function analyticsChartData(chart = {}) {
    const values = chartValues(chart);
    const xs = chartXs(chart);
    const minY = values.length ? Math.min(...values) : 0;
    const maxY = values.length ? Math.max(...values) : 1;
    const pad = Math.max(0.5, (maxY - minY) * 0.18);
    const y0 = minY - pad;
    const y1 = maxY + pad;
    const minX = xs.length ? Math.min(...xs) : 0;
    const maxX = xs.length ? Math.max(...xs) : 1;
    const yScale = (value) => 40 - (((value - y0) / Math.max(1, y1 - y0)) * 32);
    const xScale = (value) => ((value - minX) / Math.max(1, maxX - minX)) * 160;
    const linePaths = (Array.isArray(chart.lines) ? chart.lines : []).map((line) => ({
      ...line,
      path: (line.points || [])
        .map((point, index) => {
          const x = finite(point.x);
          const y = finite(point.y);
          if (x === null || y === null) return "";
          return `${index ? "L" : "M"}${xScale(x).toFixed(1)} ${yScale(y).toFixed(1)}`;
        })
        .filter(Boolean)
        .join(" ")
    })).filter((line) => line.path);
    const bands = (Array.isArray(chart.bands) ? chart.bands : []).map((band) => {
      const top = yScale(finite(band.max) ?? finite(band.min) ?? 0);
      const bottom = yScale(finite(band.min) ?? finite(band.max) ?? 0);
      return {...band, y: Math.min(top, bottom), height: Math.max(1, Math.abs(bottom - top))};
    });
    const windows = (Array.isArray(chart.windows) ? chart.windows : []).map((window) => {
      const start = xScale(finite(window.start) ?? minX);
      const end = xScale(finite(window.end) ?? minX);
      return {...window, x: Math.min(start, end), width: Math.max(1, Math.abs(end - start))};
    });
    return {
      title: chart.title || "Analytics",
      summary: chart.summary || chart.empty_reason || "No chart data",
      hasData: chart.has_data === true && linePaths.length > 0,
      linePaths,
      bands,
      windows
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
  $: analyticsCards = Array.isArray(adaptiveUi.analytics?.cards) ? adaptiveUi.analytics.cards : [];
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
          <label class="field">Comfort Margin<input id="adaptive-comfort-margin" type="number" min="0" max="15" value={adaptiveConfig.comfort_margin ?? 4} /></label>
          <label class="check-row"><input id="adaptive-allow-ac-power-on" type="checkbox" checked={adaptiveConfig.allow_ac_power_on !== false} /><span>Allow AC Power On</span></label>
          <label class="field">Cooling Comfort<input id="adaptive-cool-comfort-temp" type="number" min="16" max="32" value={adaptiveConfig.cool_comfort_temp ?? 24} /></label>
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
            <label class="field">Hybrid Max Boost<input id="adaptive-hybrid-max-boost-degrees" type="number" min="0" max="5" step="1" value={adaptiveConfig.hybrid_max_boost_degrees ?? 2} /></label>
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
      {#each analyticsCards as card}
        {@const zoneId = card.zone_id}
        {@const chart = analyticsChartData(card.chart)}
        <article class="summary-card analytics-row" class:ready={card.ready} class:learning={card.learning} data-analytics-kind={card.kind}>
          <div class="analytics-row-status">
            <div>
              <div class="card-title">{card.title || (zoneId === undefined || zoneId === null ? "Analytics" : zoneName(zoneId))}</div>
              <div class="hero-detail">{card.state}</div>
            </div>
            <div class="pill-row-inline">
              {#each card.flags as flag}
                <span>{flag}</span>
              {/each}
            </div>
          </div>
          <div class="analytics-sparkline">
            <svg class="temp-line" viewBox="0 0 160 44" preserveAspectRatio="none" aria-hidden="true">
              <line class="axis" x1="0" y1="28" x2="160" y2="28"></line>
              {#each chart.bands as band}
                <rect class="chart-band" x="0" y={band.y} width="160" height={band.height}></rect>
              {/each}
              {#each chart.windows as window}
                <rect class="chart-window" x={window.x} y="5" width={window.width} height="35"></rect>
              {/each}
              {#each chart.linePaths as line}
                <path class={lineClass(line.kind)} d={line.path}></path>
              {/each}
            </svg>
            <div class="analytics-sparkline-meta"><span>{chart.title}</span><span>{chart.hasData ? chart.summary : "No chart data"}</span></div>
          </div>
          <div class="model-badge-grid">
            {#each card.badges.slice(0, 6) as badge}
              <span class="model-badge"><b>{badge.label}</b>{badge.value}</span>
            {/each}
          </div>
          {#if zoneId !== undefined && zoneId !== null}
            <div class="service-actions">
              <button type="button" disabled={pendingKey === `adaptive-model-accelerate_zone-${zoneId}`} on:click={() => onModelAction("accelerate_zone", Number(zoneId))}>{card.accelerated_learning ? "Normal" : "Fast"}</button>
              <button type="button" class="action-danger" disabled={pendingKey === `adaptive-model-reset_zone-${zoneId}`} on:click={() => onModelAction("reset_zone", Number(zoneId))}>Reset</button>
            </div>
          {/if}
        </article>
      {/each}
    </div>
    {/if}
  {/if}
</section>
