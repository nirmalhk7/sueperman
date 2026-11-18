import { expect, type Page } from "@playwright/test";
export const api = process.env.API_URL || "http://localhost:8000";

// Import real-shaped records into the disposable API, keeping each browser
// isolated by merchant without deleting other tests' purchase history.
export async function importPurchases(page: Page, models = ["ZHX-PB22", "ZHX-PB23", ""]) {
  const merchant = `Purchase ${crypto.randomUUID()}`;
  const uploaded = await page.request.post(`${api}/api/uploads/purchases`, { multipart: {
    file: { name: "purchases.csv", mimeType: "text/csv", buffer: Buffer.from(
      "order_id,purchased_at,merchant,product_name,brand,model_number\n" + models.map(model =>
        `${crypto.randomUUID()},2024-06-12,${merchant},Portable Power Bank,NEWDERY,${model}`).join("\n")) },
  } });
  expect(uploaded.ok()).toBeTruthy();
  await page.route("**/api/products", async route => {
    const response = await route.fetch();
    const products = await response.json();
    await route.fulfill({ json: products.filter((p: {product:{merchant:string}}) => p.product.merchant === merchant) });
  });
  return { ...(await uploaded.json()), merchant } as { product_ids: string[]; purchase_ids: string[]; merchant: string };
}
