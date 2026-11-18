import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";

test("restored demo export persists via API while public UI shows imported purchases", async ({ page }, testInfo) => {
  const packet = process.env.STORAGE_RESTORE_PACKET_ID;
  const expected = process.env.STORAGE_EXPORT_SHA256;
  expect(packet, "storage acceptance must provide the restored packet").toBeTruthy();
  expect(expected, "storage acceptance must bind the original export").toBeTruthy();
  const exported = await page.request.post(`/api/claim-packets/${packet}/export`);
  expect(exported.ok()).toBeTruthy();
  expect(createHash("sha256").update(await exported.body()).digest("hex")).toBe(expected);

  // The retained synthetic API draft does not become a live public result.
  await page.goto(`/claims/${packet}`);
  await expect(page.getByRole("heading", { name: "Investigation unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Approve draft locally" })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("restored-demo-unavailable.png"), fullPage: true });

  await page.goto("/");
  const purchases = page.getByTestId("purchase-row");
  await expect(purchases).toHaveCount(1);
  await expect(purchases).toContainText("Bottle");
  await expect(purchases).toContainText("DC-BOTTLE-1");
  await expect(page.getByRole("button", { name: "Use synthetic purchases" })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("restored-imported-purchase.png"), fullPage: true });
});
