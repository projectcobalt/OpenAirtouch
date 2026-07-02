<script>
  import { tempText, title } from "../lib/format.js";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let controller = {};
  export let integrations = {};
  export let selectedRoomName = "-";
  export let selectedThermostat = {};
</script>

<aside class="room-panel">
  <div class="room-brand">
    <h1>OpenAirTouch</h1>
  </div>
  <div class="room-focus">
    <div class="room-kicker">Climate</div>
    <div class="room-stats">
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="indoor" size={17} /></span><div><strong>{tempText(selectedThermostat.current, 1)}</strong><span>Indoor</span></div></div>
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="outdoor" size={17} /></span><div><strong>{integrations.weather?.state?.temperature === undefined ? "-" : tempText(integrations.weather?.state?.temperature, 1)}</strong><span>Outdoor</span></div></div>
      <div class="room-stat"><span class="room-stat-icon"><SemanticIcon name="humidity" size={16} /></span><div><strong>{integrations.indoor?.state?.humidity ?? integrations.weather?.state?.humidity ?? "-"}</strong><span>Humidity</span></div></div>
    </div>
  </div>
  <div class="room-footer">
    <div>
      <span>Status</span>
      <strong>{controller.status === "running" ? "Running" : title(controller.status || "Connecting")}</strong>
    </div>
    <div>
      <span>Zone</span>
      <strong>{selectedRoomName}</strong>
    </div>
  </div>
</aside>
