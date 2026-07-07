import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { adaptiveConfigPayload } from "./commands.js";

function fakeAdaptiveCard(values = {}) {
  return {
    querySelector(selector) {
      return Object.hasOwn(values, selector) ? {value: values[selector]} : null;
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

test("adaptive config view exposes air quality threshold controls", async () => {
  const source = await readFile(new URL("../views/AdaptiveView.svelte", import.meta.url), "utf8");

  assert.match(source, /id="adaptive-dry-humidity-threshold"/);
  assert.match(source, /id="adaptive-co2-ventilation-threshold"/);
  assert.match(source, /Dry Humidity Threshold/);
  assert.match(source, /CO2 Ventilation Threshold/);
});
