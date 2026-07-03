<script>
  import Subnav from "../components/Subnav.svelte";
  import AppSettings from "./settings/AppSettings.svelte";
  import SensorSettings from "./settings/SensorSettings.svelte";
  import GroupingSettings from "./settings/GroupingSettings.svelte";
  import SpillSettings from "./settings/SpillSettings.svelte";
  import BalanceSettings from "./settings/BalanceSettings.svelte";
  import AcSetupSettings from "./settings/AcSetupSettings.svelte";
  import GeneralSettings from "./settings/GeneralSettings.svelte";
  import ServiceSettings from "./settings/ServiceSettings.svelte";
  import DiagnosticsSettings from "./settings/DiagnosticsSettings.svelte";

  export let options = [];
  export let activeServiceView = "app";
  export let runtime = {};
  export let socketState = "offline";
  export let selectedTheme = "system";
  export let showSupportDiagnostics = false;
  export let system = {};
  export let service = {};
  export let controller = {};
  export let transactions = {};
  export let busEvents = [];
  export let sensorRows = [];
  export let groupEntries = [];
  export let selectedGroupEntries = [];
  export let acEntries = [];
  export let balanceRows = {};
  export let setTheme = () => {};
  export let setShowSupportDiagnostics = () => {};
  export let savePreference = () => {};
  export let pairSensor = () => {};
  export let sensorKindLabel = () => "Sensor";
  export let saveSensorTemperature = () => {};
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let groupIsOn = () => false;
  export let saveGroupName = () => {};
  export let saveGrouping = () => {};
  export let saveSpill = () => {};
  export let stepBalance = () => {};
  export let balanceAction = () => {};
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let saveAcBase = () => {};
  export let saveAcSettings = () => {};
  export let resetTempOffsets = () => {};
  export let saveTurboGroup = () => {};
  export let saveParameters = () => {};
  export let saveService = () => {};
  export let onView = () => {};

  $: scopedGroupEntries = selectedGroupEntries.length ? selectedGroupEntries : groupEntries;
  $: scopedGroupIds = new Set(scopedGroupEntries.map(([id]) => Number(id)));
  $: scopedSensorRows = sensorRows.filter((sensor) => {
    const mappedIds = Array.isArray(sensor.mapped_group_ids) ? sensor.mapped_group_ids.map(Number) : [];
    if (sensor.resolved_group_id !== undefined && sensor.resolved_group_id !== null && scopedGroupIds.has(Number(sensor.resolved_group_id))) return true;
    if (mappedIds.some((groupId) => scopedGroupIds.has(groupId))) return true;
    return mappedIds.length === 0 && (sensor.resolved_group_id === undefined || sensor.resolved_group_id === null);
  });
</script>

<section class="cards-view">
  <Subnav options={options} active={activeServiceView} className="service-subnav" on:change={(event) => onView(event.detail)} />

  {#if activeServiceView === "app"}
    <AppSettings {runtime} {controller} {selectedTheme} {showSupportDiagnostics} {system} {setTheme} {setShowSupportDiagnostics} {savePreference} />
  {:else if activeServiceView === "sensors"}
    <SensorSettings {scopedSensorRows} {pairSensor} {sensorKindLabel} {saveSensorTemperature} />
  {:else if activeServiceView === "grouping"}
    <GroupingSettings {scopedGroupEntries} {zoneName} {groupIsOn} {saveGroupName} {saveGrouping} />
  {:else if activeServiceView === "spill"}
    <SpillSettings {scopedGroupEntries} {acEntries} {system} {zoneName} {acName} {saveSpill} />
  {:else if activeServiceView === "balance"}
    <BalanceSettings {scopedGroupEntries} {balanceRows} {zoneName} {stepBalance} {balanceAction} />
  {:else if activeServiceView === "ac-setup"}
    <AcSetupSettings {acEntries} {system} {acName} {saveAcBase} {saveAcSettings} {resetTempOffsets} {saveTurboGroup} />
  {:else if activeServiceView === "general" || activeServiceView === "parameters"}
    <GeneralSettings {system} {groupEntries} {saveParameters} />
  {:else if activeServiceView === "service" || activeServiceView === "system"}
    <ServiceSettings {service} {saveService} />
  {:else}
    <DiagnosticsSettings {runtime} {socketState} {controller} {transactions} {busEvents} {acEntries} />
  {/if}
</section>
