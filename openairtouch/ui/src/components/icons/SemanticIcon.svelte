<script>
  import {
    Activity,
    ArrowLeftRight,
    Circle,
    Droplets,
    Fan,
    Flame,
    House,
    Minus,
    Plus,
    Power,
    RefreshCw,
    Settings,
    Snowflake,
    Thermometer,
    ThermometerSun,
    Waves,
    Wind
  } from "@lucide/svelte";

  export let name = "status";
  export let size = 18;
  export let label = "";
  export let strokeWidth = 2;

  const icons = {
    activity: Activity,
    arrowsHorizontal: ArrowLeftRight,
    cool: Snowflake,
    damper: Waves,
    dry: Droplets,
    fan: Fan,
    heat: Flame,
    humidity: Droplets,
    indoor: House,
    minus: Minus,
    outdoor: ThermometerSun,
    plus: Plus,
    power: Power,
    refresh: RefreshCw,
    room: House,
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
