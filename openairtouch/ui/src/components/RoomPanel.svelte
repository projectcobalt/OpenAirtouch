<script>
  import { percentText, tempText, title } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let controller = {};
  export let integrations = {};
  export let selectedRoomName = "-";
  export let selectedThermostat = {};

  $: outdoorTemperature = integrations.weather?.state?.temperature;
  $: humidity = integrations.indoor?.state?.humidity ?? integrations.weather?.state?.humidity;
</script>

<aside class="room-panel">
  <div class="room-brand">
    <h1>OpenAirTouch</h1>
  </div>
  <div class="room-focus">
    <div class="room-kicker">Climate</div>
    <div class="room-stats">
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="indoor" size={17} /></span><div><strong>{tempText(selectedThermostat.current, 1)}</strong><span>Indoor</span></div></div>
      {#if outdoorTemperature !== undefined && outdoorTemperature !== null}
        <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="outdoor" size={17} /></span><div><strong>{tempText(outdoorTemperature, 1)}</strong><span>Outdoor</span></div></div>
      {/if}
      {#if humidity !== undefined && humidity !== null}
        <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="humidity" size={16} /></span><div><strong>{percentText(humidity)}</strong><span>Humidity</span></div></div>
      {/if}
    </div>
  </div>
  <div class="room-footer">
    <div>
      <span>Status</span>
      <strong>{controller.status === "running" ? "Running" : title(controller.status || "Connecting")}</strong>
    </div>
    <div>
      <span>Sensor</span>
      <strong>{selectedRoomName}</strong>
    </div>
  </div>
</aside>
