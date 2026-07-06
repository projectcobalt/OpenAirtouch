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
  export let saveRuntimeConfig = () => {};
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
  $: fallbackTouchpadTemperature = controller.config?.fallback_touchpad_temperature ?? 23;
</script>

<article class="summary-card editor-card app-settings-card">
  <section class="settings-section" data-runtime-config-card>
    <div class="section-title">OpenAirTouch App</div>
    <div class="field-grid">
      <label class="field">Theme<select value={selectedTheme} on:change={(event) => setTheme(event.currentTarget.value)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
      <label class="field">Support Diagnostics<select value={showSupportDiagnostics ? "true" : "false"} on:change={(event) => setShowSupportDiagnostics(event.currentTarget.value === "true")}><option value="false">Hidden</option><option value="true">Visible</option></select></label>
      <label class="field">Fallback OpenAirTouch Temperature<input data-field="fallback-touchpad-temperature" type="number" min="0" max="50" step="0.1" value={fallbackTouchpadTemperature} /></label>
    </div>
    <ActionRow><button type="button" class="action-primary" on:click={saveRuntimeConfig}>Save OpenAirTouch</button></ActionRow>
  </section>

  <section class="settings-section" data-preference-card>
    <div class="section-title">AirTouch Touchpad Preferences</div>
    <div class="field-grid">
      <Field label="System Name" id="system-name-input" maxlength="16" value={system.system_name || ""} />
      <ToggleSelect label="Show AC Errors" dataField="show-ac-errors" value={system.show_ac_errors} />
      <ToggleSelect label="Show Outside Temp" dataField="pref-show-outside-temp" value={system.show_outside_temp} />
      <ToggleSelect label="Show Control Sensor Temperature" dataField="pref-show-control-sensor" value={system.show_control_sensor} />
      <ToggleSelect label="Fahrenheit" dataField="use-fahrenheit" value={system.use_fahrenheit} />
    </div>
    <ActionRow><button type="button" class="action-primary" on:click={savePreference}>Save Touchpad Preferences</button></ActionRow>
  </section>

  <GeneralSettings {system} {groupEntries} {zoneName} {saveParameters} />

  <section class="settings-section">
    <div class="section-title">Installer Info</div>
    <div class="readonly-summary system-info-list">
      {#each systemInfo as item}
        <span>{item.label}: {item.value}</span>
      {/each}
    </div>
  </section>
</article>
