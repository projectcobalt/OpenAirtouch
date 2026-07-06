<script>
  import SemanticIcon from "../../components/icons/SemanticIcon.svelte";
  import { tempText } from "../../lib/format.js";

  export let scopedSensorRows = [];
  export let system = {};
  export let pairSensor = () => {};
  export let sensorKindLabel = () => "Sensor";
  export let saveSensorTemperature = () => {};
  export let confirmAction = async () => true;

  let selectedSensorId = "";
  let calibrationSensorId = "";
  let calibrationTarget = "";

  function sensorValue(sensor) {
    return String(sensor?.id ?? "");
  }

  function display(value) {
    return value === undefined || value === null || value === "" ? "-" : String(value);
  }

  function sensorLabel(sensor) {
    return sensor.mapped_groups?.length ? sensor.mapped_groups.join(", ") : sensor.name;
  }

  function apkSensorName(sensor) {
    const zone = sensor.mapped_groups?.[0];
    const id = Number(sensor.id);
    if (sensor.kind === "touchpad" && Number.isFinite(id)) return `TouchPad #${id >= 0x90 ? id - 0x8F : id + 1}`;
    if (zone && Number.isFinite(id)) return `[${zone} #s${(id % 2) + 1}]`;
    if (zone) return `[${zone}]`;
    return sensor.name;
  }

  function signalText(sensor) {
    if (sensor.status === "lost") return "Lost";
    if (sensor.signal === undefined || sensor.signal === null) return "-";
    const signal = Number(sensor.signal);
    if (!Number.isFinite(signal)) return display(sensor.signal);
    if (signal < -95) return `${signal} dBm / Weak`;
    if (signal < -79) return `${signal} dBm / Normal`;
    return `${signal} dBm / Strong`;
  }

  function batteryText(sensor) {
    if (sensor.battery === undefined || sensor.battery === null) return "-";
    return `${sensor.battery}%${sensor.low_battery ? " / Low" : ""}`;
  }

  function healthBadges(sensor) {
    const badges = [];
    const battery = batteryText(sensor);
    const signal = signalText(sensor);
    if (battery !== "-") badges.push({icon: "battery", value: battery, label: `Battery ${battery}`});
    if (signal !== "-") badges.push({icon: "signal", value: signal, label: `Signal ${signal}`});
    return badges;
  }

  function calibrationText(value) {
    const number = Number(value);
    return Number.isFinite(number) ? tempText(number) : "-";
  }

  function calibrationPercent(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.min(100, Math.max(0, ((number + 10) / 50) * 100));
  }

  async function confirmCalibrationSave(event) {
    const card = event.currentTarget.closest("[data-sensor-row]");
    const input = card?.querySelector("[data-sensor-temperature]");
    const target = input?.value || calibrationTarget;
    const confirmed = await confirmAction({
      title: "Save Calibration",
      message: `${apkSensorName(selectedSensor)} will be saved as ${calibrationText(target)}. Current reading is ${tempText(selectedSensor.temperature)}.`,
      confirmLabel: "Save Calibration"
    });
    if (confirmed) saveSensorTemperature(card, selectedSensor.id);
  }

  $: selectableSensors = scopedSensorRows.filter((sensor) => sensor.kind !== "supply_air" && (sensor.mapped_groups?.length || sensor.kind === "touchpad"));
  $: sensorOptions = selectableSensors.length ? selectableSensors : scopedSensorRows;
  $: if (sensorOptions.length && !sensorOptions.some((sensor) => sensorValue(sensor) === selectedSensorId)) selectedSensorId = sensorValue(sensorOptions[0]);
  $: selectedSensor = sensorOptions.find((sensor) => sensorValue(sensor) === selectedSensorId) || sensorOptions[0];
  $: pairing = system.sensor_pairing?.pairing === true;
  $: canCalibrate = selectedSensor && selectedSensor.kind !== "supply_air" && selectedSensor.temperature !== undefined && selectedSensor.temperature !== null;
  $: if (canCalibrate && sensorValue(selectedSensor) !== calibrationSensorId) {
    calibrationSensorId = sensorValue(selectedSensor);
    calibrationTarget = String(selectedSensor.temperature);
  }
</script>

<div class="sensor-toolbar top-actions">
  <label class="field sensor-selector">
    <span class="sr-only">Sensor</span>
    <select bind:value={selectedSensorId}>
      {#each sensorOptions as sensor}
        <option value={sensorValue(sensor)}>{sensorLabel(sensor)}</option>
      {/each}
    </select>
  </label>
  <div class="service-actions sensor-pair-action">
    <button type="button" class={pairing ? "selected-pill" : "action-primary"} on:click={() => pairSensor(!pairing)}>{pairing ? "Stop Pairing" : "Start Pairing"}</button>
  </div>
</div>

{#if selectedSensor}
  <div class="summary-grid sensor-detail-grid">
    <article class="summary-card editor-card sensor-card">
      <div class="card-head">
        <div class="card-title">Sensor Info</div>
        <div class="sensor-badges">
          <span class:selected-pill={selectedSensor.present !== false}>{selectedSensor.present === false ? "Missing" : sensorKindLabel(selectedSensor.kind)}</span>
          {#each healthBadges(selectedSensor) as badge}
            <span class="sensor-icon-badge" title={badge.label} aria-label={badge.label}><SemanticIcon name={badge.icon} size={14} />{badge.value}</span>
          {/each}
        </div>
      </div>
      <div class="field-grid sensor-info-grid">
        <div class="info-field"><span>Zone</span><strong>{selectedSensor.mapped_groups?.length ? selectedSensor.mapped_groups.join(", ") : "-"}</strong></div>
        <div class="info-field"><span>Temp</span><strong>{selectedSensor.temperature === undefined || selectedSensor.temperature === null ? "-" : tempText(selectedSensor.temperature)}</strong></div>
        <div class="info-field"><span>Name</span><strong>{apkSensorName(selectedSensor)}</strong></div>
        <div class="info-field"><span>Address</span><strong>{selectedSensor.address}</strong></div>
        <div class="info-field"><span>Status</span><strong>{display(selectedSensor.status)}</strong></div>
        <div class="info-field"><span>MAC</span><strong>{display(selectedSensor.mac)}</strong></div>
      </div>
    </article>

    <article class="summary-card editor-card sensor-card" data-sensor-row={selectedSensor.id}>
      <div class="card-title">Calibration</div>
      {#if canCalibrate}
        <div class="sensor-calibration">
          <div class="range-field" title={`Target ${calibrationText(calibrationTarget)}`}>
            <input type="range" min="-10" max="40" step="0.1" bind:value={calibrationTarget} aria-label="Calibration temperature" data-sensor-temperature />
            <output class="slider-tooltip" style={`left: ${calibrationPercent(calibrationTarget)}%`}>{calibrationText(calibrationTarget)}</output>
          </div>
          <button type="button" class="action-primary" on:click={confirmCalibrationSave}>Save Calibration</button>
        </div>
      {:else}
        <div class="hero-detail">Calibration unavailable for this sensor.</div>
      {/if}
    </article>
  </div>
{:else}
  <article class="summary-card"><div class="card-title">No Sensor Data</div><div class="hero-detail">Pairing or sensor list data has not been received yet.</div></article>
{/if}
