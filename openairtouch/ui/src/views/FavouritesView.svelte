<script>
  import { createEventDispatcher } from "svelte";
  import Subnav from "../components/Subnav.svelte";
  import ViewHeading from "../components/ViewHeading.svelte";
  import { fanName, modeName } from "../lib/airtouch.js";
  import { tempText } from "../lib/format.js";

  export let options = [];
  export let activeProgramView = "favourites";
  export let favourites = {};
  export let programs = {};
  export let groups = {};
  export let groupEntries = [];
  export let acEntries = [];
  export let pendingKey = "";
  export let favouriteGroups = () => [];
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let groupsFromBitmap = () => [];
  export let groupIsSpill = () => false;
  export let acName = (id) => `AC ${Number(id) + 1}`;
  export let timeText = () => "-";
  export let timeValue = () => "00:00";

  const dispatch = createEventDispatcher();
</script>

<section class="cards-view">
  <ViewHeading title="Favourites" detail={`${Object.keys(favourites).length} saved / ${Object.keys(programs).length} programs`} />
  <Subnav {options} active={activeProgramView} on:change={(event) => dispatch("view", event.detail)} />

  {#if activeProgramView === "favourites"}
    <div class="card-grid">
      {#each Object.entries(favourites).sort((a, b) => Number(a[0]) - Number(b[0])) as [id, favourite]}
        {@const selectedGroups = favouriteGroups(favourite)}
        <article class="summary-card editor-card" data-favourite-card={id}>
          <div class="card-head">
            <div class="card-title">Favourite {Number(id) + 1}: {favourite.name || "Empty"}</div>
            <span class:selected-pill={selectedGroups.length}>{selectedGroups.length ? `${selectedGroups.length} Zones` : "No Zones"}</span>
          </div>
          <div class="readonly-summary">{selectedGroups.length ? selectedGroups.map((groupId) => zoneName(groupId, groups[String(groupId)] || {})).join(", ") : "No Zones Selected"}</div>
          <div class="field-grid">
            <label class="field">Name<input data-field="favourite-name" maxlength="8" value={favourite.name || ""} /></label>
          </div>
          <div class="chip-grid">
            {#each groupEntries as [groupId, group]}
              <label class="check-row">
                <input type="checkbox" data-favourite-group value={Number(groupId)} checked={selectedGroups.includes(Number(groupId))} />
                <span>{zoneName(groupId, group)}</span>
              </label>
            {/each}
          </div>
          <div class="service-actions">
            <button type="button" class="action-primary" disabled={pendingKey === `favourite-apply-${id}`} on:click={() => dispatch("applyFavourite", id)}>Apply</button>
            <button type="button" disabled={pendingKey === `favourite-save-${id}`} on:click={(event) => dispatch("saveFavourite", {event, id})}>Save Favourite</button>
            <button type="button" class="action-danger" disabled={pendingKey === `favourite-clear-${id}`} on:click={() => dispatch("clearFavourite", id)}>Clear</button>
          </div>
        </article>
      {:else}
        <article class="summary-card"><div class="card-title">No Favourite Data</div><div class="hero-detail">Favourite records have not been received yet.</div></article>
      {/each}
    </div>
  {:else if activeProgramView === "programs"}
    <div class="card-grid">
      {#each Object.entries(programs).sort((a, b) => Number(a[0]) - Number(b[0])) as [id, program]}
        {@const programNumber = Number(program.program ?? id)}
        {@const programGroups = groupsFromBitmap(program.groups_1_8_bitmap || 0, program.groups_9_16_bitmap || 0)}
        {@const programAcs = groupsFromBitmap(program.active_ac_bitmap || 0, 0)}
        <article class="summary-card editor-card program-card" data-program={programNumber}>
          <div class="card-head">
            <div class="card-title">Program {programNumber + 1}: {program.name || "Empty"}</div>
            <span class:selected-pill={program.enabled}>{program.enabled ? "Enabled" : "Off"}</span>
          </div>
          <div class="readonly-summary">
            <span>{programGroups.length ? `${programGroups.length} Zones` : "No Zones"}</span>
            <span>{programAcs.length ? `${programAcs.length} ACs` : "No AC"}</span>
            <span>On {timeText(program.on_timer)}</span>
            <span>Off {timeText(program.off_timer)}</span>
          </div>
          <div class="field-grid">
            <label class="field">Name<input data-field="program-name" maxlength="8" value={program.name || ""} /></label>
            <label class="field">Enabled<select data-field="program-enabled"><option value="true" selected={program.enabled}>On</option><option value="false" selected={!program.enabled}>Off</option></select></label>
            <label class="field">On Enabled<select data-field="on-enabled"><option value="true" selected={program.on_timer?.enabled}>On</option><option value="false" selected={!program.on_timer?.enabled}>Off</option></select></label>
            <label class="field">On Time<input data-field="on-time" type="time" value={timeValue(program.on_timer)} /></label>
            <label class="field">Setpoint<input data-field="program-on-setpoint" type="number" min="16" max="30" value={program.on_setpoint ?? 26} /></label>
            <label class="field">Off Enabled<select data-field="off-enabled"><option value="true" selected={program.off_timer?.enabled}>On</option><option value="false" selected={!program.off_timer?.enabled}>Off</option></select></label>
            <label class="field">Off Time<input data-field="off-time" type="time" value={timeValue(program.off_timer)} /></label>
          </div>
          <div class="field-block">
            <span>Days</span>
            <div class="chip-grid compact">
              {#each [["Mon", 1], ["Tue", 2], ["Wed", 3], ["Thu", 4], ["Fri", 5], ["Sat", 6], ["Sun", 0]] as [label, bit]}
                <label class="day-chip"><input type="checkbox" data-program-day value={bit} checked={!!(Number(program.days_bitmap || 0) & (1 << Number(bit)))} /><span>{label}</span></label>
              {/each}
            </div>
          </div>
          <div class="field-block">
            <span>Zones</span>
            <div class="chip-grid">
              {#each groupEntries as [groupId, group]}
                {@const spill = groupIsSpill(group)}
                {#if !spill || programGroups.includes(Number(groupId))}
                  <label class="check-row" class:muted={spill}>
                    <input type="checkbox" data-program-zone value={Number(groupId)} checked={programGroups.includes(Number(groupId))} disabled={spill && !programGroups.includes(Number(groupId))} />
                    <span>{zoneName(groupId, group)}{spill ? " Spill" : ""}</span>
                  </label>
                {/if}
              {/each}
            </div>
          </div>
          <div class="field-block">
            <span>AC</span>
            <div class="chip-grid compact">
              {#each acEntries as [acId, ac]}
                <label class="check-row"><input type="checkbox" data-program-ac value={Number(acId)} checked={programAcs.includes(Number(acId))} /><span>{acName(acId, ac)}</span></label>
              {/each}
            </div>
          </div>
          <div class="service-actions">
            <button type="button" class="action-primary" disabled={pendingKey === `program-save-${programNumber}`} on:click={(event) => dispatch("saveProgram", {event, id: programNumber})}>Save Program</button>
            <button type="button" class="action-danger" disabled={pendingKey === `program-clear-${programNumber}`} on:click={() => dispatch("clearProgram", programNumber)}>Clear</button>
          </div>
        </article>
      {:else}
        <article class="summary-card"><div class="card-title">No Program Data</div><div class="hero-detail">Program records have not been received yet.</div></article>
      {/each}
    </div>
  {:else}
    <div class="card-grid ac-timer-grid">
      {#each acEntries as [id, ac]}
        {@const timer = ac.timer || {}}
        {@const onTimer = timer.on_timer || timer.timer || {}}
        {@const offTimer = timer.off_timer || {}}
        <article class="summary-card editor-card ac-timer-card" data-ac-timer={id}>
          <div class="card-head">
            <div class="card-title">{acName(id, ac)}</div>
            <span class:selected-pill={onTimer.enabled || offTimer.enabled}>{onTimer.enabled || offTimer.enabled ? "Timer Set" : "No Timer"}</span>
          </div>
          <div class="readonly-summary">
            <span>{ac.status?.power_on ? "On" : "Off"}</span>
            <span>{modeName(ac.status?.mode)}</span>
            <span>{fanName(ac.status?.fan)}</span>
            <span>{tempText(ac.status?.setpoint)}</span>
            <span>On {timeText(onTimer)} / Off {timeText(offTimer)}</span>
          </div>
          <div class="field-grid timer-fields">
            <label class="field">On Enabled<select data-field="on-enabled"><option value="true" selected={onTimer.enabled}>On</option><option value="false" selected={!onTimer.enabled}>Off</option></select></label>
            <label class="field">On Time<input data-field="on-time" type="time" value={timeValue(onTimer)} /></label>
            <label class="field">Off Enabled<select data-field="off-enabled"><option value="true" selected={offTimer.enabled}>On</option><option value="false" selected={!offTimer.enabled}>Off</option></select></label>
            <label class="field">Off Time<input data-field="off-time" type="time" value={timeValue(offTimer)} /></label>
          </div>
          <div class="service-actions">
            <button type="button" class="action-primary" disabled={pendingKey === `ac-timer-${id}`} on:click={(event) => dispatch("saveAcTimer", {event, id})}>Save Timer</button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</section>
