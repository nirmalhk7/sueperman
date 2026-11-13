/** Explicit paid acceptance only: one new synthetic photo, then a free cached duplicate. */
import { chromium, expect } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const base = process.env.RECEIPT_LIVE_URL;
if (!base) throw new Error("Set RECEIPT_LIVE_URL explicitly; this check can consume one OCR attempt.");
const output = "../../output/playwright/receipt-camera-public";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chromium" });
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
try {
  const healthResponse = await page.request.get(base + "/api/health");
  expect(healthResponse.ok()).toBeTruthy();
  const health = await healthResponse.json();
  expect(health.providers.find(p => p.name === "openai_receipts")).toMatchObject({ enabled: true, configured: true });
  for (const name of ["openai", "gemini", "brightdata"]) {
    expect(health.providers.find(p => p.name === name).enabled).toBe(false);
  }
  await page.goto(base);
  await expect(page.getByText(/SHARED DEMO · Use synthetic purchases/)).toBeVisible();
  const camera = page.getByLabel("Take receipt photo", { exact: true });
  await expect(camera).toHaveAttribute("capture", "environment");
  const first = page.waitForResponse(r => r.url().endsWith("/api/uploads/purchases") && r.request().method() === "POST", { timeout: 45000 });
  await camera.setInputFiles(path.resolve("../../demo/receipt-synthetic.jpg"));
  const response = await first;
  expect(response.status()).toBe(200);
  const imported = await response.json();
  const row = page.locator(`[data-product-id="${imported.product_ids[0]}"]`);
  await expect(row).toContainText("Demo Store");
  await expect(row).toContainText(/power bank/i);
  await expect(row.getByRole("button", { name: "Confirm identifiers" })).toBeDisabled();
  const repeat = page.waitForResponse(r => r.url().endsWith("/api/uploads/purchases") && r.request().method() === "POST");
  await camera.setInputFiles(path.resolve("../../demo/receipt-synthetic.jpg"));
  const reused = await (await repeat).json();
  expect(reused.purchase_ids).toEqual(imported.purchase_ids);
  expect(reused.parse_warnings.join(" ")).toContain("no additional model request");
  await page.screenshot({ path: `${output}/photo-read-review.png`, fullPage: true });
  const products = await (await page.request.get(base + "/api/products")).json();
  const extracted = products.find(p => p.id === imported.product_ids[0]);
  expect(extracted.product.user_confirmed_identifiers).toBe(false);
  const proof = { observed_at: new Date().toISOString(), url: base, provider: "openai", model: "gpt-6-luna",
    input: "clearly labeled synthetic receipt JPEG", health, mobile_camera_preference: "environment",
    live_photo_upload_status: response.status(), upload: imported, product: extracted,
    duplicate_reused_without_model_request: true, unconfirmed_identifiers: true };
  await writeFile("../../docs/evidence/receipt-camera-public.json", JSON.stringify(proof, null, 2) + "\n");
  console.log("PASS: public mobile camera input, live OpenAI photo reading, merchant/items review, identifier gate and free duplicate reuse");
} finally { await browser.close(); }
