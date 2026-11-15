import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

const api = process.env.API_URL || "http://localhost:8000";

test("Diwali packet workflow", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Try demo data" }).click();
  await expect(page.getByRole("heading", { name: /My purchases.*5 items/ })).toBeVisible();
  await page.getByTestId("diwali-mode").selectOption("local");
  await page.getByRole("button", { name: "Check my purchases" }).click();
  await expect(page.getByRole("heading", { name: "Run completed" })).toBeVisible();
  await expect(page.getByTestId("transport-mode")).toHaveText("LOCAL TEST");
  await expect(page.getByTestId("source-mode")).toHaveText("SOURCE RECORDED");
  await expect(page.getByTestId("agent-timeline").getByRole("listitem")).toHaveCount(18);
  await expect(page.getByTestId("model-comparison").filter({ hasText: "ZHX-PB23" })).toContainText("ZHX-PB22");
  await expect(page.getByTestId("challenge-reason")).toContainText("MODEL_MISMATCH");
  if (process.env.DIWALI_EVIDENCE_DIR) {
    await page.screenshot({ path: `${process.env.DIWALI_EVIDENCE_DIR}/local-run.png`, fullPage: true });
  }
  const exact = page.getByTestId("opportunity-card").filter({ hasText: "Your model: ZHX-PB22" });
  await exact.getByRole("link", { name: "Review details" }).click();
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const download = await downloadPromise;
  const text = await readFile((await download.path())!, "utf8");
  expect(text).toContain("ZHX-PB22");
  expect(text).toContain("not an external submission");
  expect(text).toContain("https://www.cpsc.gov/Recalls/");
});

test("Diwali error and empty states", async ({ page }) => {
  const seeded = await (await page.request.post(`${api}/api/demo/reset`)).json();
  const started = await (await page.request.post(`${api}/api/runs`, { data: {
    purchase_ids: seeded.purchase_ids, collaboration_mode: "local", idempotency_key: crypto.randomUUID(),
  } })).json();
  await page.route("**/agent-messages*", route => route.fulfill({ json: { items: [], next_seq: 0 } }));
  await page.goto(`/runs/${started.run_id}`);
  await expect(page.getByTestId("agent-timeline")).toContainText("No accepted actor messages yet.");
  await page.unroute("**/agent-messages*");
  await page.route("**/agent-messages*", route => route.fulfill({ status: 503, json: { message: "Timeline unavailable" } }));
  await page.reload();
  await expect(page.getByRole("alert").filter({ hasText: "Timeline unavailable" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Run completed" })).toBeVisible();
  // Controlled UI fault state; the separate API test injects an actual coordinator failure.
  await page.route(`**/api/runs/${started.run_id}`, async route => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...(await response.json()), status: "failed" } });
  });
  await page.reload();
  const fallback = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/runs"));
  await page.getByRole("button", { name: "Run recorded-source workflow separately" }).click();
  const next = await (await fallback).json();
  expect(next.run_id).not.toBe(started.run_id);
  expect(next.fallback_of).toBe(started.run_id);
  await expect(page.getByRole("heading", { name: "Run completed" })).toBeVisible();
});
