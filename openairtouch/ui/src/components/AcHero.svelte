<script>
  import { createEventDispatcher } from "svelte";
  import { modeName } from "../lib/airtouch.js";
  import { tempText } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let acOptions = [];
  export let selectedAcId = 0;
  export let selectedStatus = {};
  export let selectedThermostat = {};
  export let selectedHistoryEntries = [];
  export let selectedHistoryPath = "";
  export let selectedPlanEntries = [];
  export let selectedPlanPath = "";
  export let selectedSetpointPath = "";
  export let selectedCallAreaPath = "";
  export let selectedCallLabel = "";
  export let pendingKey = "";
  export let modeOptions = [];
  export let fanOptions = [];

  const dispatch = createEventDispatcher();

  function smoothHistoryPath(path) {
    const points = [...path.matchAll(/(-?[0-9.]+) (-?[0-9.]+)/g)].map((match) => [Number(match[1]), Number(match[2])]);
    if (points.length < 3) return path;
    const commands = [`M${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`];
    for (let index = 0; index < points.length - 1; index += 1) {
      const current = points[index];
      const next = points[index + 1];
      const midX = (current[0] + next[0]) / 2;
      const midY = (current[1] + next[1]) / 2;
      commands.push(`Q${current[0].toFixed(1)} ${current[1].toFixed(1)} ${midX.toFixed(1)} ${midY.toFixed(1)}`);
    }
    const last = points[points.length - 1];
    commands.push(`T${last[0].toFixed(1)} ${last[1].toFixed(1)}`);
    return commands.join(" ");
  }

  function historyAreaFor(path) {
    if (!path) return "";
    const points = [...path.matchAll(/(-?[0-9.]+) (-?[0-9.]+)/g)].map((match) => [Number(match[1]), Number(match[2])]);
    if (!points.length) return "";
    const first = points[0];
    const last = points[points.length - 1];
    return `${path} L${last[0].toFixed(1)} 28 L${first[0].toFixed(1)} 28 Z`;
  }

  $: selectedAcLabel = acOptions.find(([id]) => Number(id) === Number(selectedAcId))?.[1] || acOptions[0]?.[1] || "AC";
  $: smoothPath = smoothHistoryPath(selectedHistoryPath);
  $: smoothPlanPath = smoothHistoryPath(selectedPlanPath);
  $: historyAreaPath = historyAreaFor(smoothPath);
  $: controlRoomTemperature = selectedStatus.sensor_temp ?? selectedThermostat.current;
  $: planEnd = selectedPlanEntries.at(-1)?.temperature;
  $: planLabel = selectedPlanEntries.length ? tempText(planEnd, 1) : selectedCallLabel || (selectedHistoryEntries.length ? tempText(selectedHistoryEntries[selectedHistoryEntries.length - 1].temperature, 1) : "-");
</script>

<article class="hero-card primary">
  <div class="hero-topline">
    <div>
      <label class="hero-ac-select">
        {#if acOptions.length > 1}
          <select aria-label="Selected AC" on:change={(event) => dispatch("selectAc", Number(event.currentTarget.value))}>
            {#each acOptions as [id, name]}
              <option value={id} selected={Number(id) === Number(selectedAcId)}>{name}</option>
            {/each}
          </select>
        {:else}
          <span>{selectedAcLabel}</span>
        {/if}
      </label>
    </div>
    <button type="button" class="hero-power" class:on={selectedStatus.power_on} disabled={pendingKey.startsWith("ac-power")} on:click={() => dispatch("power", !selectedStatus.power_on)} title="Power">
      <SemanticIcon name="power" size={18} />
      <span>{selectedStatus.power_on ? "On" : "Off"}</span>
    </button>
  </div>
  <div class="hero-temp-split">
    <div class="hero-setpoint">
      <div class="hero-readout-label">Setpoint</div>
      <div class="hero-value">{tempText(selectedThermostat.setpoint)}</div>
    </div>
    <div class="hero-current">
      <div class="hero-readout-label">Room</div>
      <div class="hero-value small">{tempText(controlRoomTemperature, 1)}</div>
      <div class="hero-status-line">{modeName(selectedStatus.mode)}</div>
    </div>
  </div>
  <div class="history-strip">
    <svg class="temp-line" viewBox="0 0 120 28" preserveAspectRatio="none" aria-label="Aggregated active zone temperature plan">
      {#if selectedCallAreaPath}<path class="history-call-area" d={selectedCallAreaPath}></path>{/if}
      {#if selectedSetpointPath}<path class="history-setpoint-line" d={selectedSetpointPath}></path>{/if}
      {#if historyAreaPath}<path class="history-area" d={historyAreaPath}></path>{/if}
      {#if smoothPath}<path class="history-line" d={smoothPath}></path>{/if}
      {#if smoothPlanPath}<path class="history-plan-line" d={smoothPlanPath}></path>{/if}
    </svg>
    <div class="history-meta">
      <span>{selectedHistoryEntries.length ? tempText(selectedHistoryEntries[0].temperature, 1) : "History"}</span>
      <span>{planLabel}</span>
    </div>
  </div>
  <div class="hero-control-actions">
    <button type="button" class="hero-all-off" disabled={pendingKey === "all-off"} on:click={() => dispatch("allOff")}>All Off</button>
    <div class="hero-mode-row">
      <label class="hero-mode-pill">Mode
        <SemanticIcon name="activity" size={16} />
        <select class="hero-mode-select" disabled={pendingKey.startsWith("ac-mode")} on:change={(event) => dispatch("mode", Number(event.currentTarget.value))}>
          {#each modeOptions as [value, label]}
            <option value={value} selected={Number(value) === Number(selectedStatus.mode)}>{label}</option>
          {/each}
        </select>
      </label>
      <label class="hero-mode-pill">Fan
        <SemanticIcon name="fan" size={16} />
        <select class="hero-mode-select" disabled={pendingKey.startsWith("ac-fan")} on:change={(event) => dispatch("fan", Number(event.currentTarget.value))}>
          {#each fanOptions as [value, label]}
            <option value={value} selected={Number(value) === Number(selectedStatus.fan)}>{label}</option>
          {/each}
        </select>
      </label>
    </div>
  </div>
</article>
