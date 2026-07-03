<script>
  import { tempText } from "../../lib/format.js";

  export let scopedSensorRows = [];
  export let pairSensor = () => {};
  export let sensorKindLabel = () => "Sensor";
  export let saveSensorTemperature = () => {};
</script>

<div class="service-actions top-actions">
  <button type="button" class="action-primary" on:click={() => pairSensor(true)}>Start Pair</button>
  <button type="button" on:click={() => pairSensor(false)}>Stop Pair</button>
</div>
<div class="card-grid">
  {#each scopedSensorRows as sensor}
    <article class="summary-card editor-card sensor-card" data-sensor-row={sensor.id}>
      <div class="card-head">
        <div class="card-title">{sensor.name}</div>
        <span class:selected-pill={sensor.present !== false}>{sensor.present === false ? "Missing" : sensorKindLabel(sensor.kind)}</span>
      </div>
      <div class="readonly-summary">
        <span>{sensor.address}</span>
        <span>{sensor.temperature === undefined || sensor.temperature === null ? "-" : tempText(sensor.temperature, 1)}</span>
        <span>Mapped {sensor.mapped_groups?.length ? sensor.mapped_groups.join(", ") : "-"}</span>
      </div>
      {#if sensor.kind !== "supply_air" && sensor.temperature !== undefined && sensor.temperature !== null}
        <div class="sensor-calibration">
          <input type="range" min="-10" max="40" step="1" value={Math.round(sensor.temperature)} data-sensor-temperature />
          <button type="button" on:click={(event) => saveSensorTemperature(event, sensor.id)}>Revise Sensor Temperature</button>
        </div>
      {:else}
        <div class="hero-detail">Calibration unavailable</div>
      {/if}
    </article>
  {:else}
    <article class="summary-card"><div class="card-title">No Sensor Data</div><div class="hero-detail">Pairing or sensor list data has not been received yet.</div></article>
  {/each}
</div>
