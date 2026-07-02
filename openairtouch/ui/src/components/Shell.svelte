<script>
  import { createEventDispatcher } from "svelte";
  import SemanticIcon from "./icons/SemanticIcon.svelte";

  export let activeView = "control";

  const dispatch = createEventDispatcher();
  const views = [["control", "Control"], ["favourites", "Favourites"], ["adaptive", "Adaptive"]];
  const selectView = (view) => dispatch("view", view);
</script>

<header class="topbar">
  <div class="brand">
    <span class="mark"><SemanticIcon name="wind" size={16} /></span>
  </div>
  <nav class="view-tabs" aria-label="Views">
    {#each views as [view, label]}
      <button type="button" class:active={activeView === view} on:click={() => selectView(view)}>{label}</button>
    {/each}
  </nav>
  <button type="button" class="settings-button icon-only" class:active={activeView === "service"} on:click={() => selectView("service")} title="Service" aria-label="Service">
    <SemanticIcon name="service" />
  </button>
</header>
