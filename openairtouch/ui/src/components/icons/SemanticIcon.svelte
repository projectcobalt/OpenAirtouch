<script>
  import {
    Activity,
    Circle,
    Droplets,
    Fan,
    Flame,
    Minus,
    Plus,
    Power,
    RefreshCw,
    Settings,
    Snowflake,
    Thermometer,
    Waves,
    Wind
  } from "@lucide/svelte";

  export let name = "status";
  export let size = 18;
  export let label = "";
  export let strokeWidth = 2;

  const icons = {
    activity: Activity,
    cool: Snowflake,
    damper: Waves,
    dry: Droplets,
    fan: Fan,
    heat: Flame,
    humidity: Droplets,
    minus: Minus,
    plus: Plus,
    power: Power,
    refresh: RefreshCw,
    room: Thermometer,
    service: Settings,
    status: Circle,
    temperature: Thermometer,
    wind: Wind
  };

  $: Icon = icons[name] || Circle;
</script>

<Icon
  aria-hidden={label ? undefined : "true"}
  aria-label={label || undefined}
  class="semantic-icon"
  {size}
  {strokeWidth}
/>
