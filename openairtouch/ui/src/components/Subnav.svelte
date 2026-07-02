<script>
  import { createEventDispatcher } from "svelte";

  export let options = [];
  export let active = "";
  export let className = "";

  const dispatch = createEventDispatcher();
</script>

<div class={`subnav ${className}`.trim()}>
  {#each options as [value, label]}
    <button type="button" class:active={active === value} on:click={() => dispatch("change", value)}>{label}</button>
  {/each}
</div>
