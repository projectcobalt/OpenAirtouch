<script>
  export let system = {};
  export let groupEntries = [];
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let saveParameters = () => {};

  function touchpadLocationOptions(value) {
    const current = Number(value ?? 255);
    const options = [{value: 255, label: "None"}];
    groupEntries.forEach(([id, group]) => {
      options.push({value: Number(id), label: zoneName(id, group)});
    });
    if (!options.some((option) => option.value === current)) {
      options.push({value: current, label: `Current (${current})`});
    }
    return options;
  }
</script>

<article class="summary-card editor-card" data-parameters-card>
  <div class="card-title">AirTouch General</div>
  <div class="field-grid">
    <label class="field">Total Zones<input data-field="group-count" type="number" min="1" max="16" value={system.group_count ?? (groupEntries.length || 1)} /></label>
    <label class="field">Damper Motor RPM<input data-field="damper-rpm" type="number" min="0.1" max="2.5" step="0.1" value={(Number(system.damper_rpm ?? 100) / 100).toFixed(1)} /></label>
    <label class="field">
      Touchpad 1 Zone
      <select data-field="touchpad-1-location">
        {#each touchpadLocationOptions(system.touchpad_1_location) as option}
          <option value={option.value} selected={option.value === Number(system.touchpad_1_location ?? 255)}>{option.label}</option>
        {/each}
      </select>
    </label>
    <label class="field">
      Touchpad 2 Zone
      <select data-field="touchpad-2-location">
        {#each touchpadLocationOptions(system.touchpad_2_location) as option}
          <option value={option.value} selected={option.value === Number(system.touchpad_2_location ?? 255)}>{option.label}</option>
        {/each}
      </select>
    </label>
    <label class="field">Lock Zones To Temp Control<select data-field="lock-to-temp-control"><option value="true" selected={system.lock_to_temp_control}>On</option><option value="false" selected={!system.lock_to_temp_control}>Off</option></select></label>
    <label class="field">Show Control Sensor Temperature<select data-field="param-show-control-sensor"><option value="true" selected={system.show_control_sensor}>On</option><option value="false" selected={!system.show_control_sensor}>Off</option></select></label>
  </div>
  <div class="service-actions"><button type="button" class="action-primary" on:click={saveParameters}>Save General</button></div>
</article>
