<script>
  import { title } from "../../lib/format.js";

  export let scopedGroupEntries = [];
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let groupIsOn = () => false;
  export let saveGroupName = () => {};
  export let saveGrouping = () => {};
</script>

<div class="card-grid">
  {#each scopedGroupEntries as [id, group]}
    {@const grouping = group.grouping || {}}
    {@const status = group.status || {}}
    <article class="summary-card editor-card" data-service-group={id}>
      <div class="card-head"><div class="card-title">{zoneName(id, group)}</div><span class:selected-pill={groupIsOn(group)}>{title(status.power_name || "off")}</span></div>
      <div class="readonly-summary">
        <span>Dampers {grouping.zone_start ?? Number(id)}-{Number(grouping.zone_start ?? id) + Number(grouping.zone_count ?? 1) - 1}</span>
        <span>Min {grouping.min_percent ?? status.min_percentage ?? 0}%</span>
        <span>{grouping.thermostat_name || `Sensor ${grouping.thermostat ?? 255}`}</span>
      </div>
      <div class="field-grid">
        <label class="field">Name<input data-field="group-name" maxlength="8" value={zoneName(id, group)} /></label>
        <label class="field">First Damper<input data-field="zone-start" type="number" min="0" max="63" value={grouping.zone_start ?? Number(id)} /></label>
        <label class="field">Damper Count<input data-field="zone-count" type="number" min="1" max="4" value={grouping.zone_count ?? 1} /></label>
        <label class="field">Min Open<input data-field="min-percent" type="number" min="0" max="100" value={grouping.min_percent ?? status.min_percentage ?? 0} /></label>
        <label class="field">Sensor<input data-field="thermostat" type="number" min="0" max="255" value={grouping.thermostat ?? 255} /></label>
      </div>
      <div class="service-actions">
        <button type="button" on:click={(event) => saveGroupName(event, id)}>Save Name</button>
        <button type="button" class="action-primary" on:click={(event) => saveGrouping(event, id)}>Save Grouping</button>
      </div>
    </article>
  {/each}
</div>
