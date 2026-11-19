import { test, expect } from "@playwright/test";
import { api, importPurchases } from "./purchases";
import { readFile } from "node:fs/promises";

// Removing the opt-in entry, dropping the challenge or enabling stale export breaks these flows.
test("live team board explains exact, excluded and missing-model cases with safe local export", async ({ page }) => {
  await importPurchases(page);
  await page.goto("/");
  const rows = page.getByTestId("purchase-row");
  await rows.filter({ hasText: "ZHX-PB23" }).getByRole("button", { name: "Investigate with agent team" }).click();
  await expect(page.getByRole("heading", { name: "Agent team case" })).toBeVisible();
  await expect(page.getByTestId("case-status")).toHaveText("Not affected");
  await expect(page.getByTestId("challenge")).toContainText("ZHX-PB23");
  await expect(page.getByTestId("challenge")).toContainText("ZHX-PB22");
  await expect(page.getByText("Live investigation · inspect sources and role outcomes", { exact: true })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: "../../.impeccable/review/case.png", fullPage: true, animations: "disabled" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "../../.impeccable/review/case-mobile.png", fullPage: true, animations: "disabled" });
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(page.getByRole("button", { name: "Prepare claim packet" })).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId("case-status")).toHaveText("Not affected");
  await page.goto("/");
  await page.getByTestId("purchase-row").filter({ hasText: "Missing model number" })
    .getByRole("button", { name: "Investigate with agent team" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("Needs information");
  await expect(page.getByLabel("model number", { exact: true })).toHaveValue("");
  await page.getByLabel("model number", { exact: true }).fill("ZHX-PB22");
  await expect(page.getByRole("button", { name: "Send answer" })).toBeDisabled();
  await page.getByLabel("I checked this answer against my product or record.").check();
  await page.getByRole("button", { name: "Send answer" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("Ready for review");
  await expect(page.getByRole("heading", { name: "Finding" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Challenge" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await expect(page.getByTestId("role-result")).toHaveCount(3);
  const tools = page.getByRole("region", { name: "Tools recorded for this case" });
  await expect(tools).toContainText(/Agent37.*Scout/);
  await expect(tools).toContainText(/Lyzr.*Skeptic/);
  await expect(tools).toContainText(/Lyzr.*Builder/);
  await expect(tools).toContainText(/BAND.*handoffs/);
  await expect(tools).not.toContainText(/Finch|AdaL/);
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const download = await downloadPromise;
  const path = await download.path();
  const content = await readFile(path!, "utf8");
  expect(content).not.toContain("OFFLINE REPLAY");
  expect(content).toContain("not an external submission");
  expect(content).toMatch(/https:\/\/(www\.)?cpsc\.gov\/Recalls\//);
});

test("a newer case run blocks export from an already open approved draft", async ({ page }) => {
  const seeded = await importPurchases(page, ["ZHX-PB22"]);
  const started = await (await page.request.post(`${api}/api/collaborations`, {
    data: { product_ids: [seeded.product_ids[0]], mode: "live", idempotency_key: crypto.randomUUID() },
  })).json();
  await page.goto(`/collaborations/${started.id}`);
  await expect(page.getByTestId("case-status")).toHaveText("Ready for review");
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeEnabled();
  const newer = await page.request.post(`${api}/api/collaborations`, {
    data: { case_id: started.case_id, product_ids: [seeded.product_ids[0]], mode: "live", idempotency_key: crypto.randomUUID() },
  });
  expect(newer.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Export Markdown" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Current case requires new review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toHaveCount(0);
  await page.goto(`/collaborations/${(await newer.json()).id}`);
  await expect(page.getByTestId("case-status")).toHaveText("Ready for review");
  await page.getByRole("button", { name: "Review current sources" }).click();
  await expect(page).not.toHaveURL(`/collaborations/${started.id}`);
  await expect(page.getByTestId("case-status")).toHaveText("Ready for review");
});
