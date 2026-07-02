<script>
  import Subnav from "../components/Subnav.svelte";
  import ViewHeading from "../components/ViewHeading.svelte";
  import { fanName, modeName } from "../lib/airtouch.js";
  import { tempText, title } from "../lib/format.js";

  export let options = [];
  export let activeServiceView = "app";
  export let runtime = {};
  export let selectedTheme = "system";
  export let system = {};
  export let runtimeMetrics = [];
  export let sensorRows = [];
  export let groupEntries = [];
  export let selectedGroupEntries = [];
  export let acEntries = [];
  export let balanceRows = {};
  export let rootState = {};
  export let setTheme = () => {};
  export let savePreference = () => {};
  export let pairSensor = () => {};
  export let sensorKindLabel = () => "Sensor";
  export let saveSensorTemperature = () => {};
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let groupIsOn = () => false;
  export let saveGroupName = () => {};
  export let saveGrouping = () => {};
  export let saveSpill = () => {};
  export let stepBalance = () => {};
  export let balanceAction = () => {};
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let saveAcBase = () => {};
  export let saveAcSettings = () => {};
  export let resetTempOffsets = () => {};
  export let saveTurboGroup = () => {};
  export let saveParameters = () => {};
  export let saveService = () => {};
  export let onView = () => {};

  $: scopedGroupEntries = selectedGroupEntries.length ? selectedGroupEntries : groupEntries;
  $: scopedGroupIds = new Set(scopedGroupEntries.map(([id]) => Number(id)));
  $: scopedSensorRows = sensorRows.filter((sensor) => {
    const mappedIds = Array.isArray(sensor.mapped_group_ids) ? sensor.mapped_group_ids.map(Number) : [];
    if (sensor.resolved_group_id !== undefined && sensor.resolved_group_id !== null && scopedGroupIds.has(Number(sensor.resolved_group_id))) return true;
    if (mappedIds.some((groupId) => scopedGroupIds.has(groupId))) return true;
    return mappedIds.length === 0 && (sensor.resolved_group_id === undefined || sensor.resolved_group_id === null);
  });
</script>
<section class="cards-view">
        <ViewHeading title="Settings" detail={runtime.protocol_name || "Runtime"} />
        <Subnav options={options} active={activeServiceView} className="service-subnav" on:change={(event) => onView(event.detail)} />

        {#if activeServiceView === "app"}
          <div class="summary-grid">
            <article class="summary-card editor-card">
              <div class="card-title">Appearance</div>
              <div class="field">
                <span>Theme</span>
                <div class="theme-choices" role="group" aria-label="Theme">
                  {#each [["system", "System"], ["light", "Light"], ["dark", "Dark"]] as [theme, label]}
                    <button type="button" class="option" class:active={selectedTheme === theme} on:click={() => setTheme(theme)}>{label}</button>
                  {/each}
                </div>
              </div>
            </article>
            <article class="summary-card editor-card" data-preference-card>
              <div class="card-title">Display</div>
              <div class="field-grid">
                <label class="field">System Name<input id="system-name-input" maxlength="16" value={system.system_name || ""} /></label>
                <label class="field">Show AC Errors<select data-field="show-ac-errors"><option value="true" selected={system.show_ac_errors}>On</option><option value="false" selected={!system.show_ac_errors}>Off</option></select></label>
                <label class="field">Show Outside Temp<select data-field="pref-show-outside-temp"><option value="true" selected={system.show_outside_temp}>On</option><option value="false" selected={!system.show_outside_temp}>Off</option></select></label>
                <label class="field">Show Control Sensor<select data-field="pref-show-control-sensor"><option value="true" selected={system.show_control_sensor}>On</option><option value="false" selected={!system.show_control_sensor}>Off</option></select></label>
                <label class="field">Fahrenheit<select data-field="use-fahrenheit"><option value="true" selected={system.use_fahrenheit}>On</option><option value="false" selected={!system.use_fahrenheit}>Off</option></select></label>
                <label class="field">Screensaver<select data-field="screensaver-enabled"><option value="true" selected={system.screensaver_enabled}>On</option><option value="false" selected={!system.screensaver_enabled}>Off</option></select></label>
                <label class="field">Screen Timeout<input data-field="screensaver-timeout" type="number" min="0" max="127" value={system.screensaver_timeout ?? 0} /></label>
                <label class="field">Location<input data-field="location" type="number" min="0" max="127" value={system.location ?? system.address_or_location ?? 0} /></label>
              </div>
              <div class="service-actions"><button type="button" class="action-primary" on:click={savePreference}>Save App</button></div>
            </article>
            {#each runtimeMetrics as item}
              <article class="summary-card metric-card"><span>{item.label}</span><strong>{item.value}</strong></article>
            {/each}
          </div>
        {:else if activeServiceView === "sensors"}
          <div class="service-actions top-actions">
            <button type="button" class="action-primary" on:click={() => pairSensor(true)}>Start Pair</button>
            <button type="button" on:click={() => pairSensor(false)}>Stop Pair</button>
          </div>
          <div class="card-grid">
            {#each scopedSensorRows as sensor}
              <article class="summary-card editor-card sensor-card" data-sensor-row={sensor.id}>
                <div class="card-head">
                  <div class="card-title">{sensor.name}</div>
                  <span class:selected-pill={sensor.present !== false}>{sensor.present === false ? "Missing" : sensorKindLabel(sensor.kind)}</span>
                </div>
                <div class="readonly-summary">
                  <span>{sensor.address}</span>
                  <span>{sensor.temperature === undefined || sensor.temperature === null ? "-" : tempText(sensor.temperature, 1)}</span>
                  <span>Mapped {sensor.mapped_groups?.length ? sensor.mapped_groups.join(", ") : "-"}</span>
                </div>
                {#if sensor.kind !== "supply_air" && sensor.temperature !== undefined && sensor.temperature !== null}
                  <div class="sensor-calibration">
                    <input type="range" min="-10" max="40" step="1" value={Math.round(sensor.temperature)} data-sensor-temperature />
                    <button type="button" on:click={(event) => saveSensorTemperature(event, sensor.id)}>Revise Sensor Temperature</button>
                  </div>
                {:else}
                  <div class="hero-detail">Calibration unavailable</div>
                {/if}
              </article>
            {:else}
              <article class="summary-card"><div class="card-title">No Sensor Data</div><div class="hero-detail">Pairing or sensor list data has not been received yet.</div></article>
            {/each}
          </div>
        {:else if activeServiceView === "grouping"}
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
        {:else if activeServiceView === "spill"}
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
        {:else if activeServiceView === "balance"}
          <div class="card-grid">
            {#each scopedGroupEntries as [id, group]}
              {@const balance = balanceRows[String(id)] || {}}
              {@const status = group.status || {}}
              <article class="summary-card editor-card balance-row" data-balance-zone={id}>
                <div class="card-head"><div class="card-title">{zoneName(id, group)}</div><span>{title(status.power_name || "off")}</span></div>
                <div class="readonly-summary"><span>Current {balance.current_value ?? status.percentage ?? "-"}</span><span>Max Opening</span></div>
                <div class="balance-row-control">
                  <button type="button" on:click={(event) => stepBalance(event, id, -5)}>-</button>
                  <input data-balance-number={Number(id)} type="number" min="0" max="255" value={balance.set_value ?? 0} />
                  <button type="button" on:click={(event) => stepBalance(event, id, 5)}>+</button>
                </div>
              </article>
            {/each}
            <article class="summary-card editor-card">
              <div class="card-title">Balance Mode</div>
              <div class="hero-detail">Start balance before setting individual zones, then stop when airflow balancing is complete.</div>
              <div class="service-actions">
                <button type="button" class="action-primary" on:click={() => balanceAction("balance_start")}>Start Balance</button>
                <button type="button" on:click={() => balanceAction("balance_stop")}>Stop Balance</button>
              </div>
            </article>
          </div>
        {:else if activeServiceView === "ac-setup"}
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
        {:else if activeServiceView === "parameters"}
          <div class="summary-grid">
            <article class="summary-card editor-card" data-parameters-card>
              <div class="card-title">Parameters</div>
              <div class="field-grid">
                <label class="field">Groups<input data-field="group-count" type="number" min="1" max="16" value={system.group_count ?? (groupEntries.length || 1)} /></label>
                <label class="field">Damper RPM<input data-field="damper-rpm" type="number" min="0" max="255" value={system.damper_rpm ?? 100} /></label>
                <label class="field">Touchpad 1<input data-field="touchpad-1-location" type="number" min="0" max="255" value={system.touchpad_1_location ?? 255} /></label>
                <label class="field">Touchpad 2<input data-field="touchpad-2-location" type="number" min="0" max="255" value={system.touchpad_2_location ?? 255} /></label>
                <label class="field">Block AC Button<select data-field="ac-button-blocked"><option value="true" selected={system.ac_button_blocked}>On</option><option value="false" selected={!system.ac_button_blocked}>Off</option></select></label>
                <label class="field">Outside Temp<select data-field="param-show-outside-temp"><option value="true" selected={system.show_outside_temp}>On</option><option value="false" selected={!system.show_outside_temp}>Off</option></select></label>
                <label class="field">Lock Temp Control<select data-field="lock-to-temp-control"><option value="true" selected={system.lock_to_temp_control}>On</option><option value="false" selected={!system.lock_to_temp_control}>Off</option></select></label>
                <label class="field">Control Sensor<select data-field="param-show-control-sensor"><option value="true" selected={system.show_control_sensor}>On</option><option value="false" selected={!system.show_control_sensor}>Off</option></select></label>
              </div>
              <div class="service-actions"><button type="button" class="action-primary" on:click={saveParameters}>Save Parameters</button></div>
            </article>
            <article class="summary-card metric-card"><span>Device ID</span><strong>{system.device_id || "-"}</strong></article>
            <article class="summary-card metric-card"><span>Firmware</span><strong>{system.firmware_version_raw || "-"}</strong></article>
            <article class="summary-card metric-card"><span>Sensors</span><strong>{(system.sensor_addresses || []).join(", ") || "-"}</strong></article>
          </div>
        {:else if activeServiceView === "system"}
          <div class="summary-grid">
            <article class="summary-card editor-card" data-service-system>
              <div class="card-title">System Info</div>
              <div class="field-grid">
                <label class="field">Service Company<input id="service-company-input" maxlength="10" autocomplete="off" value={service.company || service.company_name || ""} /></label>
                <label class="field">Service Phone<input id="service-phone-input" maxlength="12" autocomplete="off" value={service.phone || service.phone_number || ""} /></label>
                <label class="field">Show Service Due<select data-field="show-service-due"><option value="true" selected={service.show_service_due}>On</option><option value="false" selected={!service.show_service_due}>Off</option></select></label>
                <label class="field">Lock Service Due<select data-field="service-due-locked"><option value="true" selected={service.service_due_locked}>On</option><option value="false" selected={!service.service_due_locked}>Off</option></select></label>
                <label class="field">Filter Clean Due<select data-field="filter-clean-due"><option value="true" selected={service.filter_clean_due}>On</option><option value="false" selected={!service.filter_clean_due}>Off</option></select></label>
                <label class="field">Maintenance Due<select data-field="maintenance-due"><option value="true" selected={service.maintenance_due}>On</option><option value="false" selected={!service.maintenance_due}>Off</option></select></label>
                <label class="field">Months<input data-field="service-months" type="number" min="0" max="255" value={service.months ?? 0} /></label>
                <label class="field">Days<input data-field="service-days" type="number" min="0" max="65535" value={service.days ?? 0} /></label>
                <label class="field">Runtime Hours<input data-field="service-runtime-hours" type="number" min="0" value={service.runtime_hours ?? 0} /></label>
              </div>
              <div class="service-actions"><button type="button" class="action-primary" on:click={saveService}>Save Service</button></div>
            </article>
            <article class="summary-card metric-card"><span>Device ID</span><strong>{system.device_id || "-"}</strong></article>
            <article class="summary-card metric-card"><span>Firmware</span><strong>{system.firmware_version_raw || "-"}</strong></article>
            <article class="summary-card metric-card"><span>Supply Air</span><strong>{(system.supply_air || []).join(", ") || "-"}</strong></article>
          </div>
        {:else}
          <div class="summary-grid">
            {#each runtimeMetrics as item}
              <article class="summary-card metric-card"><span>{item.label}</span><strong>{item.value}</strong></article>
            {/each}
            <article class="summary-card metric-card"><span>Last LED</span><strong>{rootState.last_led?.led_code ?? "-"}</strong></article>
            <article class="summary-card metric-card"><span>Touchpads</span><strong>{(system.sensor_list?.touchpad_addresses || []).join(", ") || "-"}</strong></article>
            <article class="summary-card metric-card"><span>Runtime</span><strong>{system.expanded?.software_version || "-"}</strong></article>
          </div>
        {/if}
      </section>
