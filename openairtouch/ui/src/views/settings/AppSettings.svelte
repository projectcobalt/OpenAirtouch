<script>
  import Field from "../../components/form/Field.svelte";
  import ToggleSelect from "../../components/form/ToggleSelect.svelte";
  import ActionRow from "../../components/form/ActionRow.svelte";

  export let runtime = {};
  export let controller = {};
  export let selectedTheme = "system";
  export let showSupportDiagnostics = false;
  export let system = {};
  export let setTheme = () => {};
  export let setShowSupportDiagnostics = () => {};
  export let savePreference = () => {};

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
  <article class="summary-card editor-card">
    <div class="card-title">Appearance</div>
    <div class="field">
      <span>Theme</span>
      <div class="theme-choices" role="group" aria-label="Theme">
        {#each [["system", "System"], ["light", "Light"], ["dark", "Dark"]] as [theme, label]}
          <button type="button" class="option" class:active={selectedTheme === theme} on:click={() => setTheme(theme)}>{label}</button>
        {/each}
      </div>
    </div>
  </article>
  <article class="summary-card editor-card" data-preference-card>
    <div class="card-title">Display</div>
    <div class="field-grid">
      <Field label="System Name" id="system-name-input" maxlength="16" value={system.system_name || ""} />
      <ToggleSelect label="Show AC Errors" dataField="show-ac-errors" value={system.show_ac_errors} />
      <ToggleSelect label="Show Outside Temp" dataField="pref-show-outside-temp" value={system.show_outside_temp} />
      <ToggleSelect label="Fahrenheit" dataField="use-fahrenheit" value={system.use_fahrenheit} />
      <ToggleSelect label="Screensaver" dataField="screensaver-enabled" value={system.screensaver_enabled} />
      <Field label="Screen Timeout" dataField="screensaver-timeout" type="number" min="0" max="127" value={system.screensaver_timeout ?? 0} />
    </div>
    <label class="check-row support-toggle">
      <input type="checkbox" checked={showSupportDiagnostics} on:change={(event) => setShowSupportDiagnostics(event.currentTarget.checked)} />
      <span>Show Support Diagnostics</span>
    </label>
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
</div>
