import { expect, test } from "@playwright/test";
import { importPurchases } from "./purchases";

test("missing-model result lets the user correct that purchase in place", async ({ page }) => {
  await importPurchases(page, [""]);
  await page.goto("/");
  await page.getByRole("button", { name: "Check my purchases" }).click();
  await page.getByRole("link", { name: "Review details" }).click();
  await page.getByRole("button", { name: "Correct model number" }).click();
  await page.getByLabel("Model number", { exact: true }).fill("ZHX-PB22");
  await expect(page.getByRole("button", { name: "Save correction" })).toBeDisabled();
  await page.getByLabel("I checked these identifiers against my receipt or product.").check();
  await page.getByRole("button", { name: "Save correction" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Purchase corrected" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Correct model number" })).toHaveCount(0);
});

test("unavailable tools are disclosed before an attempt", async ({ page }) => {
  await importPurchases(page, ["ZHX-PB22"]);
  await page.route("**/api/health", route => route.fulfill({ json: {
    db: "ok",
    providers: [
      { name: "agent_team", enabled: true, configured: false },
      { name: "openai_receipts", enabled: true, configured: false },
    ],
  } }));
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Investigate with agent team" })).toBeDisabled();
  await expect(page.getByText(/Agent team unavailable/)).toBeVisible();
  await expect(page.getByLabel("Take receipt photo", { exact: true })).toBeDisabled();
  await expect(page.getByText(/Photo reading unavailable/)).toBeVisible();
});

test("initial loading gets a status and navigation has empty destinations", async ({ page }) => {
  let loaded!: () => void;
  const pending = new Promise<void>(resolve => { loaded = resolve; });
  await page.route("**/api/products", async route => {
    await pending;
    await route.fulfill({ json: [] });
  });
  try {
    await page.goto("/");
    await expect(page.getByRole("status").filter({ hasText: "Loading purchases" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /0 items/ })).toHaveCount(0);
  } finally {
    loaded();
  }
  await page.getByRole("link", { name: "Opportunities" }).click();
  await expect(page.locator("#opportunities")).toContainText(/Run a check/);
  await page.getByRole("link", { name: "Activity" }).click();
  await expect(page.locator("#activity")).toContainText(/No activity yet/);
});

test("reusing a receipt announces the reuse without another purchase", async ({ page }) => {
  await importPurchases(page, ["ZHX-PB22"]);
  await page.route("**/api/uploads/purchases", route => route.fulfill({ json: {
    product_ids: [], purchase_ids: [],
    parse_warnings: ["Existing receipt import reused; no additional model request."],
  } }));
  await page.goto("/");
  await expect(page.getByTestId("purchase-row")).toHaveCount(1);
  await page.getByLabel("Upload purchases or receipt").setInputFiles({
    name: "receipt.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-"),
  });
  await expect(page.getByRole("status").filter({ hasText: /used your existing receipt/i })).toBeVisible();
  await expect(page.getByTestId("purchase-row")).toHaveCount(1);
});

test("case reads as a decision with evidence history and a structured draft", async ({ page }) => {
  await importPurchases(page, ["ZHX-PB22"]);
  await page.goto("/");
  await page.getByRole("button", { name: "Investigate with agent team" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("Ready for review");
  await page.getByText("Inspect revision and evidence history", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Case revisions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence snapshots" })).toBeVisible();
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  const draft = page.getByRole("article", { name: "Remedy draft" });
  await expect(draft.getByRole("heading", { name: "Verified product facts" })).toBeVisible();
  await expect(draft.locator("dd").filter({ hasText: "ZHX-PB22" })).toHaveCount(1);
  await expect(draft).not.toContainText(/\{'product_name'/);
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
});
