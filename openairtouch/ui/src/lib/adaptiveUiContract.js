const REQUIRED_SURFACES = ["environment", "zone", "hybrid"];
const REQUIRED_SUMMARY_FIELDS = ["headline", "detail", "authority", "mode", "strategy", "intent"];
const REQUIRED_ANALYTICS_ZONE_FIELDS = ["id", "state", "flags", "badges", "series"];

const missing = (value) => value === undefined || value === null || value === "";

export function validateAdaptiveUiContract(ui = {}) {
  const issues = [];
  if (!ui || typeof ui !== "object") return ["adaptive.ui is missing"];
  if (ui.version !== 1) issues.push("adaptive.ui.version must be 1");

  validateSummary(ui.summary, issues);
  validateSurfaces(ui.surfaces, issues);
  validateMetrics(ui.metrics, issues);
  validateAnalytics(ui.analytics, issues);

  return issues;
}

export const isAdaptiveUiReady = (ui = {}) => validateAdaptiveUiContract(ui).length === 0;

function validateSummary(summary, issues) {
  if (!summary || typeof summary !== "object") {
    issues.push("adaptive.ui.summary is missing");
    return;
  }
  for (const key of REQUIRED_SUMMARY_FIELDS) {
    if (missing(summary[key])) issues.push(`adaptive.ui.summary.${key} is missing`);
  }
}

function validateSurfaces(surfaces, issues) {
  if (!surfaces || typeof surfaces !== "object") {
    issues.push("adaptive.ui.surfaces is missing");
    return;
  }
  for (const key of REQUIRED_SURFACES) {
    const surface = surfaces[key];
    if (!surface || typeof surface !== "object") {
      issues.push(`adaptive.ui.surfaces.${key} is missing`);
      continue;
    }
    for (const field of ["headline", "detail", "state"]) {
      if (missing(surface[field])) issues.push(`adaptive.ui.surfaces.${key}.${field} is missing`);
    }
    if (!Array.isArray(surface.fields)) issues.push(`adaptive.ui.surfaces.${key}.fields must be an array`);
  }
}

function validateMetrics(metrics, issues) {
  if (!Array.isArray(metrics) || !metrics.length) {
    issues.push("adaptive.ui.metrics must be a non-empty array");
    return;
  }
  metrics.forEach((metric, index) => {
    if (!metric || typeof metric !== "object") {
      issues.push(`adaptive.ui.metrics[${index}] is not an object`);
      return;
    }
    if (!metric.label) issues.push(`adaptive.ui.metrics[${index}].label is missing`);
    if (missing(metric.value)) issues.push(`adaptive.ui.metrics[${index}].value is missing`);
  });
}

function validateAnalytics(analytics, issues) {
  if (!analytics || typeof analytics !== "object") {
    issues.push("adaptive.ui.analytics is missing");
    return;
  }
  if (!Array.isArray(analytics.zones)) {
    issues.push("adaptive.ui.analytics.zones must be an array");
    return;
  }
  analytics.zones.forEach((zone, index) => validateAnalyticsZone(zone, index, issues));
}

function validateAnalyticsZone(zone, index, issues) {
  if (!zone || typeof zone !== "object") {
    issues.push(`adaptive.ui.analytics.zones[${index}] is not an object`);
    return;
  }
  for (const key of REQUIRED_ANALYTICS_ZONE_FIELDS) {
    if (missing(zone[key])) issues.push(`adaptive.ui.analytics.zones[${index}].${key} is missing`);
  }
  if (!Array.isArray(zone.flags)) issues.push(`adaptive.ui.analytics.zones[${index}].flags must be an array`);
  if (!Array.isArray(zone.badges)) issues.push(`adaptive.ui.analytics.zones[${index}].badges must be an array`);
  if (!zone.series || typeof zone.series !== "object") return;
  if (!Array.isArray(zone.series.history)) issues.push(`adaptive.ui.analytics.zones[${index}].series.history must be an array`);
  if (!Array.isArray(zone.series.forecast)) issues.push(`adaptive.ui.analytics.zones[${index}].series.forecast must be an array`);
  if (missing(zone.series.label)) issues.push(`adaptive.ui.analytics.zones[${index}].series.label is missing`);
  if (missing(zone.series.meta)) issues.push(`adaptive.ui.analytics.zones[${index}].series.meta is missing`);
}
