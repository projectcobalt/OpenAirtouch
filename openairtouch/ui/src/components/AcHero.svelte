<script>
  import { createEventDispatcher } from "svelte";
  import { modeName } from "../lib/airtouch.js";
  import { tempText } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let acOptions = [];
  export let selectedAcId = 0;
  export let selectedAcName = "";
  export let selectedStatus = {};
  export let selectedSettings = {};
  export let selectedThermostat = {};
  export let selectedHistoryEntries = [];
  export let selectedHistoryPath = "";
  export let selectedSpillHints = [];
  export let runtimeText = "-";
  export let pendingKey = "";
  export let modeOptions = [];
  export let fanOptions = [];

  const dispatch = createEventDispatcher();
</script>

<article class="hero-card primary">
  <div class="hero-topline">
    <div>
      <div class="hero-kicker">Selected AC</div>
      <label class="hero-ac-select">
        <span class="hero-title">{selectedAcName}</span>
        <select aria-label="Selected AC" on:change={(event) => dispatch("selectAc", Number(event.currentTarget.value))}>
          {#each acOptions as [id, name]}
            <option value={id} selected={Number(id) === Number(selectedAcId)}>{name}</option>
          {/each}
        </select>
      </label>
    </div>
    <button type="button" class="hero-power" class:on={selectedStatus.power_on} disabled={pendingKey.startsWith("ac-power")} on:click={() => dispatch("power", !selectedStatus.power_on)} title="Power">
      <SemanticIcon name="power" size={22} />
      <span>{selectedStatus.power_on ? "On" : "Off"}</span>
    </button>
  </div>
  <div class="hero-temp-split">
    <div class="hero-setpoint">
      <div class="hero-readout-label">Setpoint</div>
      <div class="hero-value">{tempText(selectedThermostat.setpoint)}</div>
    </div>
    <div class="hero-current">
      <div class="hero-readout-label">Current</div>
      <div class="hero-value small">{tempText(selectedThermostat.current, 1)}</div>
      <div class="hero-status-line">{modeName(selectedStatus.mode)}</div>
    </div>
  </div>
  <div class="history-strip">
    <svg class="temp-line" viewBox="0 0 120 28" preserveAspectRatio="none" aria-label="Temperature history">
      <line class="axis" x1="0" y1="18" x2="120" y2="18"></line>
      {#if selectedHistoryPath}<path class="history-line" d={selectedHistoryPath}></path>{/if}
    </svg>
    <div class="history-meta">
      <span>{selectedHistoryEntries.length ? tempText(selectedHistoryEntries[0].temperature, 1) : "History"}</span>
      <span>{selectedHistoryEntries.length ? tempText(selectedHistoryEntries[selectedHistoryEntries.length - 1].temperature, 1) : "-"}</span>
    </div>
  </div>
  <div class="hero-control-actions">
    <button type="button" class="hero-all-off" disabled={pendingKey === "all-off"} on:click={() => dispatch("allOff")}>All Off</button>
    <div class="setpoint-controls">
      <button type="button" title="Lower setpoint" aria-label="Lower setpoint" on:click={() => dispatch("setpoint", -1)}><SemanticIcon name="minus" /></button>
      <strong>{tempText(selectedThermostat.setpoint)}</strong>
      <button type="button" title="Raise setpoint" aria-label="Raise setpoint" on:click={() => dispatch("setpoint", 1)}><SemanticIcon name="plus" /></button>
    </div>
  </div>
  <div class="ac-detail-row">
    <span>Runtime {runtimeText}</span>
    <span>{selectedStatus.has_timer ? "Timer set" : "No timer"}</span>
    <span>{selectedSettings.auto_off ? `Auto off ${selectedSettings.on_time_limit ?? 0}` : "Auto off disabled"}</span>
    {#if selectedSpillHints.length}<span>{selectedSpillHints.join(" / ")}</span>{/if}
  </div>
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
</article>
