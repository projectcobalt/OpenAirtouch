<script>
  export let title = "";
  export let detail = "";
</script>

<div class="view-heading">
  <strong>{title}</strong>
  {#if detail}<span>{detail}</span>{/if}
</div>
