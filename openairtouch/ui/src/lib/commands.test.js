import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { adaptiveConfigPayload } from "./commands.js";

function fakeAdaptiveCard(values = {}) {
  return {
    querySelector(selector) {
      if (!Object.hasOwn(values, selector)) return null;
      return typeof values[selector] === "object" ? values[selector] : {value: values[selector]};
    },
    querySelectorAll(selector) {
      return values[selector] || [];
    }
  };
}

test("adaptiveConfigPayload includes air quality thresholds", () => {
  const payload = adaptiveConfigPayload(fakeAdaptiveCard({
    "#adaptive-dry-humidity-threshold": "68",
    "#adaptive-co2-ventilation-threshold": "1250"
  }));

  assert.equal(payload.dry_humidity_threshold, 68);
  assert.equal(payload.co2_ventilation_threshold_ppm, 1250);
});

test("adaptiveConfigPayload uses one comfort margin", () => {
  const payload = adaptiveConfigPayload(fakeAdaptiveCard({
    "#adaptive-comfort-margin": "5"
  }));

  assert.equal(payload.comfort_margin, 5);
  assert.equal(Object.hasOwn(payload, "cool_diff"), false);
  assert.equal(Object.hasOwn(payload, "heat_diff"), false);
});

test("adaptiveConfigPayload includes ac power permission", () => {
  const payload = adaptiveConfigPayload(fakeAdaptiveCard({
    "#adaptive-allow-ac-power-on": "false"
  }));

  assert.equal(payload.allow_ac_power_on, false);
});

test("adaptiveConfigPayload includes hybrid max boost", () => {
  const payload = adaptiveConfigPayload(fakeAdaptiveCard({
    "#adaptive-hybrid-max-boost-degrees": "3"
  }));

  assert.equal(payload.hybrid_max_boost_degrees, 3);
});

test("adaptive config view exposes air quality threshold controls", async () => {
  const source = await readFile(new URL("../views/AdaptiveView.svelte", import.meta.url), "utf8");

  assert.match(source, /id="adaptive-dry-humidity-threshold"/);
  assert.match(source, /id="adaptive-co2-ventilation-threshold"/);
  assert.match(source, /Dry Humidity Threshold/);
  assert.match(source, /CO2 Ventilation Threshold/);
});

test("adaptive config view exposes one comfort margin control", async () => {
  const source = await readFile(new URL("../views/AdaptiveView.svelte", import.meta.url), "utf8");

  assert.match(source, /id="adaptive-comfort-margin"/);
  assert.match(source, /Comfort Margin/);
  assert.match(source, /id="adaptive-allow-ac-power-on"/);
  assert.match(source, /Allow AC Power On/);
  assert.match(source, /<option value="true"/);
  assert.match(source, /<option value="false"/);
  assert.match(source, /id="adaptive-hybrid-max-boost-degrees"/);
  assert.match(source, /Hybrid Max Boost/);
  assert.match(source, /<div class="card-title">Timing And Model Tuning<\/div>/);
  assert.match(source, /adaptive-config-actions/);
  assert.doesNotMatch(source, /<details class="advanced-panel">/);
  assert.doesNotMatch(source, /adaptive-cool-diff/);
  assert.doesNotMatch(source, /adaptive-heat-diff/);
});

test("adaptive analytics view reads zone names from the backend contract", async () => {
  const source = await readFile(new URL("../views/AdaptiveView.svelte", import.meta.url), "utf8");

  assert.doesNotMatch(source, /function analyticsZoneLabel/);
  assert.doesNotMatch(source, /groupEntries\.find/);
  assert.match(source, /return card\.title \|\| "Analytics"/);
  assert.match(source, /analyticsCardTitle\(card\)/);
  assert.match(source, /analyticsChartTitle\(card, chart\)/);
  assert.match(source, /function analyticsFlags/);
  assert.match(source, /normalized !== state/);
  assert.match(source, /normalized !== "ready"/);
  assert.match(source, /normalized !== "learning"/);
});
