import { test } from "node:test";
import assert from "node:assert/strict";
import * as labels from "../components/diwali-case-evidence";

test("failed BAND startup never claims local fallback or live delivery", () => {
  const label = (labels as Record<string, unknown>).diwaliTransportLabel as
    ((actual?: string | null, requested?: string) => string) | undefined;
  const render = label || (() => "LOCAL TEST");
  assert.equal(render(null, "band"), "BAND NOT STARTED");
  assert.equal(render("band", "band"), "BAND LIVE");
  assert.equal(render("local", "local"), "LOCAL TEST");
});
