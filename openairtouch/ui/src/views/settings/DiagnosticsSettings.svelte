<script>
  import { title } from "../../lib/format.js";

  export let runtime = {};
  export let socketState = "offline";
  export let controller = {};
  export let transactions = {};
  export let busEvents = [];
  export let acEntries = [];

  function protocolName(currentRuntime) {
    const raw = String(currentRuntime.protocol_name || currentRuntime.protocol || currentRuntime.detected_protocol || "").trim();
    const key = raw.toLowerCase().replace(/[\s_-]+/g, "");
    const names = {
      at4: "AirTouch 4",
      airtouch4: "AirTouch 4",
      at5: "AirTouch 5",
      airtouch5: "AirTouch 5"
    };
    return names[key] || title(raw || "unknown");
  }

  function acFaults(entries) {
    return entries.filter(([_id, ac]) => {
      const code = Number(ac?.status?.error_code || 0);
      return Number.isFinite(code) && code !== 0;
    });
  }

  function healthPills(currentRuntime, currentSocketState, currentController, currentTransactions, currentAcEntries) {
    const faults = acFaults(currentAcEntries);
    const failed = currentTransactions.failed?.length || 0;
    return [
      {label: "Service", value: title(currentController.status || "unknown"), state: currentController.error ? "bad" : currentController.status === "running" ? "good" : "warn"},
      {label: "Link", value: currentSocketState === "live" ? "Live" : title(currentSocketState || "offline"), state: currentSocketState === "live" ? "good" : "warn"},
      {label: "Bus", value: currentRuntime.connected ? "Active" : "Waiting", state: currentRuntime.connected ? "good" : "warn"},
      {label: "Protocol", value: protocolName(currentRuntime), state: currentRuntime.protocol_mismatch ? "bad" : currentRuntime.protocol || currentRuntime.protocol_name || currentRuntime.detected_protocol ? "good" : "warn"},
      {label: "Faults", value: currentController.error || faults.length || failed ? "Check" : "Clear", state: currentController.error || faults.length || failed ? "bad" : "good"}
    ];
  }

  function eventSeverity(event) {
    if (event.plain?.severity === "warning") return "warn";
    if (event.plain?.severity === "error") return "error";
    if (event.crc_ok === false || event.event === "controller") return "error";
    if (event.event === "transaction" || event.event === "status") return "warn";
    return "info";
  }

  function eventMessage(event) {
    if (event.plain?.text) return event.plain.text;
    if (event.summary) return event.summary;
    if (event.plain?.headline) return [event.plain.headline, event.plain.detail].filter(Boolean).join(": ");
    if (event.message) return event.message;
    if (event.transaction?.name) return event.transaction.name;
    if (event.decoded?.type) return title(event.decoded.type);
    if (event.decoded?.message_type) return title(event.decoded.message_type);
    return "";
  }

  function eventCategory(event) {
    return event.plain?.category_label || title(event.plain?.category || event.event || "-");
  }

  function busEventRows(events) {
    const rows = (events || []).slice(-18).reverse().map((event) => {
      const direction = event.direction ? title(event.direction) : title(event.event || "event");
      const path = event.src && event.dest ? `${direction} ${event.src} -> ${event.dest}` : direction;
      const message = eventMessage(event);
      return {
        frame: event.packet_id === undefined || event.packet_id === null ? "-" : `#${event.packet_id}`,
        type: eventCategory(event),
        severity: eventSeverity(event),
        source: event.cmd_name || event.cmd || title(event.event || "-"),
        message: message || path
      };
    });
    return rows.length ? rows : [{frame: "-", type: "-", severity: "info", source: "-", message: "No bus messages yet"}];
  }

  $: pills = healthPills(runtime, socketState, controller, transactions, acEntries);
  $: rows = busEventRows(busEvents);
</script>

<div class="support-diagnostics">
  <div class="support-strip" aria-label="Support health">
    {#each pills as pill}
      <div class={`support-pill ${pill.state}`}>
        <span>{pill.label}</span>
        <strong>{pill.value}</strong>
      </div>
    {/each}
  </div>

  <article class="summary-card support-stream">
    <div class="support-table-wrap">
      <table class="support-table">
        <thead>
          <tr><th>Frame</th><th>Type</th><th>Command</th><th>Message</th></tr>
        </thead>
        <tbody>
          {#each rows as row}
            <tr class={row.severity}>
              <td>{row.frame}</td>
              <td>{row.type}</td>
              <td>{row.source}</td>
              <td>{row.message}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </article>
</div>
