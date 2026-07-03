<script>
  export let label = "";
  export let id = undefined;
  export let dataField = undefined;
  export let type = "text";
  export let value = "";
  export let min = undefined;
  export let max = undefined;
  export let maxlength = undefined;
  export let autocomplete = undefined;
</script>

<label class="field">
  {label}
  <input
    {id}
    data-field={dataField}
    {type}
    {value}
    {min}
    {max}
    {maxlength}
    {autocomplete}
  />
</label>
