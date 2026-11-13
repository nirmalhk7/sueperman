import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("five purchases produce evidence-backed recall, safe export and visible negative cases", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Find recalls and settlements hiding in your purchase history.",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try demo data" }).click();
  await expect(page.getByTestId("purchase-row")).toHaveCount(5);
  await page.getByRole("button", { name: "Check my purchases" }).click();
  await expect(page.getByText("Run completed", { exact: true })).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByTestId("opportunity-card")).toHaveCount(4);
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
  ).toHaveAttribute("href", /https:\/\/www.cpsc.gov\/Recalls\//);
  await expect(
    page.getByText("ZHX-PB22", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText(/OFFLINE REPLAY of a real published recall/).first(),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("evidence.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
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
  expect(content).toContain("https://www.cpsc.gov/Recalls/");
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
  await expect(
    page.getByText("Missing model number", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await page
    .getByTestId("opportunity-card")
    .filter({ hasText: "Simulated settlement" })
    .getByRole("link", { name: "Review details" })
    .click();
  await expect(
    page
      .getByText("SIMULATED CASE — NO REAL CLAIM AVAILABLE", { exact: true })
      .first(),
  ).toBeVisible();
  await expect(page.getByText("Claim submitted", { exact: true })).toHaveCount(
    0,
  );
});

test("demo selection stays five purchases after CSV import without deleting imported history", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Upload purchases or receipt").setInputFiles({
    name: "purchase.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "order_id,purchased_at,merchant,product_name,brand,model_number\nUPLOAD-TEST,2024-06-12,Fixture Upload,Portable Power Bank,NEWDERY,ZHX-PB22\n",
    ),
  });
  await expect(
    page.getByTestId("purchase-row").filter({ hasText: "Fixture Upload" }),
  ).toHaveCount(1);
  await page.getByRole("button", { name: "Try demo data" }).click();
  await expect(page.getByTestId("purchase-row")).toHaveCount(5);
});
