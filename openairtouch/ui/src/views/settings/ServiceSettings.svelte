<script>
  export let service = {};
  export let saveService = () => {};
</script>

<div class="summary-grid">
  <article class="summary-card editor-card service-card" data-service-system>
    <div class="card-title">Service</div>
    <div class="field-grid">
      <label class="field">Installer<input id="service-company-input" maxlength="10" autocomplete="off" value={service.company || service.company_name || ""} /></label>
      <label class="field">Phone<input id="service-phone-input" maxlength="12" autocomplete="off" value={service.phone || service.phone_number || ""} /></label>
      <label class="field">Show Service Due<select data-field="show-service-due"><option value="true" selected={service.show_service_due}>On</option><option value="false" selected={!service.show_service_due}>Off</option></select></label>
      <label class="field">Lock Service Due<select data-field="service-due-locked"><option value="true" selected={service.service_due_locked}>On</option><option value="false" selected={!service.service_due_locked}>Off</option></select></label>
      <label class="field">Filter Clean Due<select data-field="filter-clean-due"><option value="true" selected={service.filter_clean_due}>On</option><option value="false" selected={!service.filter_clean_due}>Off</option></select></label>
      <label class="field">Maintenance Due<select data-field="maintenance-due"><option value="true" selected={service.maintenance_due}>On</option><option value="false" selected={!service.maintenance_due}>Off</option></select></label>
      <label class="field">Service Months<input data-field="service-months" type="number" min="0" max="255" value={service.months ?? 0} /></label>
      <label class="field">Service Days<input data-field="service-days" type="number" min="0" max="65535" value={service.days ?? 0} /></label>
      <label class="field">Runtime Hours<input data-field="service-runtime-hours" type="number" min="0" value={service.runtime_hours ?? 0} /></label>
    </div>
    <div class="service-actions"><button type="button" class="action-primary" on:click={saveService}>Save Service</button></div>
  </article>
</div>
