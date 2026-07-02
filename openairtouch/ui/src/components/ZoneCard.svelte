<script>
  import { createEventDispatcher } from "svelte";
  import { finite, tempText } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let id;
  export let group = {};
  export let isOn = false;
  export let badges = [];
  export let pendingKey = "";
  export let spill = false;
  export let name = "";

  const dispatch = createEventDispatcher();
  $: status = group?.status || {};
</script>

<article class="zone-card" class:on={isOn} class:off={!isOn} class:spill>
  <button type="button" class="mini-power" class:on={isOn} disabled={pendingKey === `zone-power-${id}`} on:click={() => dispatch("power", {id, group, powerOn: !isOn})} aria-label={`${isOn ? "Turn off" : "Turn on"} ${name}`}>
    <SemanticIcon name="power" size={16} />
    <span>{isOn ? "On" : "Off"}</span>
  </button>
  <div class="zone-top">
    <span>Zone {Number(id) + 1}</span>
    <strong>{name}</strong>
  </div>
  <div class="zone-metrics">
    <div>
      <span>Room</span>
      <strong>{status.has_sensor ? tempText(status.temperature, 1) : "-"}</strong>
    </div>
    <div>
      <span>Set</span>
      <strong>{tempText(status.setpoint)}</strong>
    </div>
    <div>
      <span>Damper</span>
      <strong>{finite(status.percentage) === null ? "-" : `${status.percentage}%`}</strong>
    </div>
  </div>
  <div class="zone-damper">
    <div class="bar"><div class="bar-fill" style={`width:${finite(status.percentage) === null ? 0 : status.percentage}%`}></div></div>
    <div class="tile-foot">
      {#each badges as badge}<span>{badge}</span>{/each}
    </div>
  </div>
  <div class="zone-actions">
    <button type="button" aria-label="Lower zone setpoint" on:click={() => dispatch("setpoint", {id, group, delta: -1})}><SemanticIcon name="minus" size={16} /></button>
    <button type="button" aria-label="Raise zone setpoint" on:click={() => dispatch("setpoint", {id, group, delta: 1})}><SemanticIcon name="plus" size={16} /></button>
    <button type="button" on:click={() => dispatch("percent", {id, group, delta: -10})}>-10%</button>
    <button type="button" on:click={() => dispatch("percent", {id, group, delta: 10})}>+10%</button>
  </div>
</article>
