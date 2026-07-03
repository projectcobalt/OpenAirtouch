<script>
  import { title } from "../../lib/format.js";

  export let scopedGroupEntries = [];
  export let balanceRows = {};
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let stepBalance = () => {};
  export let balanceAction = () => {};
</script>

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
