import assert from "node:assert/strict";
import test from "node:test";

import { analyticsChartData, lineClass } from "./adaptiveChart.js";

test("analyticsChartData marks backend non-meaningful charts as muted", () => {
  const chart = analyticsChartData({
    title: "Hybrid Plan",
    summary: "No plan",
    has_data: true,
    meaningful: false,
    lines: [
      {key: "room", kind: "actual", points: [{x: 100, y: 23.8}, {x: 160, y: 23.8}]}
    ],
    bands: [{min: 21.5, max: 22.5}],
    windows: [{start: 100, end: 160}]
  });

  assert.equal(chart.hasData, true);
  assert.equal(chart.meaningful, false);
  assert.equal(chart.summary, "No plan");
  assert.equal(chart.bands.length, 0);
  assert.equal(chart.windows.length, 0);
});

test("analyticsChartData normalizes mixed timestamp and offset x domains", () => {
  const chart = analyticsChartData({
    title: "Zone Plan",
    summary: "Plan active",
    has_data: true,
    meaningful: true,
    lines: [
      {key: "room", kind: "actual", points: [{x: 113631.7, y: 23.8}, {x: 113691.7, y: 23.7}]},
      {key: "prediction", kind: "forecast", points: [{x: 0, y: 23.6}, {x: 5, y: 23.3}]}
    ],
    bands: [],
    windows: []
  });

  const path = chart.linePaths.find((line) => line.key === "prediction").path;

  assert.match(path, /^M106\.7 /);
  assert.match(path, /L160\.0 /);
});

test("lineClass maps contract line kinds to chart classes", () => {
  assert.equal(lineClass("forecast"), "chart-line chart-line-forecast");
  assert.equal(lineClass(), "chart-line chart-line-actual");
});
