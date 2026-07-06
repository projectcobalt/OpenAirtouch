<script>
  export let service = {};
  export let datetimeSync = {};
  export let acEntries = [];
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let saveService = () => {};
  export let resetServiceCounter = () => {};

  const boolValue = (value) => value === true || value === "true";
  const display = (value) => value === undefined || value === null || value === "" ? "-" : value;
  const clockDisplay = (value) => {
    if (!value) return "-";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  $: installerName = service.company || service.company_name || "";
  $: installerPhone = service.phone || service.phone_number || "";
  $: halfYear = boolValue(service.half_year ?? service.service_due_locked);
  $: oneYear = boolValue(service.one_year ?? service.filter_clean_due);
  $: twoYears = boolValue(service.two_years ?? service.maintenance_due);
  $: displayDays = service.display_days ?? service.months ?? 0;
  $: runningDays = service.running_days ?? service.days ?? 0;
  $: clientNumber = service.client_number ?? service.runtime_hours ?? 0;
  $: runHourRows = acEntries
    .map(([id, ac]) => ({
      id,
      name: acName(id, ac),
      hours: ac?.runtime?.running_hours ?? ac?.runtime?.minutes_or_flags
    }))
    .filter((row) => row.hours !== undefined && row.hours !== null);
  $: datetimeRole = datetimeSync.enabled ? "Main Touchpad" : `Standby (${display(datetimeSync.source_address)})`;
  $: datetimeClock = datetimeSync.synced_time || datetimeSync.current_time;
</script>

<article class="summary-card editor-card service-card app-settings-card" data-service-system>
  <section class="settings-section">
    <div class="section-title">Installer Contact</div>
    <div class="field-grid">
      <label class="field">Installers<input id="service-company-input" maxlength="10" autocomplete="off" value={installerName} /></label>
      <label class="field">Number<input id="service-phone-input" maxlength="12" autocomplete="off" value={installerPhone} /></label>
    </div>
  </section>

  <section class="settings-section">
    <div class="section-title">Service Reminder</div>
    <div class="service-option-row">
      <label class="service-check"><input data-field="service-half-year" type="checkbox" checked={halfYear} />Half Year</label>
      <label class="service-check"><input data-field="service-one-year" type="checkbox" checked={oneYear} />One Year</label>
      <label class="service-check"><input data-field="service-two-years" type="checkbox" checked={twoYears} />Two Years</label>
    </div>
    <div class="field-grid">
      <label class="field">Reminder Display Days<input data-field="service-display-days" type="number" min="0" max="255" value={displayDays} /></label>
      <label class="field">Service Counter<input data-field="service-running-days" type="number" min="0" max="65535" value={runningDays} readonly /></label>
      <label class="field">Client No<input data-field="service-client-number" type="number" min="0" value={clientNumber} /></label>
    </div>
    <input data-field="show-service-due" type="hidden" value={service.show_service_due ? "true" : "false"} />
    <div class="service-actions">
      <button type="button" on:click={resetServiceCounter}>Reset Service Counter</button>
      <button type="button" class="action-primary" on:click={saveService}>Save Service</button>
    </div>
  </section>

  <section class="settings-section">
    <div class="section-title">AC Run Hours</div>
    <div class="readonly-summary system-info-list">
      {#if runHourRows.length}
        {#each runHourRows as row}
          <span>{row.name}: {display(row.hours)} h</span>
        {/each}
      {:else}
        <span>No run-hour data</span>
      {/if}
    </div>
  </section>

  <section class="settings-section">
    <div class="section-title">Date Time</div>
    <div class="readonly-summary system-info-list">
      <span>Clock: {clockDisplay(datetimeClock)}</span>
      <span>Zone: {display(datetimeSync.time_zone)}</span>
      <span>Sync: {datetimeRole}</span>
      <span>Last Sync: {clockDisplay(datetimeSync.last_queued_at)}</span>
      {#if datetimeSync.error}
        <span>Error: {datetimeSync.error}</span>
      {/if}
    </div>
  </section>
</article>
