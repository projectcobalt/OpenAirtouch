<script>
  import { createEventDispatcher } from "svelte";
  import { finite, percentText, tempText } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let id;
  export let group = {};
  export let isOn = false;
  export let badges = [];
  export let pendingKey = "";
  export let spill = false;
  export let name = "";
  export let roomTemperature = null;

  const dispatch = createEventDispatcher();
  $: status = group?.status || {};
  $: sensorControl = status.sensor_control === true;
  $: hasSetpoint = finite(status.setpoint) !== null;
  $: hasPercentage = finite(status.percentage) !== null;
  $: controlsDisabled = !isOn || pendingKey.startsWith(`zone-set-${id}-`) || pendingKey.startsWith(`zone-percent-${id}-`);
</script>

<article class="zone-card" class:on={isOn} class:off={!isOn} class:spill class:temp-control={sensorControl} class:damper-control={!sensorControl}>
  <button type="button" class="mini-power" class:on={isOn} disabled={pendingKey === `zone-power-${id}`} on:click={() => dispatch("power", {id, group, powerOn: !isOn})} aria-label={`${isOn ? "Turn off" : "Turn on"} ${name}`}>
    <SemanticIcon name="power" size={16} />
    <span>{isOn ? "On" : "Off"}</span>
  </button>
  <div class="zone-top">
    <strong>{name}</strong>
    {#if sensorControl}
      <div class="zone-room-badge" aria-label={`Room temperature ${tempText(roomTemperature, 1)}`}>
        <span>Room</span>
        <strong>{tempText(roomTemperature, 1)}</strong>
      </div>
    {/if}
  </div>
  <div class="zone-damper">
    <div class="bar"><div class="bar-fill" style={`width:${finite(status.percentage) === null ? 0 : status.percentage}%`}></div></div>
    <div class="tile-foot">
      {#each badges as badge}<span>{badge}</span>{/each}
    </div>
  </div>
  <div class="zone-primary-field">
    {#if isOn && sensorControl}
      <div class="zone-setpoint-control">
        <span>Setpoint</span>
        <div class="zone-actions zone-setpoint-actions">
          <button type="button" aria-label="Lower zone setpoint" disabled={!hasSetpoint || controlsDisabled} on:click={() => dispatch("setpoint", {id, group, delta: -1})}><SemanticIcon name="minus" size={15} /></button>
          <strong>{tempText(status.setpoint)}</strong>
          <button type="button" aria-label="Raise zone setpoint" disabled={!hasSetpoint || controlsDisabled} on:click={() => dispatch("setpoint", {id, group, delta: 1})}><SemanticIcon name="plus" size={15} /></button>
        </div>
      </div>
    {:else if isOn}
      <div class="zone-damper-control">
        <span>Damper</span>
        <div class="zone-actions">
          <button type="button" aria-label="Close zone damper" disabled={!hasPercentage || controlsDisabled} on:click={() => dispatch("percent", {id, group, delta: -10})}><SemanticIcon name="minus" size={15} /></button>
          <strong>{percentText(status.percentage)}</strong>
          <button type="button" aria-label="Open zone damper" disabled={!hasPercentage || controlsDisabled} on:click={() => dispatch("percent", {id, group, delta: 10})}><SemanticIcon name="plus" size={15} /></button>
        </div>
      </div>
    {/if}
  </div>
</article>
