<script>
  import SemanticIcon from "../../components/icons/SemanticIcon.svelte";

  export let scopedGroupEntries = [];
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let saveGroupName = () => {};
  export let saveGrouping = () => {};

  let drafts = {};

  function initialDraft(id, grouping = {}, status = {}) {
    return {
      zone_start: Number(grouping.zone_start ?? id),
      zone_count: Number(grouping.zone_count ?? 1),
      min_percent: Number(grouping.min_percent ?? status.min_percentage ?? 0),
      thermostat: Number(grouping.thermostat ?? 0)
    };
  }

  function draftFor(id, grouping = {}, status = {}) {
    const key = String(id);
    if (!drafts[key]) drafts[key] = initialDraft(id, grouping, status);
    return drafts[key];
  }

  function updateDraft(id, patch) {
    const key = String(id);
    drafts = {...drafts, [key]: {...(drafts[key] || {}), ...patch}};
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function stepCount(id, delta) {
    const draft = drafts[String(id)] || initialDraft(id);
    updateDraft(id, {zone_count: clamp(Number(draft.zone_count || 1) + delta, 1, 4)});
  }

  function stepMinVent(id, delta) {
    const draft = drafts[String(id)] || initialDraft(id);
    updateDraft(id, {min_percent: clamp(Number(draft.min_percent || 0) + delta, 0, 50)});
  }

  function zoneRange(draft) {
    const start = Number(draft.zone_start || 0);
    const count = Number(draft.zone_count || 1);
    const zones = Array.from({length: count}, (_, index) => start + index + 1);
    return `[Zone ${zones.join(",")}]`;
  }

  function thermostatOptions(grouping = {}) {
    const options = [{label: "Auto", value: 0}];
    if (grouping.has_sensor_1 || grouping.available_selectors?.includes("rf_sensor_1")) options.push({label: "Sensor 1", value: 1});
    if (grouping.has_sensor_2 || grouping.available_selectors?.includes("rf_sensor_2")) options.push({label: "Sensor 2", value: 2});
    if (grouping.has_touchpad_1 || grouping.available_selectors?.includes("touchpad_1")) options.push({label: "TouchPad 1", value: 144});
    if (grouping.has_touchpad_2 || grouping.available_selectors?.includes("touchpad_2")) options.push({label: "TouchPad 2", value: 145});
    if (grouping.has_average || grouping.available_selectors?.includes("average")) options.push({label: "Average", value: 254});
    options.push({label: "None", value: 255});
    return options;
  }

  function thermostatLabel(value, grouping = {}) {
    return thermostatOptions(grouping).find((option) => Number(option.value) === Number(value))?.label || `Selector ${value}`;
  }
</script>

<div class="grouping-list">
  {#each scopedGroupEntries as [id, group]}
    {@const grouping = group.grouping || {}}
    {@const status = group.status || {}}
    {@const draft = draftFor(id, grouping, status)}
    <article class="summary-card editor-card grouping-row" data-service-group={id}>
      <input type="hidden" data-field="zone-start" value={draft.zone_start} />
      <input type="hidden" data-field="zone-count" value={draft.zone_count} />
      <input type="hidden" data-field="min-percent" value={draft.min_percent} />

      <div class="grouping-name">
        <div class="grouping-name-edit">
          <input data-field="group-name" maxlength="8" value={zoneName(id, group)} aria-label="Group name" />
          <button type="button" title="Save group name" on:click={(event) => saveGroupName(event, id)}>Save Name</button>
        </div>
      </div>

      <div class="grouping-zone">{zoneRange(draft)}</div>

      <div class="grouping-control">
        <span>Zones</span>
        <div class="stepper-control" aria-label="Zone count">
          <button type="button" aria-label="Decrease zone count" on:click={() => stepCount(id, -1)}><SemanticIcon name="minus" size={15} /></button>
          <strong>{draft.zone_count}</strong>
          <button type="button" aria-label="Increase zone count" on:click={() => stepCount(id, 1)}><SemanticIcon name="plus" size={15} /></button>
        </div>
      </div>

      <div class="grouping-control">
        <span>Min Vent</span>
        <div class="stepper-control min-vent-control" aria-label="Minimum vent">
          <button type="button" aria-label="Decrease minimum vent" on:click={() => stepMinVent(id, -5)}><SemanticIcon name="minus" size={15} /></button>
          <strong>{draft.min_percent}%</strong>
          <button type="button" aria-label="Increase minimum vent" on:click={() => stepMinVent(id, 5)}><SemanticIcon name="plus" size={15} /></button>
        </div>
      </div>

      <label class="field grouping-thermostat">
        <span class="sr-only">Temp Control</span>
        <select data-field="thermostat" value={draft.thermostat} on:change={(event) => updateDraft(id, {thermostat: Number(event.currentTarget.value)})}>
          {#each thermostatOptions(grouping) as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <div class="service-actions grouping-actions">
        <button type="button" class="action-primary" title={`Save ${zoneRange(draft)} with ${draft.min_percent}% minimum vent and ${thermostatLabel(draft.thermostat, grouping)} temp control`} on:click={(event) => saveGrouping(event, id)}>Save</button>
      </div>
    </article>
  {/each}
</div>
