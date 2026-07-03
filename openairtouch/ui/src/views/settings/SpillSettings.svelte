<script>
  export let scopedGroupEntries = [];
  export let acEntries = [];
  export let system = {};
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let saveSpill = () => {};
</script>

<div class="card-grid" data-spill-card>
  <article class="summary-card editor-card">
    <div class="card-title">Spill Zones</div>
    <div class="chip-grid">
      {#each scopedGroupEntries as [id, group]}
        {@const status = group.status || {}}
        <label class="check-row"><input type="checkbox" data-spill-group value={Number(id)} checked={group.spill_configured || status.spill_on} /><span>{zoneName(id, group)}</span><span>{status.spill_on ? `Open ${status.percentage ?? "-"}%` : "Reported"}</span></label>
      {/each}
    </div>
  </article>
  <article class="summary-card editor-card">
    <div class="card-title">AC Spill Mode</div>
    <div class="field-grid">
      {#each acEntries as [id, ac]}
        {@const configured = (system.spill?.ac_spill_types || [])[Number(id)]?.value ?? 0}
        <label class="field">{acName(id, ac)}<select data-spill-ac={Number(id)}><option value="0" selected={configured === 0}>None</option><option value="1" selected={configured === 1}>Spill</option><option value="2" selected={configured === 2}>Bypass</option></select></label>
      {/each}
    </div>
    <div class="service-actions"><button type="button" class="action-primary" on:click={saveSpill}>Save Spill</button></div>
  </article>
</div>
