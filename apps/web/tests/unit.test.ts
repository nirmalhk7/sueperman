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
