<script>
  import { createEventDispatcher } from "svelte";
  import { tempText, title } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let health = null;
  export let runtime = {};
  export let system = {};
  export let controller = {};
  export let integrations = {};
  export let selectedRoomName = "-";
  export let selectedSensorName = "-";
  export let selectedThermostat = {};

  const dispatch = createEventDispatcher();
</script>

<aside class="room-panel">
  <div class="room-brand">
    <h1>{health?.protocol_name || runtime.protocol_name || "AirTouch 4"}</h1>
    <div class="room-status"><span class="status-dot"></span>{controller.status === "running" ? "Running" : title(controller.status || "Connecting")}</div>
  </div>
  <div class="room-focus">
    <div class="room-kicker">Active Room</div>
    <div class="room-title">{selectedRoomName}</div>
    <div class="room-sensor">{selectedSensorName}</div>
    <div class="room-stats">
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="room" size={16} /></span><div><strong>{tempText(selectedThermostat.current, 1)}</strong><span>Indoor</span></div></div>
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="temperature" size={16} /></span><div><strong>{integrations.weather?.state?.temperature === undefined ? "-" : tempText(integrations.weather?.state?.temperature, 1)}</strong><span>Outdoor</span></div></div>
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="humidity" size={16} /></span><div><strong>{integrations.indoor?.state?.humidity ?? integrations.weather?.state?.humidity ?? "-"}</strong><span>Humidity</span></div></div>
    </div>
  </div>
  <div class="room-footer">
    <div>
      <span>Gateway</span>
      <strong>{runtime.src || "-"}</strong>
    </div>
    <div>
      <span>Version</span>
      <strong>{system.version || runtime.version || "-"}</strong>
    </div>
    <button type="button" class="icon-button" title="Refresh" aria-label="Refresh" on:click={() => dispatch("refresh")}>
      <SemanticIcon name="refresh" />
    </button>
  </div>
</aside>
