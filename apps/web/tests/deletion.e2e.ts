import { test, expect } from "@playwright/test";

const api = process.env.API_URL || "http://localhost:8000";
for (const width of [1280, 390]) {
  test(`Delete purchase and explicitly re-import at ${width}px`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 900 });
    const csv = Buffer.from("order_id,purchased_at,merchant,product_name,brand,model_number\n" +
      `DELETE-${width},2024-06-12,Synthetic shop,Deletion test ${width},NEWDERY,ZHX-PB22\n`);
    const response = await request.post(`${api}/api/uploads/purchases`, {
      multipart: { file: { name: "deletion.csv", mimeType: "text/csv", buffer: csv } },
    });
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
    const row = page.getByTestId("purchase-row").filter({ hasText: `Deletion test ${width}` });
    await row.getByRole("button", { name: "Delete purchase", exact: true }).click();
    const review = row.getByRole("group", { name: "Review purchase deletion" });
    await expect(review.getByRole("button", { name: "Delete permanently" })).toBeDisabled();
    await row.screenshot({ path: `${process.env.DIWALI_EVIDENCE_DIR || "test-results"}/deletion-preview-${width}.png` });
    await review.getByLabel("I understand this permanently deletes this purchase and its local records").check();
    await review.getByRole("button", { name: "Delete permanently" }).click();
    await expect(row).toHaveCount(0);
    await page.getByLabel("Upload purchases or receipt").setInputFiles({ name: "deletion.csv", mimeType: "text/csv", buffer: csv });
    await expect(page.getByRole("group", { name: "Confirm fresh import" })).toBeVisible();
    await expect(page.getByText("Purchase and associated local records deleted.", { exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Import again", exact: true })).toBeDisabled();
    await page.getByLabel("I want to import this previously deleted file again").check();
    await page.getByRole("button", { name: "Import again", exact: true }).click();
    await expect(row).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.screenshot({ path: `${process.env.DIWALI_EVIDENCE_DIR || "test-results"}/deletion-${width}.png`, fullPage: true });
  });
}

test("Shared history needs separate consent and preserves other purchases", async ({ page, request }) => {
  const imported = [];
  for (const name of ["Remove shared", "Keep shared"]) {
    const csv = Buffer.from("order_id,purchased_at,merchant,product_name,brand,model_number\n" +
      `${name},2024-06-12,Shop,${name},NEWDERY,ZHX-PB22\n`);
    const response = await request.post(`${api}/api/uploads/purchases`, {
      multipart: { file: { name: "shared.csv", mimeType: "text/csv", buffer: csv } },
    });
    expect(response.ok()).toBeTruthy();
    imported.push(await response.json());
  }
  const run = await request.post(`${api}/api/runs`, { data: { mode: "demo",
    purchase_ids: imported.flatMap(item => item.purchase_ids), idempotency_key: "deletion-shared-browser" } });
  expect(run.ok()).toBeTruthy();
  await page.goto("/");
  const target = page.getByTestId("purchase-row").filter({ hasText: "Remove shared" });
  await target.getByRole("button", { name: "Delete purchase", exact: true }).click();
  await target.getByLabel("I understand this permanently deletes this purchase and its local records").check();
  await expect(target.getByRole("button", { name: "Delete permanently" })).toBeDisabled();
  await expect(target.getByText("1 shared investigation histories will also be removed.", { exact: false })).toBeVisible();
  await target.getByLabel("I also agree to remove these shared investigation histories").check();
  await target.getByRole("button", { name: "Delete permanently" }).click();
  await expect(target).toHaveCount(0);
  await expect(page.getByTestId("purchase-row").filter({ hasText: "Keep shared" })).toHaveCount(1);
});
