# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: receipt-camera.e2e.ts >> camera upload failure permits another photo without starting a purchase check
- Location: tests/receipt-camera.e2e.ts:48:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.setInputFiles: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByLabel('Take receipt photo', { exact: true })

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - link "Skip to content" [ref=e2] [cursor=pointer]:
    - /url: "#main"
  - banner [ref=e3]:
    - link "Sueperman" [ref=e4] [cursor=pointer]:
      - /url: /
    - navigation "Primary" [ref=e5]:
      - link "My purchases" [ref=e6] [cursor=pointer]:
        - /url: /#purchases
      - link "Opportunities" [ref=e7] [cursor=pointer]:
        - /url: /#opportunities
      - link "Activity" [ref=e8] [cursor=pointer]:
        - /url: /#activity
    - generic [ref=e9]: LOCAL / EVIDENCE FIRST
  - generic [ref=e10]: REPLAY AVAILABLE · Demo purchases are synthetic. Source timestamps and provider modes shown on every result.
  - main [ref=e11]:
    - generic [ref=e13]:
      - text: Your purchases. Your rights.
      - heading "Find recalls and settlements hiding in your purchase history." [level=1] [ref=e14]
      - paragraph [ref=e15]: Turn forgotten orders into evidence-backed next steps. Check official recalls, understand what applies, and review a remedy draft before taking action.
      - generic [ref=e16]:
        - button "Check my purchases" [disabled] [ref=e17]
        - button "Try demo data" [ref=e18] [cursor=pointer]
    - generic [ref=e19]:
      - generic [ref=e20]:
        - heading "My purchases / 0 items" [level=2] [ref=e21]:
          - text: My purchases
          - generic [ref=e22]: / 0 items
        - generic [ref=e23]: CSV · Up to 10MB · No account needed
      - generic [ref=e24]:
        - generic [ref=e25]:
          - strong [ref=e26]: Drop your purchase history here
          - generic [ref=e27]: — or choose a CSV or receipt. Uncertain identifiers stay uncertain.
        - button "Upload purchases or receipt" [ref=e28]
    - group [ref=e29]:
      - generic "Demo controls & provider health" [ref=e30] [cursor=pointer]
      - option "Offline replay" [selected]
      - option "Live APIs with labeled fallback"
  - contentinfo [ref=e31]:
    - strong [ref=e32]: Sueperman — Your consumer-rights agent
    - paragraph [ref=e33]: Sueperman helps organize public information and user-provided evidence; verify official terms and submit claims yourself.
    - text: Local approval never sends a request. No legal advice or guaranteed remedy.
  - button "Open Next.js Dev Tools" [ref=e39] [cursor=pointer]
  - alert [ref=e43]
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import path from "node:path";
  3  | 
  4  | test.use({ viewport: { width: 390, height: 844 }, isMobile: true });
  5  | 
  6  | const product = {
  7  |   id: "camera-product", purchase_id: "camera-purchase", demo: false, source_type: "image",
  8  |   product: { product_name: "Power Bank", brand: "NEWDERY", merchant: "Demo Store",
  9  |     date_purchased: "2024-06-12", model_number: null, upc: null,
  10 |     suggested_identifiers: { model_number: "ZHX-PB22" }, user_confirmed_identifiers: false },
  11 | };
  12 | 
  13 | async function health(page: import("@playwright/test").Page) {
  14 |   await page.route("**/api/health", route => route.fulfill({ json: {
  15 |     db: "ok", demo_ready: true,
  16 |     providers: [{ name: "openai_receipts", enabled: true, configured: true, healthy: null }],
  17 |   } }));
  18 | }
  19 | 
  20 | test("camera photo is read into reviewable purchases without confirming identifiers", async ({ page }) => {
  21 |   let uploaded = false;
  22 |   let release = () => {};
  23 |   const pending = new Promise<void>(resolve => { release = resolve; });
  24 |   await health(page);
  25 |   await page.route("**/api/products", route => route.fulfill({ json: uploaded ? [product] : [] }));
  26 |   await page.route("**/api/uploads/purchases", async route => {
  27 |     expect(route.request().headers()["content-type"]).toContain("multipart/form-data");
  28 |     expect(route.request().postDataBuffer()?.toString("latin1")).toContain("image/jpeg");
  29 |     await pending;
  30 |     uploaded = true;
  31 |     await route.fulfill({ json: { product_ids: [product.id], purchase_ids: [product.purchase_id], parse_warnings: [] } });
  32 |   });
  33 |   await page.goto("/");
  34 |   const camera = page.getByLabel("Take receipt photo", { exact: true });
  35 |   await expect(camera).toHaveAttribute("capture", "environment");
  36 |   await expect(camera).toHaveAttribute("accept", "image/jpeg,image/png");
  37 |   try {
  38 |     await camera.setInputFiles(path.resolve("../../demo/receipt-synthetic.jpg"));
  39 |     await expect(page.getByRole("status")).toContainText("Reading receipt");
  40 |     await expect(camera).toBeDisabled();
  41 |   } finally { release(); }
  42 |   const row = page.getByTestId("purchase-row");
  43 |   await expect(row).toContainText("Demo Store");
  44 |   await expect(row).toContainText("Unverified scan: ZHX-PB22");
  45 |   await expect(row.getByRole("button", { name: "Confirm identifiers" })).toBeDisabled();
  46 | });
  47 | 
  48 | test("camera upload failure permits another photo without starting a purchase check", async ({ page }) => {
  49 |   await health(page);
  50 |   await page.route("**/api/products", route => route.fulfill({ json: [] }));
  51 |   await page.route("**/api/uploads/purchases", route => route.fulfill({ status: 429,
  52 |     json: { message: "Daily receipt-photo limit reached; try tomorrow or upload CSV" } }));
  53 |   await page.goto("/");
  54 |   const camera = page.getByLabel("Take receipt photo", { exact: true });
> 55 |   await camera.setInputFiles(path.resolve("../../demo/receipt-synthetic.jpg"));
     |   ^ Error: locator.setInputFiles: Test timeout of 30000ms exceeded.
  56 |   await expect(page.getByRole("alert")).toContainText("Daily receipt-photo limit reached");
  57 |   await expect(camera).toBeEnabled();
  58 |   await expect(camera).toHaveValue("");
  59 |   await expect(page.getByRole("button", { name: "Check my purchases" })).toBeDisabled();
  60 | });
  61 | 
```