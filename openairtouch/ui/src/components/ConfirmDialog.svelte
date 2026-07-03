<script>
  export let dialog = null;
  export let resolve = () => {};

  function handleWindowKeydown(event) {
    if (dialog && event.key === "Escape") resolve(false);
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if dialog}
  <div class="confirm-backdrop" role="presentation" on:click={() => resolve(false)}>
    <div
      class="confirm-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      tabindex="-1"
      on:click={(event) => event.stopPropagation()}
      on:keydown={(event) => event.key === "Escape" && resolve(false)}
    >
      <div class="card-title" id="confirm-dialog-title">{dialog.title || "Confirm Change"}</div>
      {#if dialog.message}
        <div class="hero-detail">{dialog.message}</div>
      {/if}
      <div class="service-actions confirm-actions">
        <button type="button" on:click={() => resolve(false)}>{dialog.cancelLabel || "Cancel"}</button>
        <button type="button" class="action-primary" on:click={() => resolve(true)}>{dialog.confirmLabel || "Confirm"}</button>
      </div>
    </div>
  </div>
{/if}
