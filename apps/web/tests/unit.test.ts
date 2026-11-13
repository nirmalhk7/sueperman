import { test } from "node:test";
import assert from "node:assert/strict";
import { opportunityLabel } from "../lib/labels";
test("simulation label takes priority over candidate status", () => {
  assert.equal(
    opportunityLabel("eligible_candidate", true),
    "Simulated settlement",
  );
  assert.equal(opportunityLabel("verified_match", false), "Recall matched");
  assert.equal(opportunityLabel("rejected", false), "Not affected");
  assert.equal(opportunityLabel("needs_review", false), "Needs information");
});

test("real settlement labels identify public sources and keep eligibility uncertain", async () => {
  const { sourceLabel } = await import("../lib/labels");
  assert.equal(sourceLabel("settlement", "live", false), "LIVE verified settlement sources");
  assert.equal(opportunityLabel("uncertain", false), "Needs information");
  assert.equal(opportunityLabel("ineligible", false), "Not affected");
});
