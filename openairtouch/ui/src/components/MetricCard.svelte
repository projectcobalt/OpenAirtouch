<script>
  export let label = "";
  export let value = "";
  export let detail = "";
  export let warning = false;
</script>

<article class="hero-card metric" class:warning>
  <div class="hero-kicker">{label}</div>
  <div class="hero-value small">{value}</div>
  {#if detail}<div class="hero-detail">{detail}</div>{/if}
  <slot />
</article>
