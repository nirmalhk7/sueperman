import { test, expect } from "@playwright/test";
import { api, importPurchases } from "./purchases";
import { readFile } from "node:fs/promises";

test("imported purchases produce evidence-backed recall, safe export and visible negative cases", async ({
  page,
}, testInfo) => {
  await importPurchases(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Find recalls and settlements hiding in your purchase history.",
    }),
  ).toBeVisible();
  await expect(page.getByTestId("purchase-row")).toHaveCount(3);
  await page.getByRole("button", { name: "Check my purchases" }).click();
  await expect(page.getByText("Run completed", { exact: true })).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByTestId("opportunity-card")).toHaveCount(3);
  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
  });
  const exact = page
    .getByTestId("opportunity-card")
    .filter({ hasText: "Recall matched" });
  await exact.getByRole("link", { name: "Review details" }).click();
  await expect(
    page.getByRole("heading", { name: "Recall matched — review details" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /U.S. Consumer Product Safety Commission/ }),
  ).toHaveAttribute("href", /https:\/\/(www\.)?cpsc\.gov\/Recalls\//);
  await expect(
    page.getByText("ZHX-PB22", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText(/LIVE CPSC lookup/).first(),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("evidence.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  const draft = page.getByRole("article", { name: "Remedy draft" });
  await expect(draft.getByRole("heading", { name: "Verified product facts" })).toBeVisible();
  await expect(draft.locator("dd").filter({ hasText: "ZHX-PB22" })).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Export Markdown" }),
  ).toBeDisabled();
  await page
    .getByLabel("I reviewed this draft and understand approval stays local.")
    .check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  await expect(
    page.getByText("Approved locally", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("packet.png"),
    fullPage: true,
  });
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const download = await downloadPromise;
  const path = await download.path();
  const content = await readFile(path!, "utf8");
  expect(content).toContain("ZHX-PB22");
  expect(content).toContain("not an external submission");
  expect(content).toMatch(/https:\/\/(www\.)?cpsc\.gov\/Recalls\//);
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await page
    .getByTestId("opportunity-card")
    .filter({ hasText: "Not affected" })
    .getByRole("link", { name: "Review details" })
    .click();
  await expect(
    page.getByText("REJECTED — MODEL MISMATCH", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Prepare claim packet" }),
  ).toHaveCount(0);
  await page.screenshot({
    path: testInfo.outputPath("rejection.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await page
    .getByTestId("opportunity-card")
    .filter({ hasText: "Needs information" })
    .getByRole("link", { name: "Review details" })
    .click();
  await expect(page).toHaveURL(/\/opportunities\//);
  await expect(page.getByRole("heading", { level: 1, name: "Needs information" })).toBeVisible();
  await expect(
    page.getByText("Missing model number", { exact: true }),
  ).toBeVisible();

});

test("CSV import preserves purchase history", async ({ page }) => {
  const seeded = await importPurchases(page, ["ZHX-PB22"]);
  await page.goto("/");
  await expect(page.getByTestId("purchase-row")).toHaveCount(1);
  await page.getByLabel("Upload purchases or receipt").setInputFiles({
    name: "purchase.csv", mimeType: "text/csv", buffer: Buffer.from(
      `order_id,purchased_at,merchant,product_name,brand,model_number\nUPLOAD-TEST,2024-06-12,${seeded.merchant},Portable Power Bank,NEWDERY,ZHX-PB23\n`),
  });
  await expect(page.getByTestId("purchase-row")).toHaveCount(2);
  await page.reload();
  await expect(page.getByTestId("purchase-row")).toHaveCount(2);
});

test("decision detail explains selected action and hard-gate evidence", async ({ page }) => {
  const seeded = await importPurchases(page);
  const started = await (await page.request.post(`${api}/api/runs`, {
    data: { purchase_ids: seeded.purchase_ids, mode: "live", allow_recorded_fallback: false, idempotency_key: crypto.randomUUID() },
  })).json();
  await page.goto(`/runs/${started.run_id}`);
  await expect(page.getByText("Run completed", { exact: true })).toBeVisible();
  const response = await page.request.get(`${api}/api/opportunities?run_id=${started.run_id}`);
  const items = await response.json();
  const excluded = items.find((item: { status: string }) => item.status === "rejected");
  expect(excluded).toBeTruthy();
  await page.goto(`/opportunities/${excluded.id}`);
  await expect(page.getByRole("heading", { name: "Investigation decision" })).toBeVisible();
  await expect(page.getByText("Next step: Exclude this product", { exact: true })).toBeVisible();
  await expect(page.getByText("Result: Not affected", { exact: true })).toBeVisible();
  await expect(page.getByText("Decision source: Official matching rules", { exact: true })).toBeVisible();
});

test("scan identifiers require explicit review before confirmation", async ({ page }) => {
  const facts = { product_name: "Power Bank", brand: "NEWDERY", model_number: null as string | null, merchant: "Synthetic test", date_purchased: "2024-06-12", order_reference_redacted: null, suggested_identifiers: { model_number: "ZHX-PB22" }, user_confirmed_identifiers: false };
  const product = { id: "scan-test", purchase_id: "scan-purchase", demo: false, source_type: "image", product: facts };
  await page.route("**/api/products", route => route.fulfill({ json: [product] }));
  await page.route("**/api/products/scan-test/confirm-identifiers", async route => {
    const body = route.request().postDataJSON();
    expect(body).toEqual({ confirmed: true, brand: "NEWDERY", model_number: "ZHX-PB22", upc: null });
    facts.model_number = body.model_number;
    facts.user_confirmed_identifiers = true;
    await route.fulfill({ json: product });
  });
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Confirm identifiers" })).toBeDisabled();
  await page.getByLabel("I checked these identifiers against my receipt or product.").check();
  await page.getByRole("button", { name: "Confirm identifiers" }).click();
  await expect(page.getByText("Identifiers confirmed by you", { exact: true })).toBeVisible();
  await expect(page.getByText(/Unverified scan:/)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Confirm identifiers" })).toHaveCount(0);
});
