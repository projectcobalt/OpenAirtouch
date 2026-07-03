<script>
  export let system = {};
  export let groupEntries = [];
  export let saveParameters = () => {};
</script>

<div class="summary-grid">
  <article class="summary-card editor-card" data-parameters-card>
    <div class="card-title">General</div>
    <div class="field-grid">
      <label class="field">Total Zones<input data-field="group-count" type="number" min="1" max="16" value={system.group_count ?? (groupEntries.length || 1)} /></label>
      <label class="field">Damper RPM<input data-field="damper-rpm" type="number" min="0" max="255" value={system.damper_rpm ?? 100} /></label>
      <label class="field">Touchpad 1 Location<input data-field="touchpad-1-location" type="number" min="0" max="255" value={system.touchpad_1_location ?? 255} /></label>
      <label class="field">Touchpad 2 Location<input data-field="touchpad-2-location" type="number" min="0" max="255" value={system.touchpad_2_location ?? 255} /></label>
      <label class="field">Block AC Button<select data-field="ac-button-blocked"><option value="true" selected={system.ac_button_blocked}>On</option><option value="false" selected={!system.ac_button_blocked}>Off</option></select></label>
      <label class="field">Lock Temp Control<select data-field="lock-to-temp-control"><option value="true" selected={system.lock_to_temp_control}>On</option><option value="false" selected={!system.lock_to_temp_control}>Off</option></select></label>
      <label class="field">Display Control Sensor Temp<select data-field="param-show-control-sensor"><option value="true" selected={system.show_control_sensor}>On</option><option value="false" selected={!system.show_control_sensor}>Off</option></select></label>
    </div>
    <div class="service-actions"><button type="button" class="action-primary" on:click={saveParameters}>Save General</button></div>
  </article>
</div>
