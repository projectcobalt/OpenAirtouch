<script>
  export let scopedGroupEntries = [];
  export let balanceRows = {};
  export let zoneName = (id) => `Zone ${Number(id) + 1}`;
  export let stepBalance = () => {};
  export let balanceAction = () => {};

  let balanceRunning = false;

  const balanceText = (value) => Number(value) > 0 ? `${value}%` : "Disabled";
  const percentText = (value) => value === undefined || value === null ? "-" : `${value}%`;

  function toggleBalance() {
    const nextRunning = !balanceRunning;
    balanceAction(nextRunning ? "balance_start" : "balance_stop");
    balanceRunning = nextRunning;
  }
</script>

<div class="balance-panel">
  <div class="balance-list">
    {#each scopedGroupEntries as [id, group]}
      {@const balance = balanceRows[String(id)] || {}}
      {@const status = group.status || {}}
      {@const setValue = balance.set_value ?? 0}
      <article class="summary-card editor-card balance-row" data-balance-zone={id}>
        <div class="balance-zone">
          <strong>{zoneName(id, group)}</strong>
        </div>
        <div class="balance-value">
          <span>Current</span>
          <strong>{percentText(balance.current_value ?? status.percentage)}</strong>
        </div>
        <div class="balance-value">
          <span>Balance</span>
          <strong data-balance-display>{balanceText(setValue)}</strong>
        </div>
        <div class="balance-row-control">
          <button type="button" title="Decrease balance" on:click={(event) => stepBalance(event, id, -5)}>-</button>
          <input data-balance-number={Number(id)} type="number" min="0" max="100" step="5" value={setValue} aria-label={`Balance for ${zoneName(id, group)}`} on:change={(event) => stepBalance(event, id, 0)} />
          <button type="button" title="Increase balance" on:click={(event) => stepBalance(event, id, 5)}>+</button>
        </div>
        <button type="button" class="balance-apply" on:click={() => balanceAction("balance_start")}>Apply</button>
      </article>
    {/each}
  </div>

  <div class="service-actions balance-footer">
    <button type="button" class:action-primary={!balanceRunning} on:click={toggleBalance}>{balanceRunning ? "Stop Balancing" : "Start Balancing"}</button>
  </div>
</div>
