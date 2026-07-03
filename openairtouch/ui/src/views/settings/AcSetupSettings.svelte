<script>
  import { title } from "../../lib/format.js";

  export let acEntries = [];
  export let scopedGroupEntries = [];
  export let system = {};
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let saveAcBase = () => {};
  export let saveAcSettings = () => {};
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
  const hasSelectorBit = (bitmap, groupId) => {
    const group = Number(groupId);
    if (group < 0 || group > 15) return false;
    const mask = Number(bitmap ?? 0);
    return !!(mask & (1 << (group % 8)));
  };
  const isGroupVisibleForSensor = (selectors, groupId) => {
    const group = Number(groupId);
    return group < 8 ? hasSelectorBit(selectors.groups_1_8_bitmap, group) : hasSelectorBit(selectors.groups_9_16_bitmap, group);
  };
  const controlSensorOptions = (selectors = {}, current, groups = scopedGroupEntries) => {
    const options = [{label: "AC", value: 128}];
    if (selectors.auto) options.push({label: "Auto", value: 255});
    if (selectors.economy) options.push({label: "Economy", value: 253});
    if (selectors.average) options.push({label: "Average", value: 254});
    for (const [groupId, group] of groups) {
      if (isGroupVisibleForSensor(selectors, groupId)) options.push({label: zoneName(groupId, group), value: Number(groupId)});
    }
    if (selectors.touchpad_1) options.push({label: "Touchpad 1", value: 144});
    if (selectors.touchpad_2) options.push({label: "Touchpad 2", value: 145});
    const selected = Number(current ?? 128);
    if (!options.some((option) => option.value === selected)) options.push({label: `Raw ${selected}`, value: selected});
    return options;
  };
  const groupEntriesForAc = (base) => {
    if (system.one_duct_system) return scopedGroupEntries;
    const start = Number(base.group_start ?? 0);
    const count = Number(base.group_count ?? 0);
    return scopedGroupEntries.filter(([groupId]) => Number(groupId) >= start && Number(groupId) < start + count);
  };
  const supportsTurboFan = (fans = {}) => fanSpeedSequence(fans.turbo, 0) !== null;
  const isLastAc = (id) => {
    const ids = acEntries.map(([entryId]) => Number(entryId));
    return Number(id) === Math.max(...ids);
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
        <label class="field">AC Name<input data-field="ac-name" maxlength="8" value={base.name || acName(id, ac)} /></label>
        <input data-field="ac-group-start" type="hidden" value={base.group_start ?? 0} />
        {#if !system.one_duct_system}
          <label class="field">AC Groups<input data-field="ac-group-count" type="number" min="0" max="63" value={base.group_count ?? 0} readonly={isLastAc(id)} /></label>
        {/if}
        <input data-field="ac-brand" type="hidden" value={base.brand ?? 0} />
        <label class="field">Auto Off<select data-field="auto-off"><option value="true" selected={settings.auto_off}>On</option><option value="false" selected={!settings.auto_off}>Off</option></select></label>
        <label class="field">On Duration Time<select data-field="on-time-limit">
          {#each [0, 1, 2, 3, 4, 5, 6, 7, 8] as hours}
            <option value={hours} selected={Number(settings.on_time_limit ?? 0) === hours}>{durationLabel(hours)}</option>
          {/each}
        </select></label>
        <label class="field">Control Sensor<select data-field="ctrl-thermostat">
          {#each controlSensorOptions(selectors, settings.ctrl_thermostat) as option}
            <option value={option.value} selected={Number(settings.ctrl_thermostat ?? 128) === option.value}>{option.label}</option>
          {/each}
        </select></label>
        <label class="field">Spill Type<select data-spill-ac={Number(id)}><option value="0" selected={spillType === 0}>No Spill And Bypass</option><option value="1" selected={spillType === 1}>Spill</option><option value="2" selected={spillType === 2}>Bypass</option></select></label>
        {#if spillType === 1}
          <label class="field">Hide Spill Group<select data-field="hide-spill"><option value="true" selected={settings.hide_spill_group}>Yes</option><option value="false" selected={!settings.hide_spill_group}>No</option></select></label>
        {/if}
      </div>
      <details class="advanced-panel capability-panel">
        <summary>Capability Details</summary>
        <div class="support-table-wrap">
          <table class="support-table capability-table">
            <thead>
              <tr><th>Group</th><th>Item</th><th>Value</th></tr>
            </thead>
            <tbody>
              <tr><td>AC Base</td><td>First Zone</td><td>{Number(base.group_start ?? 0) + 1}</td></tr>
              <tr><td>AC Base</td><td>Brand</td><td>{brandName(base.brand)}</td></tr>
              <tr><td>Setpoint Limit</td><td>Minimum</td><td>{settings.min_setpoint ?? 16}</td></tr>
              <tr><td>Setpoint Limit</td><td>Maximum</td><td>{settings.max_setpoint ?? 30}</td></tr>
              <tr><td>Temperature Offset</td><td>Cooling</td><td>{settings.cool_adjust ?? 0}</td></tr>
              <tr><td>Temperature Offset</td><td>Heating</td><td>{settings.heat_adjust ?? 0}</td></tr>
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
      <details class="advanced-panel capability-panel">
        <summary>Spill Zones</summary>
        <div class="chip-grid compact">
          {#each scopedGroupEntries as [groupId, group]}
            <label class="check-row">
              <input type="checkbox" data-spill-group value={Number(groupId)} checked={group.spill_configured || group.status?.spill_on} />
              <span>{zoneName(groupId, group)}</span>
            </label>
          {/each}
        </div>
      </details>
      {#if supportsTurboFan(fans)}
        <div class="field-grid">
          <label class="field">Turbo Group<select data-field="turbo-group">
            <option value="255" selected={Number(turboRecord.group ?? 255) === 255}>None</option>
            {#each groupEntriesForAc(base) as [groupId, group]}
              <option value={Number(groupId)} selected={Number(turboRecord.group) === Number(groupId)}>{zoneName(groupId, group)}</option>
            {/each}
          </select></label>
        </div>
      {/if}
      <div class="service-actions">
        <button type="button" on:click={(event) => saveAcBase(event, id)}>Save Name</button>
        <button type="button" class="action-primary" on:click={(event) => saveAcSettings(event, id)}>Save Settings</button>
        {#if supportsTurboFan(fans)}
          <button type="button" on:click={(event) => saveTurboGroup(event, id)}>Save Turbo Zone</button>
        {/if}
        <button type="button" on:click={saveSpill}>Save Spill</button>
      </div>
    </article>
  {/each}
</div>
