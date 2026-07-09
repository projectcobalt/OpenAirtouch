const REQUIRED_SURFACES = ["environment", "zone", "hybrid"];
const REQUIRED_SUMMARY_FIELDS = ["headline", "detail", "authority", "mode", "strategy", "intent"];
const REQUIRED_ANALYTICS_CARD_FIELDS = ["id", "kind", "title", "state", "flags", "badges", "chart"];
const REQUIRED_CHART_FIELDS = ["variant", "title", "summary", "unit", "lines", "bands", "windows", "has_data"];

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
  if (!Array.isArray(analytics.cards)) {
    issues.push("adaptive.ui.analytics.cards must be an array");
    return;
  }
  analytics.cards.forEach((card, index) => validateAnalyticsCard(card, index, issues));
}

function validateAnalyticsCard(card, index, issues) {
  if (!card || typeof card !== "object") {
    issues.push(`adaptive.ui.analytics.cards[${index}] is not an object`);
    return;
  }
  for (const key of REQUIRED_ANALYTICS_CARD_FIELDS) {
    if (missing(card[key])) issues.push(`adaptive.ui.analytics.cards[${index}].${key} is missing`);
  }
  if (!Array.isArray(card.flags)) issues.push(`adaptive.ui.analytics.cards[${index}].flags must be an array`);
  if (!Array.isArray(card.badges)) issues.push(`adaptive.ui.analytics.cards[${index}].badges must be an array`);
  validateAnalyticsChart(card.chart, index, issues);
}

function validateAnalyticsChart(chart, cardIndex, issues) {
  if (!chart || typeof chart !== "object") return;
  for (const key of REQUIRED_CHART_FIELDS) {
    if (missing(chart[key])) issues.push(`adaptive.ui.analytics.cards[${cardIndex}].chart.${key} is missing`);
  }
  if (!Array.isArray(chart.lines)) issues.push(`adaptive.ui.analytics.cards[${cardIndex}].chart.lines must be an array`);
  if (!Array.isArray(chart.bands)) issues.push(`adaptive.ui.analytics.cards[${cardIndex}].chart.bands must be an array`);
  if (!Array.isArray(chart.windows)) issues.push(`adaptive.ui.analytics.cards[${cardIndex}].chart.windows must be an array`);
}
