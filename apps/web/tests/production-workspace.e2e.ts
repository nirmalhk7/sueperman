import { test, expect } from "@playwright/test";

// Catches exposing synthetic stored records as real purchases, or restoring
// sample/reset/replay controls in the public workspace.
test("workspace offers real purchases without demo controls", async ({ page }) => {
  const record = {
    id: "real-product", purchase_id: "real-purchase", demo: false, source_type: "csv",
    created_at: "2026-11-17T12:00:00Z", updated_at: "2026-11-17T12:00:00Z",
    product: {
      product_name: "Imported power bank", brand: "NEWDERY", model_number: "ZHX-PB22",
      merchant: "Purchase history", upc: null, serial_number: null, serial_prefix: null,
      batch: null, region: null, date_purchased: "2024-06-12", order_reference_redacted: null,
      extraction_confidence: 1, suggested_identifiers: {}, user_confirmed_identifiers: false,
    },
  };
  await page.route("**/api/products", route => route.fulfill({ json: [
    record,
    { ...record, id: "synthetic-product", purchase_id: "synthetic-purchase", demo: true,
      product: { ...record.product, product_name: "Stored synthetic purchase" } },
  ] }));
  await page.goto("/");
  await expect(page.getByTestId("purchase-row")).toHaveCount(1);
  await expect(page.getByTestId("purchase-row")).toContainText("Imported power bank");
  await expect(page.getByText("Stored synthetic purchase")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /try demo|reset demo|replay/i })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Run mode" })).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(/demo|offline replay|synthetic case|simulated case/i);
});

for (const target of ["runs", "opportunities", "claims"]) {
  test(`historical ${target} cannot expose recorded content or actions`, async ({ page }) => {
    const endpoint = target === "claims" ? "claim-packets" : target;
    await page.route(`**/api/${endpoint}/historical`, route => route.fulfill({ json: {
      id: "historical", run_id: "historical", mode: "replay", demo: true,
      simulated: true, status: "completed", provider_modes: { recall: "replay" },
      warnings: [], summary: {}, opportunities: [], markdown: "Historical fixture content",
      product: { demo: true },
    } }));
    await page.route("**/api/runs/historical/events", route => route.fulfill({ json: [] }));
    await page.goto(`/${target}/historical`);
    await expect(page.getByText("Investigation unavailable")).toBeVisible();
    await expect(page.getByText("Historical fixture content")).toHaveCount(0);
    await expect(page.getByRole("button", { name: /approve|export|prepare|recorded/i })).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(/demo|offline replay|simulated case/i);
  });
}

test("historical synthetic team runs cannot appear as live investigations", async ({ page }) => {
  await page.route("**/api/collaborations/historical", route => route.fulfill({ json: {
    id: "historical", mode: "live", demo: true, status: "partial", current: true,
    revision: 1, current_revision: 1, board: {}, warnings: [], evidence: [],
  } }));
  await page.route("**/api/collaborations/historical/events", route => route.fulfill({ json: [] }));
  await page.goto("/collaborations/historical");
  await expect(page.getByRole("heading", { name: "Investigation unavailable" })).toBeVisible();
  await expect(page.getByText("Live investigation · inspect sources and role outcomes")).toHaveCount(0);
});
