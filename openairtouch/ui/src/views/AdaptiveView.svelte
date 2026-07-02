<script>
  import Subnav from "../components/Subnav.svelte";
  import ViewHeading from "../components/ViewHeading.svelte";
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

  $: zoneEntries = selectedZones.length ? selectedZones : groupEntries.filter(([_id, group]) => !groupIsSpill(group));
</script>

<section class="cards-view">
  <ViewHeading title="Adaptive" detail={adaptiveHeadline()} />
  <Subnav {options} active={activeAdaptiveView} on:change={(event) => onView(event.detail)} />

  {#if activeAdaptiveView === "status"}
    <div class="intent-card">
      <div>
        <span>Current Intent</span>
        <strong>{adaptiveHeadline()}</strong>
        <p>{adaptiveReason()}</p>
      </div>
      <div class="pill-row-inline">
        <span>{title(adaptive.mode || adaptiveConfig.mode || "off")}</span>
        <span>{title(adaptiveConfig.control_strategy || "weather_setpoint")}</span>
        {#if adaptive.weather_intent?.outside_air_intent || adaptive.mode_intent?.outside_air_intent}<span>Fresh Air</span>{/if}
        {#if adaptive.weather_intent?.pause_active}<span>Paused</span>{/if}
      </div>
    </div>
    <div class="adaptive-surface-grid">
      {#each [["Environment", adaptiveEnvironment], ["Zone", adaptiveZoneIntent], ["Hybrid", adaptiveHybridIntent]] as [label, surface]}
        <article class="summary-card adaptive-surface-card" data-adaptive-surface={label}>
          <div class="card-head">
            <div>
              <div class="hero-kicker">{label}</div>
              <div class="card-title">{surface.headline}</div>
            </div>
            <span class:selected-pill={label === "Hybrid" && adaptiveConfig.control_strategy === "hybrid_damper_mpc"}>{label}</span>
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
    <div class="summary-grid">
      {#each [
        adaptiveMetric("Authority", title(adaptive.mode || adaptiveConfig.mode || "off")),
        adaptiveMetric("Learning", `${adaptiveReadyCount} ready / ${adaptiveLearningCount} learning`),
        adaptiveMetric("Control", (adaptive.active_groups || []).length ? `${adaptive.active_groups.length} active zones` : "Idle"),
        adaptiveMetric("Compressor", adaptive.compressor?.guard || adaptive.compressor?.state || "Idle"),
        adaptiveMetric("Live Inputs", adaptive.outside_temperature === undefined ? "Outside unavailable" : `Outside ${tempText(adaptive.outside_temperature, 1)}`),
        adaptiveMetric("Expected Runtime", adaptive.runtime_hours === undefined ? adaptive.projected_runtime_hours === undefined ? "-" : `${Number(adaptive.projected_runtime_hours).toFixed(1)} h` : `${Number(adaptive.runtime_hours).toFixed(1)} h`),
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
          <label class="field">Mode<select id="adaptive-mode"><option value="off" selected={(adaptiveConfig.mode || "off") === "off"}>Off</option><option value="recommend" selected={adaptiveConfig.mode === "recommend"}>Recommend</option><option value="auto_off" selected={adaptiveConfig.mode === "auto_off"}>Auto Off</option><option value="adaptive" selected={adaptiveConfig.mode === "adaptive"}>Adaptive</option></select></label>
          <label class="field">Strategy<select id="adaptive-control-strategy"><option value="weather_setpoint" selected={(adaptiveConfig.control_strategy || "weather_setpoint") === "weather_setpoint"}>Environment</option><option value="mpc_setpoint" selected={adaptiveConfig.control_strategy === "mpc_setpoint"}>Zone</option><option value="hybrid_damper_mpc" selected={adaptiveConfig.control_strategy === "hybrid_damper_mpc"}>Hybrid</option></select></label>
          <label class="field">Cool Diff<input id="adaptive-cool-diff" type="number" min="0" max="15" value={adaptiveConfig.cool_diff ?? 4} /></label>
          <label class="field">Cool Comfort<input id="adaptive-cool-comfort-temp" type="number" min="16" max="32" value={adaptiveConfig.cool_comfort_temp ?? 24} /></label>
          <label class="field">Heat Diff<input id="adaptive-heat-diff" type="number" min="0" max="15" value={adaptiveConfig.heat_diff ?? 4} /></label>
          <label class="field">Heat Comfort<input id="adaptive-heat-comfort-temp" type="number" min="16" max="32" value={adaptiveConfig.heat_comfort_temp ?? 20} /></label>
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
        <div class="card-title">Timing</div>
        <div class="field-grid">
          <label class="field">Check Interval<input id="adaptive-check-interval" type="number" min="5" max="3600" value={adaptiveConfig.check_interval ?? 60} /></label>
          <label class="field">Command Cooldown<input id="adaptive-command-cooldown" type="number" min="1" max="7200" value={adaptiveConfig.command_cooldown ?? 300} /></label>
          <label class="field">MPC Horizon<input id="adaptive-mpc-horizon-hours" type="number" min="1" max="24" value={adaptiveConfig.mpc_horizon_hours ?? 6} /></label>
          <label class="field">Minimum Run<input id="adaptive-compressor-min-run-time" type="number" min="0" value={adaptiveConfig.compressor_min_run_time ?? 0} /></label>
          <label class="field">Minimum Off<input id="adaptive-compressor-min-off-time" type="number" min="0" value={adaptiveConfig.compressor_min_off_time ?? 0} /></label>
        </div>
        <div class="service-actions">
          <button type="button" class="action-primary" disabled={pendingKey === "adaptive-save"} on:click={onSaveConfig}>Save Adaptive</button>
          <button type="button" disabled={pendingKey === "adaptive-model-reset_all-all"} on:click={() => onModelAction("reset_all")}>Reset Models</button>
        </div>
      </article>
    </div>
  {:else}
    <div class="analytics-list">
      {#each zoneEntries as [id, group]}
        {@const learningZone = adaptiveLearningZones[String(id)] || {}}
        <article class="summary-card analytics-row" class:ready={learningZone.mpc_ready} class:learning={learningZone.learn}>
          <div class="analytics-row-status">
            <div>
              <div class="card-title">{zoneName(id, group)}</div>
              <div class="hero-detail">{learningZone.last_skip_reason ? title(learningZone.last_skip_reason) : learningZone.mpc_ready ? "Ready" : group.status?.has_sensor ? "Learning" : "No Temperature Sensor"}</div>
            </div>
            <div class="pill-row-inline">
              {#if (adaptiveConfig.control_zones || []).map(Number).includes(Number(id))}<span>Control</span>{/if}
              {#if learningZone.mpc_ready}<span>Ready</span>{/if}
              {#if learningZone.learn}<span>Learning</span>{/if}
            </div>
          </div>
          <svg class="analytics-sparkline" viewBox="0 0 220 48" preserveAspectRatio="none" aria-label="History / Now / Forecast">
            <path class="spark-grid" d="M0 12 H220 M0 24 H220 M0 36 H220"></path>
            <path class="spark-line" d="M0 34 C30 30 45 16 76 20 C110 25 120 38 154 30 C184 22 194 18 220 16"></path>
            <line class="now-line" x1="150" y1="4" x2="150" y2="44"></line>
            <path class="prediction-line" d="M150 30 C170 28 190 20 220 16"></path>
          </svg>
          <div class="model-badge-grid">
            {#each modelBadges(learningZone) as badge}
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
