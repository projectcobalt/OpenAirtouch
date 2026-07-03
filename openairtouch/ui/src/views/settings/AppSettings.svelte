<script>
  import Field from "../../components/form/Field.svelte";
  import ToggleSelect from "../../components/form/ToggleSelect.svelte";
  import ActionRow from "../../components/form/ActionRow.svelte";
  import GeneralSettings from "./GeneralSettings.svelte";

  export let runtime = {};
  export let controller = {};
  export let selectedTheme = "system";
  export let showSupportDiagnostics = false;
  export let system = {};
  export let groupEntries = [];
  export let setTheme = () => {};
  export let setShowSupportDiagnostics = () => {};
  export let savePreference = () => {};
  export let saveParameters = () => {};
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;

  function display(value) {
    return value === undefined || value === null || value === "" ? "-" : String(value);
  }

  $: systemInfo = [
    {label: "Device ID", value: display(system.device_id || system.touchpad_id || runtime.src)},
    {label: "Firmware", value: display(system.firmware_version_raw || system.firmware_version || system.software_version)},
    {label: "Hardware", value: display(system.hardware_version_raw || system.hardware_version)},
    {label: "Boot", value: display(system.boot_version_raw || system.boot_version || (runtime.boot_complete ? "Complete" : "Pending"))},
    {label: "Endpoint", value: display(controller.config?.transport === "tcp_serial" ? `${controller.config?.tcp_host}:${controller.config?.tcp_port}` : controller.config?.port)}
  ];
</script>

<div class="summary-grid">
  <article class="summary-card editor-card" data-preference-card>
    <div class="card-title">Display</div>
    <div class="field-grid">
      <label class="field">Theme<select value={selectedTheme} on:change={(event) => setTheme(event.currentTarget.value)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
      <Field label="System Name" id="system-name-input" maxlength="16" value={system.system_name || ""} />
      <ToggleSelect label="Show AC Errors" dataField="show-ac-errors" value={system.show_ac_errors} />
      <ToggleSelect label="Show Outside Temp" dataField="pref-show-outside-temp" value={system.show_outside_temp} />
      <ToggleSelect label="Fahrenheit" dataField="use-fahrenheit" value={system.use_fahrenheit} />
      <ToggleSelect label="Screensaver" dataField="screensaver-enabled" value={system.screensaver_enabled} />
      <Field label="Screen Timeout" dataField="screensaver-timeout" type="number" min="0" max="127" value={system.screensaver_timeout ?? 0} />
      <label class="field">Support Diagnostics<select value={showSupportDiagnostics ? "true" : "false"} on:change={(event) => setShowSupportDiagnostics(event.currentTarget.value === "true")}><option value="false">Hidden</option><option value="true">Visible</option></select></label>
    </div>
    <ActionRow><button type="button" class="action-primary" on:click={savePreference}>Save App</button></ActionRow>
  </article>
  <article class="summary-card editor-card">
    <div class="card-title">System Info</div>
    <div class="readonly-summary system-info-list">
      {#each systemInfo as item}
        <span>{item.label}: {item.value}</span>
      {/each}
    </div>
  </article>
  <GeneralSettings {system} {groupEntries} {zoneName} {saveParameters} />
</div>
