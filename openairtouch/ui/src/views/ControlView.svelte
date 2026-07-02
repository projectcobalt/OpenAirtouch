<script>
  import { createEventDispatcher } from "svelte";
  import AcHero from "../components/AcHero.svelte";
  import MetricCard from "../components/MetricCard.svelte";
  import ZoneCard from "../components/ZoneCard.svelte";
  import { percentText, tempText } from "../lib/format.js";

  export let acOptions = [];
  export let selectedAcId = 0;
  export let selectedAcName = "";
  export let selectedStatus = {};
  export let selectedSettings = {};
  export let selectedThermostat = {};
  export let selectedHistoryEntries = [];
  export let selectedHistoryPath = "";
  export let selectedSpillHints = [];
  export let selectedRuntimeText = "-";
  export let selectedModeOptions = [];
  export let selectedFanOptions = [];
  export let selectedSensorName = "-";
  export let selectedZones = [];
  export let activeZoneCount = 0;
  export let averageDamper = null;
  export let alerts = [];
  export let runtime = {};
  export let zonePage = 0;
  export let zonePageCount = 1;
  export let pagedZones = [];
  export let pendingKey = "";
  export let groupIsOn = () => false;
  export let groupIsSpill = () => false;
  export let groupBadges = () => [];
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;

  const dispatch = createEventDispatcher();
</script>

<section class="hero-grid">
  <AcHero
    {acOptions}
    {selectedAcId}
    {selectedAcName}
    {selectedStatus}
    {selectedSettings}
    {selectedThermostat}
    {selectedHistoryEntries}
    {selectedHistoryPath}
    {selectedSpillHints}
    {pendingKey}
    runtimeText={selectedRuntimeText}
    modeOptions={selectedModeOptions}
    fanOptions={selectedFanOptions}
    on:selectAc={(event) => dispatch("selectAc", event.detail)}
    on:power={(event) => dispatch("power", event.detail)}
    on:allOff={() => dispatch("allOff")}
    on:setpoint={(event) => dispatch("setpoint", event.detail)}
    on:mode={(event) => dispatch("mode", event.detail)}
    on:fan={(event) => dispatch("fan", event.detail)}
  />

  <MetricCard label="Active Zones" value={`${activeZoneCount} / ${selectedZones.length}`} detail={activeZoneCount ? "Zones calling" : "All zones idle"} />
  <MetricCard label="Indoor" value={tempText(selectedThermostat.current, 1)} detail={selectedSensorName} />
  <MetricCard label={alerts.length ? "Warning" : "System"} value={alerts.length ? "Gateway Fault" : "No Faults"} detail={alerts[0] || "Runtime healthy"} warning={alerts.length > 0} />
  <MetricCard label="Damper Summary" value={percentText(averageDamper)} detail="Average opening">
    <div class="bar"><div class="bar-fill" style={`width:${averageDamper === null ? 0 : averageDamper}%`}></div></div>
  </MetricCard>
</section>

<section class="zones-section">
  <div class="zone-heading">
    <div>
      <span>Zones</span>
      <strong>{activeZoneCount} / {selectedZones.length}</strong>
    </div>
    <div class="zone-pages">
      {#if zonePageCount > 1}
        {#each Array(zonePageCount) as _, index}
          <button type="button" class:active={zonePage === index} on:click={() => dispatch("zonePage", index)}>
            {(index * 8) + 1}-{Math.min((index + 1) * 8, selectedZones.length)}
          </button>
        {/each}
      {/if}
      <span>{runtime.rx_count || 0} RX / {runtime.tx_count || 0} TX</span>
    </div>
  </div>

  <div class="zone-grid">
    {#each pagedZones as [id, group]}
      <ZoneCard
        {id}
        {group}
        {pendingKey}
        isOn={groupIsOn(group)}
        spill={groupIsSpill(group)}
        badges={groupBadges(group)}
        name={zoneName(id, group)}
        on:power={(event) => dispatch("zonePower", event.detail)}
        on:setpoint={(event) => dispatch("zoneSetpoint", event.detail)}
        on:percent={(event) => dispatch("zonePercent", event.detail)}
      />
    {/each}
  </div>
</section>
