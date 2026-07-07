<script>
  import { createEventDispatcher } from "svelte";
  import AcHero from "../components/AcHero.svelte";
  import MetricCard from "../components/MetricCard.svelte";
  import ZoneCard from "../components/ZoneCard.svelte";
  import SemanticIcon from "../components/icons/SemanticIcon.svelte";
  import { percentText, tempText } from "../lib/format.js";

  export let acOptions = [];
  export let selectedAcId = 0;
  export let selectedStatus = {};
  export let selectedThermostat = {};
  export let selectedTemperatureState = {};
  export let selectedRoomName = "";
  export let selectedHistoryEntries = [];
  export let selectedHistoryPath = "";
  export let selectedPlanEntries = [];
  export let selectedPlanPath = "";
  export let selectedSetpointPath = "";
  export let selectedCallAreaPath = "";
  export let selectedCallLabel = "";
  export let selectedModeOptions = [];
  export let selectedFanOptions = [];
  export let selectedSensorName = "-";
  export let selectedZones = [];
  export let selectedGroupEntries = [];
  export let activeZoneCount = 0;
  export let averageDamper = null;
  export let alerts = [];
  export let pendingKey = "";
  export let groupIsOn = () => false;
  export let groupIsSpill = () => false;
  export let groupBadges = () => [];
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let zoneRoomTemperature = (_id, group) => group?.status?.temperature;

  const dispatch = createEventDispatcher();
</script>

<section class="hero-grid">
  <AcHero
    {acOptions}
    {selectedAcId}
    {selectedStatus}
    {selectedThermostat}
    {selectedTemperatureState}
    {selectedRoomName}
    {selectedGroupEntries}
    {selectedHistoryEntries}
    {selectedHistoryPath}
    {selectedPlanEntries}
    {selectedPlanPath}
    {selectedSetpointPath}
    {selectedCallAreaPath}
    {selectedCallLabel}
    {pendingKey}
    modeOptions={selectedModeOptions}
    fanOptions={selectedFanOptions}
    on:selectAc={(event) => dispatch("selectAc", event.detail)}
    on:power={(event) => dispatch("power", event.detail)}
    on:allOff={() => dispatch("allOff")}
    on:mode={(event) => dispatch("mode", event.detail)}
    on:fan={(event) => dispatch("fan", event.detail)}
  />

  <MetricCard label="Active Zones" value={`${activeZoneCount} / ${selectedZones.length}`} detail={activeZoneCount ? "Zones calling" : "All zones idle"} />
  <MetricCard label="Indoor" value={tempText(selectedTemperatureState.indoor?.value ?? selectedThermostat.current)} detail={selectedTemperatureState.indoor?.sourceLabel || selectedSensorName} />
  <MetricCard label={alerts.length ? "Warning" : "System"} value={alerts.length ? "Gateway Fault" : "No Faults"} detail={alerts[0] || "Runtime healthy"} warning={alerts.length > 0} />
  <MetricCard label="Damper Summary" value={percentText(averageDamper)} detail="Average opening">
    <div class="bar"><div class="bar-fill" style={`width:${averageDamper === null ? 0 : averageDamper}%`}></div></div>
  </MetricCard>
</section>

<section class="zones-section">
  {#if selectedZones.length > 8}
    <div class="zone-scroll-hint" aria-hidden="true">
      <SemanticIcon name="arrowsHorizontal" size={18} />
    </div>
  {/if}
  <div class="zone-grid" class:scrollable={selectedZones.length > 8}>
    {#each selectedZones as [id, group]}
      <ZoneCard
        {id}
        {group}
        {pendingKey}
        isOn={groupIsOn(group)}
        spill={groupIsSpill(group)}
        badges={groupBadges(group)}
        name={zoneName(id, group)}
        roomTemperature={zoneRoomTemperature(id, group)}
        on:power={(event) => dispatch("zonePower", event.detail)}
        on:setpoint={(event) => dispatch("zoneSetpoint", event.detail)}
        on:percent={(event) => dispatch("zonePercent", event.detail)}
      />
    {/each}
  </div>
</section>
