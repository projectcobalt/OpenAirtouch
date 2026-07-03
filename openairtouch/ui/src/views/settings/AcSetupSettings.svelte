<script>
  import { title } from "../../lib/format.js";

  export let acEntries = [];
  export let scopedGroupEntries = [];
  export let system = {};
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let saveAcBase = () => {};
  export let saveAcSettings = () => {};
  export let resetTempOffsets = () => {};
  export let saveTurboGroup = () => {};
  export let saveSpill = () => {};

  let selectedAcId = null;

  const spillTypeLabel = (value) => ({0: "No Spill/Bypass", 1: "Spill", 2: "Bypass"}[Number(value)] || "Reserved");
  const zoneRange = (base) => {
    const start = Number(base.group_start ?? 0);
    const count = Number(base.group_count ?? 0);
    return count > 0 ? `${start + 1}-${start + count}` : "-";
  };
  const brandNames = new Map([
    [2048, "Daikin"],
    [1793, "Daikin"],
    [5376, "Panasonic"],
    [3328, "Fujitsu"],
    [65280, "ME"],
    [1280, "ME"],
    [3840, "MHI"],
    [7936, "Toshiba"],
    [4096, "LG"],
    [5120, "HITACHI"],
    [8704, "Midea/Carrier"],
    [4608, "Samsung"],
    [57856, "Haier/Bonaire"],
    [12288, "Braemar/Gree"]
  ]);
  const brandName = (brand) => brandNames.get(Number(brand)) || (brand === undefined || brand === null ? "-" : `Brand ${brand}`);
  const durationLabel = (hours) => Number(hours) === 0 ? "Keep on" : `${hours} ${Number(hours) === 1 ? "hour" : "hours"}`;
  const fanSpeedSequence = (value, fallback) => {
    const sequence = Number(value ?? fallback);
    return Number.isFinite(sequence) && sequence !== 15 ? sequence : null;
  };

  $: acIdList = acEntries.map(([id]) => String(id));
  $: if (acEntries.length && !acIdList.includes(String(selectedAcId))) selectedAcId = String(acEntries[0][0]);
  $: visibleAcEntries = acEntries.length > 1 ? acEntries.filter(([id]) => String(id) === String(selectedAcId)) : acEntries;
</script>

<div class="card-grid" data-spill-card>
  {#each visibleAcEntries as [id, ac]}
    {@const base = ac.base || {}}
    {@const settings = ac.settings || {}}
    {@const modes = settings.modes || {}}
    {@const fans = settings.fan_values || {}}
    {@const selectors = settings.selector_visibility || {}}
    {@const turboRecord = (system.turbo_group?.records || []).find((item) => Number(item.ac) === Number(id)) || {}}
    {@const spillType = (system.spill?.ac_spill_types || [])[Number(id)]?.value ?? 0}
    <article class="summary-card editor-card ac-setup-card" data-service-ac={id}>
      <div class="ac-card-head">
        {#if acEntries.length > 1}
          <label class="sr-only" for="ac-setup-selector">AC</label>
          <select id="ac-setup-selector" class="ac-title-select" bind:value={selectedAcId}>
            {#each acEntries as [optionId, optionAc]}
              <option value={String(optionId)}>{acName(optionId, optionAc)}</option>
            {/each}
          </select>
        {:else}
          <div class="card-title">{acName(id, ac)}</div>
        {/if}
        <div class="readonly-summary">
          <span>Zones {zoneRange(base)}</span>
          <span>{brandName(base.brand)}</span>
          <span>Set {settings.min_setpoint ?? 16}-{settings.max_setpoint ?? 30}</span>
          <span>{spillTypeLabel(spillType)}</span>
        </div>
      </div>
      <div class="field-grid">
        <label class="field">Name<input data-field="ac-name" maxlength="8" value={base.name || acName(id, ac)} /></label>
        <label class="field">First Zone<input data-field="ac-group-start" type="number" min="0" max="63" value={base.group_start ?? 0} readonly /></label>
        <label class="field">Zone Count<input data-field="ac-group-count" type="number" min="0" max="63" value={base.group_count ?? 0} /></label>
        <input data-field="ac-brand" type="hidden" value={base.brand ?? 0} />
        <label class="field">Cooling Offset<input data-field="cool-adjust" type="number" min="-8" max="7" value={settings.cool_adjust ?? 0} /></label>
        <label class="field">Heating Offset<input data-field="heat-adjust" type="number" min="-8" max="7" value={settings.heat_adjust ?? 0} /></label>
        <label class="field">Min Setpoint<input data-field="min-setpoint" type="number" min="0" max="255" value={settings.min_setpoint ?? 16} /></label>
        <label class="field">Max Setpoint<input data-field="max-setpoint" type="number" min="0" max="255" value={settings.max_setpoint ?? 30} /></label>
        <label class="field">Auto Off<select data-field="auto-off"><option value="true" selected={settings.auto_off}>On</option><option value="false" selected={!settings.auto_off}>Off</option></select></label>
        <label class="field">Time Limit<select data-field="on-time-limit">
          {#each [0, 1, 2, 3, 4, 5, 6, 7, 8] as hours}
            <option value={hours} selected={Number(settings.on_time_limit ?? 0) === hours}>{durationLabel(hours)}</option>
          {/each}
        </select></label>
        <label class="field">Control Sensor<input data-field="ctrl-thermostat" type="number" min="0" max="255" value={settings.ctrl_thermostat ?? 0} /></label>
        <label class="field">Show Spill Zone<select data-field="hide-spill"><option value="false" selected={!settings.hide_spill_group}>On</option><option value="true" selected={settings.hide_spill_group}>Off</option></select></label>
        <label class="field">Spill/Bypass<select data-spill-ac={Number(id)}><option value="0" selected={spillType === 0}>None</option><option value="1" selected={spillType === 1}>Spill</option><option value="2" selected={spillType === 2}>Bypass</option></select></label>
      </div>
      <details class="advanced-panel capability-panel">
        <summary>Capability Details</summary>
        <div class="support-table-wrap">
          <table class="support-table capability-table">
            <thead>
              <tr><th>Group</th><th>Item</th><th>Value</th></tr>
            </thead>
            <tbody>
              {#each ["auto", "cool", "heat", "dry", "fan"] as mode}
                <tr><td>Modes</td><td>{title(mode)}</td><td>{modes[mode] ? "Available" : "Hidden"}</td></tr>
              {/each}
              {#each [["auto", 0], ["quiet", 0], ["low", 1], ["medium", 2], ["high", 3], ["powerful", 0], ["turbo", 0]] as [fan, fallback]}
                {@const sequence = fanSpeedSequence(fans[fan], fallback)}
                <tr><td>Fan Speeds</td><td>{sequence === null ? title(fan) : `${title(fan)} (${sequence})`}</td><td>{sequence === null ? "Hidden" : "Available"}</td></tr>
              {/each}
              {#each ["auto", "touchpad_1", "touchpad_2", "average", "economy"] as selector}
                <tr><td>Control Sensor Menu</td><td>{title(selector)}</td><td>{selectors[selector] ? "Visible" : "Hidden"}</td></tr>
              {/each}
              <tr><td>Control Sensor Menu</td><td>Zones 1-8 Bitmap</td><td>{selectors.groups_1_8_bitmap ?? 0}</td></tr>
              <tr><td>Control Sensor Menu</td><td>Zones 9-16 Bitmap</td><td>{selectors.groups_9_16_bitmap ?? 0}</td></tr>
            </tbody>
          </table>
        </div>
      </details>
      <div class="field-grid">
        <label class="field">Turbo Zone<select data-field="turbo-group">
          <option value="255" selected={Number(turboRecord.group ?? 255) === 255}>Off</option>
          {#each scopedGroupEntries as [groupId, group]}
            <option value={Number(groupId)} selected={Number(turboRecord.group) === Number(groupId)}>{zoneName(groupId, group)}</option>
          {/each}
        </select></label>
      </div>
      <div class="service-actions">
        <button type="button" on:click={(event) => saveAcBase(event, id)}>Save AC Base</button>
        <button type="button" class="action-primary" on:click={(event) => saveAcSettings(event, id)}>Save AC Settings</button>
        <button type="button" on:click={(event) => resetTempOffsets(event, id)}>Reset Offsets</button>
        <button type="button" on:click={(event) => saveTurboGroup(event, id)}>Save Turbo Zone</button>
      </div>
    </article>
  {/each}

  <article class="summary-card editor-card ac-setup-card spill-zone-card">
    <div class="card-title">Spill Zones</div>
    <div class="chip-grid compact">
      {#each scopedGroupEntries as [id, group]}
        {@const status = group.status || {}}
        <label class="check-row">
          <input type="checkbox" data-spill-group value={Number(id)} checked={group.spill_configured || status.spill_on} />
          <span>{zoneName(id, group)}</span>
          <span>{status.spill_on ? `Active ${status.percentage ?? "-"}%` : group.spill_configured ? "Configured" : "Available"}</span>
        </label>
      {/each}
    </div>
    <div class="service-actions">
      <button type="button" class="action-primary" on:click={saveSpill}>Save Spill/Bypass</button>
    </div>
  </article>
</div>
