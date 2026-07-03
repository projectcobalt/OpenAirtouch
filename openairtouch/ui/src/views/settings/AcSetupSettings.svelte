<script>
  import { title } from "../../lib/format.js";

  export let acEntries = [];
  export let system = {};
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let saveAcBase = () => {};
  export let saveAcSettings = () => {};
  export let resetTempOffsets = () => {};
  export let saveTurboGroup = () => {};
</script>

<div class="card-grid">
  {#each acEntries as [id, ac]}
    {@const base = ac.base || {}}
    {@const settings = ac.settings || {}}
    {@const modes = settings.modes || {}}
    {@const fans = settings.fan_values || {}}
    {@const selectors = settings.selector_visibility || {}}
    {@const turboRecord = (system.turbo_group?.records || []).find((item) => Number(item.ac) === Number(id)) || {}}
    <article class="summary-card editor-card ac-setup-card" data-service-ac={id}>
      <div class="card-title">{acName(id, ac)}</div>
      <div class="readonly-summary">
        <span>Zones {base.group_start ?? 0}-{Number(base.group_start ?? 0) + Number(base.group_count ?? 0) - 1}</span>
        <span>Brand {base.brand ?? "-"}</span>
        <span>Set {settings.min_setpoint ?? 16}-{settings.max_setpoint ?? 30}</span>
      </div>
      <div class="field-grid">
        <label class="field">Name<input data-field="ac-name" maxlength="8" value={base.name || acName(id, ac)} /></label>
        <label class="field">First Zone<input data-field="ac-group-start" type="number" min="0" max="63" value={base.group_start ?? 0} /></label>
        <label class="field">Zone Count<input data-field="ac-group-count" type="number" min="0" max="63" value={base.group_count ?? 0} /></label>
        <input data-field="ac-brand" type="hidden" value={base.brand ?? 0} />
        <label class="field">Cool Adjust<input data-field="cool-adjust" type="number" min="-8" max="7" value={settings.cool_adjust ?? 0} /></label>
        <label class="field">Heat Adjust<input data-field="heat-adjust" type="number" min="-8" max="7" value={settings.heat_adjust ?? 0} /></label>
        <label class="field">Min Set<input data-field="min-setpoint" type="number" min="0" max="255" value={settings.min_setpoint ?? 16} /></label>
        <label class="field">Max Set<input data-field="max-setpoint" type="number" min="0" max="255" value={settings.max_setpoint ?? 30} /></label>
        <label class="field">Auto Off<select data-field="auto-off"><option value="true" selected={settings.auto_off}>On</option><option value="false" selected={!settings.auto_off}>Off</option></select></label>
        <label class="field">Time Limit<input data-field="on-time-limit" type="number" min="0" max="15" value={settings.on_time_limit ?? 0} /></label>
        <label class="field">Thermostat Byte<input data-field="ctrl-thermostat" type="number" min="0" max="255" value={settings.ctrl_thermostat ?? 0} /></label>
        <label class="field">Show Spill<select data-field="hide-spill"><option value="false" selected={!settings.hide_spill_group}>On</option><option value="true" selected={settings.hide_spill_group}>Off</option></select></label>
      </div>
      <div class="field-block">
        <span>Modes</span>
        <div class="chip-grid compact">
          {#each ["auto", "cool", "heat", "dry", "fan"] as mode}
            <label class="field">{title(mode)}<select data-field={`mode-${mode}`}><option value="true" selected={modes[mode]}>On</option><option value="false" selected={!modes[mode]}>Off</option></select></label>
          {/each}
        </div>
      </div>
      <details class="advanced-panel">
        <summary>Fan Value Mapping</summary>
        <div class="field-grid">
          {#each [["auto", 0], ["quiet", 0], ["low", 1], ["medium", 2], ["high", 3], ["powerful", 0], ["turbo", 0]] as [fan, fallback]}
            <label class="field">{title(fan)}<input data-field={`fan-${fan}`} type="number" min="0" max="15" value={fans[fan] ?? fallback} /></label>
          {/each}
        </div>
      </details>
      <details class="advanced-panel">
        <summary>Selector Visibility</summary>
        <div class="field-grid">
          {#each ["auto", "touchpad_1", "touchpad_2", "average", "economy"] as selector}
            <label class="field">{title(selector)}<select data-field={`selector-${selector}`}><option value="true" selected={selectors[selector]}>On</option><option value="false" selected={!selectors[selector]}>Off</option></select></label>
          {/each}
          <label class="field">Selector Zones 1-8<input data-field="selector-groups-1" type="number" min="0" max="255" value={selectors.groups_1_8_bitmap ?? 0} /></label>
          <label class="field">Selector Zones 9-16<input data-field="selector-groups-2" type="number" min="0" max="255" value={selectors.groups_9_16_bitmap ?? 0} /></label>
        </div>
      </details>
      <div class="field-grid">
        <label class="field">Turbo Zone<input data-field="turbo-group" type="number" min="0" max="255" value={turboRecord.group ?? 255} /></label>
      </div>
      <div class="service-actions">
        <button type="button" on:click={(event) => saveAcBase(event, id)}>Save AC Base</button>
        <button type="button" class="action-primary" on:click={(event) => saveAcSettings(event, id)}>Save AC Settings</button>
        <button type="button" on:click={(event) => resetTempOffsets(event, id)}>Reset Offsets</button>
        <button type="button" on:click={(event) => saveTurboGroup(event, id)}>Save Turbo Zone</button>
      </div>
    </article>
  {/each}
</div>
