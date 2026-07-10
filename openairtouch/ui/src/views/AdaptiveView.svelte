<script>
  import Subnav from "../components/Subnav.svelte";
  import { analyticsChartData, lineClass } from "../lib/adaptiveChart.js";
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

  const surfaceActive = (label, strategy) => (
    (label === "Environment" && strategy === "weather")
    || (label === "Zone" && strategy === "zone")
    || (label === "Hybrid" && strategy === "hybrid")
  );
  function analyticsCardTitle(card = {}) {
    return card.title || "Analytics";
  }
  function analyticsChartTitle(card = {}, chart = {}) {
    const label = analyticsCardTitle(card);
    if (!label) return chart.title;
    if (!chart.title || chart.title.includes(label)) return label || chart.title;
    return `${label} - ${chart.title}`;
  }
  function analyticsFlags(card = {}) {
    const state = String(card.state || "").toLowerCase();
    return (Array.isArray(card.flags) ? card.flags : []).filter((flag) => {
      const normalized = String(flag || "").toLowerCase();
      return normalized !== state && normalized !== "ready" && normalized !== "learning";
    });
  }
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
          <span>{uiSummary.forecast?.headline || title(uiSummary.intent)}</span>
          <span>{uiSummary.control?.headline || title(uiSummary.authority)}</span>
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
          <label class="field">Allow AC Power On<select id="adaptive-allow-ac-power-on"><option value="true" selected={adaptiveConfig.allow_ac_power_on !== false}>Yes</option><option value="false" selected={adaptiveConfig.allow_ac_power_on === false}>No</option></select></label>
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
        <div class="chip-grid">
          {#each zoneEntries as [id, group]}
            <label class="check-row"><input type="checkbox" data-adaptive-outside-air-zone value={Number(id)} checked={(adaptiveConfig.outside_air_zones || []).map(Number).includes(Number(id))} /><span>{zoneName(id, group)}</span></label>
          {/each}
        </div>
      </article>
      <article class="summary-card editor-card adaptive-config-card">
        <div class="card-title">Timing And Model Tuning</div>
        <div class="field-grid">
          <label class="field">Check Interval<input id="adaptive-check-interval" type="number" min="5" max="3600" value={adaptiveConfig.check_interval ?? 60} /></label>
          <label class="field">Command Cooldown<input id="adaptive-command-cooldown" type="number" min="1" max="7200" value={adaptiveConfig.command_cooldown ?? 300} /></label>
          <label class="field">Model Horizon<input id="adaptive-mpc-horizon-hours" type="number" min="1" max="24" value={adaptiveConfig.mpc_horizon_hours ?? 6} /></label>
          <label class="field">Hybrid Max Boost<input id="adaptive-hybrid-max-boost-degrees" type="number" min="0" max="5" step="1" value={adaptiveConfig.hybrid_max_boost_degrees ?? 2} /></label>
          <label class="field">Minimum Run<input id="adaptive-compressor-min-run-time" type="number" min="0" value={adaptiveConfig.compressor_min_run_time ?? 0} /></label>
          <label class="field">Minimum Off<input id="adaptive-compressor-min-off-time" type="number" min="0" value={adaptiveConfig.compressor_min_off_time ?? 0} /></label>
        </div>
      </article>
      <div class="service-actions adaptive-config-actions">
        <button type="button" class="action-primary" disabled={pendingKey === "adaptive-save"} on:click={onSaveConfig}>Save Adaptive</button>
        <button type="button" disabled={pendingKey === "adaptive-model-reset_all-all"} on:click={() => onModelAction("reset_all")}>Reset Models</button>
      </div>
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
              <div class="card-title">{analyticsCardTitle(card)}</div>
              <div class="hero-detail">{card.state}</div>
            </div>
            <div class="pill-row-inline">
              {#each analyticsFlags(card) as flag}
                <span>{flag}</span>
              {/each}
            </div>
          </div>
          <div class="analytics-sparkline" class:not-meaningful={!chart.meaningful}>
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
            <div class="analytics-sparkline-meta"><span>{analyticsChartTitle(card, chart)}</span><span>{chart.hasData ? chart.summary : "No chart data"}</span></div>
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
