import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

// Removing the opt-in entry, dropping the challenge or enabling stale export breaks these flows.
test("offline team board explains exact, excluded and missing-model cases with safe local export", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Try demo data" }).click();
  const rows = page.getByTestId("purchase-row");
  await rows.filter({ hasText: "ZHX-PB23" }).getByRole("button", { name: "Investigate with agent team" }).click();
  await expect(page.getByRole("heading", { name: "Agent team case" })).toBeVisible();
  await expect(page.getByTestId("case-status")).toHaveText("rejected");
  await expect(page.getByTestId("challenge")).toContainText("ZHX-PB23");
  await expect(page.getByTestId("challenge")).toContainText("ZHX-PB22");
  await expect(page.getByText("OFFLINE REPLAY — no live sponsor execution", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Prepare claim packet" })).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId("case-status")).toHaveText("rejected");
  await page.goto("/");
  await page.getByTestId("purchase-row").filter({ hasText: "Missing model number" })
    .getByRole("button", { name: "Investigate with agent team" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("needs_information");
  await expect(page.getByLabel("model number", { exact: true })).toHaveValue("");
  await page.getByLabel("model number", { exact: true }).fill("ZHX-PB22");
  await expect(page.getByRole("button", { name: "Send answer" })).toBeDisabled();
  await page.getByLabel("I checked this answer against my product or record.").check();
  await page.getByRole("button", { name: "Send answer" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("ready_for_review");
  await expect(page.getByRole("heading", { name: "Finding" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Challenge" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await expect(page.getByTestId("role-result")).toHaveCount(3);
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const download = await downloadPromise;
  const path = await download.path();
  const content = await readFile(path!, "utf8");
  expect(content).toContain("OFFLINE REPLAY");
  expect(content).toContain("not an external submission");
  expect(content).toContain("https://www.cpsc.gov/Recalls/");
});

test("a newer case run blocks export from an already open approved draft", async ({ page }) => {
  const seeded = await (await page.request.post("http://localhost:8000/api/demo/reset")).json();
  const started = await (await page.request.post("http://localhost:8000/api/collaborations", {
    data: { product_ids: [seeded.product_ids[0]], mode: "replay", idempotency_key: crypto.randomUUID() },
  })).json();
  await page.goto(`/collaborations/${started.id}`);
  await expect(page.getByTestId("case-status")).toHaveText("ready_for_review");
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeEnabled();
  const newer = await page.request.post("http://localhost:8000/api/collaborations", {
    data: { case_id: started.case_id, product_ids: [seeded.product_ids[0]], mode: "replay", idempotency_key: crypto.randomUUID() },
  });
  expect(newer.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Export Markdown" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Current case requires new review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toHaveCount(0);
  await page.goto(`/collaborations/${(await newer.json()).id}`);
  await expect(page.getByTestId("case-status")).toHaveText("ready_for_review");
  await page.getByRole("button", { name: "Review current sources" }).click();
  await expect(page).not.toHaveURL(`/collaborations/${started.id}`);
  await expect(page.getByTestId("case-status")).toHaveText("ready_for_review");
});
