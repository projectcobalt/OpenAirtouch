<script>
  export let label = "";
  export let dataField = undefined;
  export let value = false;
  export let onLabel = "On";
  export let offLabel = "Off";
</script>

<label class="field">
  {label}
  <select data-field={dataField}>
    <option value="true" selected={!!value}>{onLabel}</option>
    <option value="false" selected={!value}>{offLabel}</option>
  </select>
</label>
