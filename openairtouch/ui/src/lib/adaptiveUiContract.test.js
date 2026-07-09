import assert from "node:assert/strict";
import test from "node:test";

import { isAdaptiveUiReady, validateAdaptiveUiContract } from "./adaptiveUiContract.js";

const validContract = () => ({
  version: 1,
  summary: {
    headline: "Adaptive Ready",
    detail: "No adaptive recommendation is active.",
    authority: "control",
    mode: "adaptive",
    strategy: "hybrid",
    intent: "monitor"
  },
  surfaces: {
    environment: surface(),
    zone: surface(),
    hybrid: surface()
  },
  metrics: [{label: "Authority", value: "Control"}],
  analytics: {
    zones: [
      {
        id: 0,
        state: "Ready",
        flags: ["Ready"],
        badges: [{label: "Progress", value: "100%"}],
        series: {
          history: [],
          forecast: [],
          label: "No chart data",
          meta: "History / Now / Forecast"
        }
      }
    ]
  }
});

const surface = () => ({
  headline: "Watching",
  detail: "Inputs are being watched.",
  state: "monitor",
  fields: []
});

test("validateAdaptiveUiContract accepts the current adaptive UI contract", () => {
  const issues = validateAdaptiveUiContract(validContract());

  assert.deepEqual(issues, []);
  assert.equal(isAdaptiveUiReady(validContract()), true);
});

test("validateAdaptiveUiContract reports missing status and analytics fields loudly", () => {
  const contract = validContract();
  delete contract.summary.headline;
  delete contract.surfaces.hybrid;
  contract.metrics = [];
  delete contract.analytics.zones[0].series.forecast;

  assert.deepEqual(validateAdaptiveUiContract(contract), [
    "adaptive.ui.summary.headline is missing",
    "adaptive.ui.surfaces.hybrid is missing",
    "adaptive.ui.metrics must be a non-empty array",
    "adaptive.ui.analytics.zones[0].series.forecast must be an array"
  ]);
  assert.equal(isAdaptiveUiReady(contract), false);
});
