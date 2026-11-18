import { test, expect, type APIRequestContext } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";

const api = process.env.API_URL || "http://localhost:8000";

async function source(mode = "unchanged") {
  if (!process.env.P1_BROWSER_CONTROL) throw new Error("Use isolated P1 browser harness; no live calls allowed");
  await writeFile(process.env.P1_BROWSER_CONTROL, JSON.stringify({ mode }));
}

async function imported(request: APIRequestContext, brand = "Flaunt", model = "E33A", variants = false) {
  await source();
  const products = variants ? [model, model + "X", ""] : [model];
  const csv = "order_id,purchased_at,merchant,product_name,brand,model_number,upc,serial_number\n" + products.map(m =>
    `${crypto.randomUUID()},2024-09-01,Synthetic shop,Magnetic power bank,${brand},${m},,${brand === "Baseus" ? "SN123D" : ""}`).join("\n");
  const upload = await request.post(`${api}/api/uploads/purchases`, { multipart: {
    file: { name: "p1-synthetic.csv", mimeType: "text/csv", buffer: Buffer.from(csv) },
  } });
  expect(upload.ok()).toBeTruthy();
  const started = await request.post(`${api}/api/runs`, { data: {
    purchase_ids: (await upload.json()).purchase_ids, mode: "live", idempotency_key: crypto.randomUUID(),
  } });
  const id = (await started.json()).run_id;
  await expect.poll(async () => (await (await request.get(`${api}/api/runs/${id}`)).json()).status).toBe("completed");
  return (await (await request.get(`${api}/api/opportunities?run_id=${id}`)).json()) as { id: string; status: string }[];
}

test("P1 additional notices preserve exact negative and missing cases", async ({ page }) => {
  for (const [brand, model] of [["Flaunt", "E33A"], ["iStore", "IST-09991/W05"]]) {
    const opportunities = await imported(page.request, brand, model, true);
    expect(opportunities.map(o => o.status).sort()).toEqual(["needs_review", "rejected", "verified_match"]);
    await page.goto(`/opportunities/${opportunities.find(o => o.status === "rejected")!.id}`);
    await expect(page.getByText("REJECTED — MODEL MISMATCH", { exact: true })).toBeVisible();
    await page.goto(`/opportunities/${opportunities.find(o => o.status === "verified_match")!.id}`);
    await expect(page.getByRole("heading", { name: "Source monitoring" })).toBeVisible();
    await page.getByRole("button", { name: "Prepare claim packet" }).click();
    await expect(page.getByRole("heading", { name: "Evidence readiness" })).toBeVisible();
    if (brand === "iStore") await expect(page.getByTestId("evidence-readiness")).not.toContainText("receipt");
  }
});

test("P1 readiness persists and requires renewed local approval", async ({ page }) => {
  const [opportunity] = await imported(page.request);
  await page.goto(`/opportunities/${opportunity.id}`);
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  const guidance = page.getByTestId("evidence-readiness");
  await expect(guidance.getByRole("heading", { name: "Preparation guidance" })).toBeVisible();
  await expect(guidance.getByRole("link", { name: "Official preparation requirements" })).toHaveAttribute("href", /^https:\/\/www.cpsc.gov\/Recalls\//);
  await expect(guidance).toContainText("Optional organizer tip");
  await expect(guidance.getByTestId("item-preparation").first()).toContainText("Required by reviewed notice");
  const evidence = process.env.DIWALI_EVIDENCE_DIR;
  if (evidence) await guidance.screenshot({ path: `${evidence}/preparation-desktop.png` });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(guidance).toBeVisible();
  expect(await guidance.evaluate(element => element.getBoundingClientRect().right <= innerWidth)).toBe(true);
  if (evidence) await guidance.screenshot({ path: `${evidence}/preparation-mobile.png` });
  const ready = page.getByTestId("evidence-readiness").getByRole("checkbox").first();
  await ready.check();
  await expect(page.getByTestId("readiness-saved")).toHaveText("Readiness saved locally");
  await page.reload();
  await expect(ready).toBeChecked();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const text = await readFile((await (await downloaded).path())!, "utf8");
  expect(text).toContain("Evidence readiness — self-reported, not verified");
  expect(text).toContain("[x] Ready locally:");
  expect(text).toContain("Preparation guidance");
  expect(text).toContain("No evidence files are collected or verified by this checklist");
  await ready.uncheck();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
  await expect(page.getByLabel("I reviewed this draft and understand approval stays local.")).not.toBeChecked();
});

test("P1 conditional photo guidance stays unknown and does not declare disposal", async ({ page }) => {
  const [opportunity] = await imported(page.request, "Baseus", "BS-30KP365");
  await page.goto(`/opportunities/${opportunity.id}`);
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  const guidance = page.getByTestId("evidence-readiness");
  const conditional = guidance.getByTestId("item-preparation").nth(1);
  await expect(conditional).toContainText("Requirement unknown");
  await expect(conditional).toContainText("order number");
  await expect(conditional.getByRole("checkbox")).not.toBeChecked();
  await expect(guidance).toContainText("does not attest disposal");
});

test("P1 rejected stale export offers reload and renewed approval", async ({ page }) => {
  const [opportunity] = await imported(page.request);
  await page.goto(`/opportunities/${opportunity.id}`);
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await expect(page.getByRole("heading", { name: "Evidence readiness" })).toBeVisible();
  const packet = page.url().split("/").at(-1)!;
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  let stale = true;
  let refresh = false;
  await page.route(`**/api/claim-packets/${packet}/export`, async route => {
    if (!stale) { await route.continue(); return; }
    stale = false; refresh = true;
    await route.fulfill({ status: 409, json: { code: "409", message: "Current preparation policy requires a new review" } });
  });
  await page.route(`**/api/claim-packets/${packet}`, async route => {
    const response = await route.fetch();
    const body = await response.json();
    if (refresh) { body.status = "ready_for_review"; body.approved_at = null; body.reviewed_at = null; refresh = false; }
    await route.fulfill({ response, json: body });
  });
  await page.getByRole("button", { name: "Export Markdown" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Export unavailable" })).toContainText("reload");
  await page.getByRole("button", { name: "Reload draft", exact: true }).click();
  const confirm = page.getByLabel("I reviewed this draft and understand approval stays local.");
  await expect(confirm).not.toBeChecked();
  await expect(page.getByRole("button", { name: "Approve draft locally" })).toBeDisabled();
  await confirm.check();
  await page.getByRole("button", { name: "Approve draft locally" }).click();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  expect(await readFile((await (await downloaded).path())!, "utf8")).toContain("Preparation guidance");
  // Export also refreshes the packet asynchronously. Drain interception before
  // closing its context so response.json() cannot race disposed responses.
  await page.unrouteAll({ behavior: "wait" });
});

test("P1 daily monitor records source change and blocks old export", async ({ page }) => {
  const [opportunity] = await imported(page.request);
  const packet = await (await page.request.post(`${api}/api/opportunities/${opportunity.id}/claim-packet`)).json();
  await page.request.post(`${api}/api/claim-packets/${packet.id}/approve-local`, { data: { confirmed: true } });
  await page.goto(`/opportunities/${opportunity.id}`);
  await page.getByRole("button", { name: "Enable daily source checks" }).click();
  await expect(page.getByTestId("monitor-result")).toHaveText("Last result: unchanged", { timeout: 12000 });
  await page.getByRole("button", { name: "Disable source checks" }).click();
  await source("changed");
  await page.getByRole("button", { name: "Enable daily source checks" }).click();
  await expect(page.getByTestId("monitor-result")).toHaveText("Last result: changed", { timeout: 12000 });
  await expect(page.getByText("Source changed — review required", { exact: true })).toBeVisible();
  await expect(page.getByText("Affected model unknown — review official notice", { exact: true })).toBeVisible();
  await expect(page.getByText("DC-EARBUDS-1 — SIMULATION", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Source update requires a new review", { exact: true })).toBeVisible();
  await expect(page.getByTestId("source-history")).toContainText("TEST100");
  expect((await page.request.post(`${api}/api/claim-packets/${packet.id}/export`)).status()).toBe(409);
  await page.getByRole("button", { name: "Disable source checks" }).click();
  if (process.env.DIWALI_EVIDENCE_DIR) {
    await page.screenshot({ path: `${process.env.DIWALI_EVIDENCE_DIR}/source-change.png`, fullPage: true });
  }
  await source("unavailable");
  await page.getByRole("button", { name: "Enable daily source checks" }).click();
  await expect(page.getByTestId("monitor-result")).toHaveText("Last result: unavailable", { timeout: 12000 });
  await expect(page.getByText("Current source unavailable — review required", { exact: true })).toBeVisible();
  expect((await page.request.post(`${api}/api/claim-packets/${packet.id}/export`)).status()).toBe(409);
  await page.getByRole("button", { name: "Disable source checks" }).click();
  if (process.env.DIWALI_EVIDENCE_DIR) {
    await page.screenshot({ path: `${process.env.DIWALI_EVIDENCE_DIR}/source-unavailable.png`, fullPage: true });
  }
});

test("P1 controls show empty and failure states without claiming a save", async ({ page }) => {
  const [opportunity] = await imported(page.request);
  await page.goto(`/opportunities/${opportunity.id}`);
  await expect(page.getByText("No source checks recorded yet.", { exact: true })).toBeVisible();
  await page.route("**/source-monitor", route => route.fulfill({ status: 503, json: { message: "Injected watch outage" } }));
  await page.reload();
  await expect(page.getByTestId("source-monitor").getByRole("alert")).toContainText("Injected watch outage");
  await page.getByRole("button", { name: "Prepare claim packet" }).click();
  await expect(page.getByTestId("evidence-readiness").getByRole("checkbox")).toHaveCount(2);
  await page.route("**/obligations", route => route.fulfill({ status: 503, json: { message: "Injected checklist outage" } }));
  await page.reload();
  await expect(page.getByTestId("evidence-readiness").getByRole("alert")).toContainText("Injected checklist outage");
  await expect(page.getByTestId("readiness-saved")).toHaveCount(0);
});
