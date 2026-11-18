import { test, expect } from "@playwright/test";
import path from "node:path";

test.use({ viewport: { width: 390, height: 844 }, isMobile: true });

const product = {
  id: "camera-product", purchase_id: "camera-purchase", demo: false, source_type: "image",
  product: { product_name: "Power Bank", brand: "NEWDERY", merchant: "Demo Store",
    date_purchased: "2024-06-12", model_number: null, upc: null,
    suggested_identifiers: { model_number: "ZHX-PB22" }, user_confirmed_identifiers: false },
};

async function health(page: import("@playwright/test").Page) {
  await page.route("**/api/health", route => route.fulfill({ json: {
    db: "ok", demo_ready: true,
    providers: [{ name: "openai_receipts", enabled: true, configured: true, healthy: null }],
  } }));
}

test("camera photo is read into reviewable purchases without confirming identifiers", async ({ page }) => {
  let uploaded = false;
  let release = () => {};
  const pending = new Promise<void>(resolve => { release = resolve; });
  await health(page);
  await page.route("**/api/products", route => route.fulfill({ json: uploaded ? [product] : [] }));
  await page.route("**/api/uploads/purchases", async route => {
    expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
    expect(route.request().postDataBuffer()?.toString("latin1")).toContain("image/jpeg");
    await pending;
    uploaded = true;
    await route.fulfill({ json: { product_ids: [product.id], purchase_ids: [product.purchase_id], parse_warnings: [] } });
  });
  await page.goto("/");
  const camera = page.getByLabel("Take receipt photo", { exact: true });
  await expect(camera).toHaveAttribute("capture", "environment");
  await expect(camera).toHaveAttribute("accept", "image/jpeg,image/png");
  try {
    await camera.setInputFiles(process.env.RECEIPT_FIXTURE_PATH || path.resolve("../../demo/receipt-synthetic.jpg"));
    await expect(page.getByRole("status").filter({ hasText: "Reading receipt" })).toBeVisible();
    await expect(camera).toBeDisabled();
  } finally { release(); }
  const row = page.getByTestId("purchase-row");
  await expect(row).toContainText("Demo Store");
  await expect(row).toContainText("Unverified scan: ZHX-PB22");
  await expect(row.getByRole("button", { name: "Confirm identifiers" })).toBeDisabled();
});

test("camera upload failure permits another photo without starting a purchase check", async ({ page }) => {
  await health(page);
  await page.route("**/api/products", route => route.fulfill({ json: [] }));
  await page.route("**/api/uploads/purchases", route => route.fulfill({ status: 429,
    json: { message: "Daily receipt-photo limit reached; try tomorrow or upload CSV" } }));
  await page.goto("/");
  const camera = page.getByLabel("Take receipt photo", { exact: true });
  await camera.setInputFiles(process.env.RECEIPT_FIXTURE_PATH || path.resolve("../../demo/receipt-synthetic.jpg"));
  await expect(page.getByRole("alert").filter({ hasText: "Daily receipt-photo limit reached" })).toBeVisible();
  await expect(camera).toBeEnabled();
  await expect(camera).toHaveValue("");
  await expect(page.getByRole("button", { name: "Check my purchases" })).toBeDisabled();
});
