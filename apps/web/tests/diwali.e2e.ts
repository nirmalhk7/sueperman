import { test, expect } from "@playwright/test";

test("Recovered investigation shows recovery and uncertain-outcome guidance", async ({ page }, testInfo) => {
  await page.route("**/api/**", async route => {
    const url = new URL(route.request().url());
    const body = url.pathname === "/api/runs/recovery-case" ? {
      run_id: "recovery-case", status: "partial", summary: {}, provider_modes: {},
      warnings: ["Execution interrupted; external outcome may be unknown. Start a new run."],
      opportunities: [], job: { state: "interrupted", attempts: 1, recoveries: 1 },
    } : [];
    await route.fulfill({ json: body });
  });
  await page.goto("/runs/recovery-case");
  await expect(page.getByRole("heading", { name: "Check finished with limited results", exact: true })).toBeVisible();
  await expect(page.getByText("Queued work recovered after restart.", { exact: true })).toBeVisible();
  await expect(page.getByText("Execution interrupted; external outcome may be unknown. Start a new run.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /approve|export/i })).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("interrupted-recovery.png"), fullPage: true });
});
const api = process.env.API_URL || "http://localhost:8000";

// Internal recordings remain inspectable through API, never through public UI.
test("Diwali packet workflow", async ({ page }) => {
  const seeded = await (await page.request.post(`${api}/api/demo/reset`)).json();
  const started = await (await page.request.post(`${api}/api/runs`, { data: {
    purchase_ids: seeded.purchase_ids, mode: "demo", collaboration_mode: "local", idempotency_key: crypto.randomUUID(),
  } })).json();
  await expect.poll(async () => (await (await page.request.get(`${api}/api/runs/${started.run_id}`)).json()).status).toBe("completed");
  const items = await (await page.request.get(`${api}/api/opportunities?run_id=${started.run_id}`)).json();
  expect(items.some((item: {status:string}) => item.status === "verified_match")).toBeTruthy();
  await page.goto(`/runs/${started.run_id}`);
  await expect(page.getByRole("heading", { name: "Investigation unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: /approve|export|recorded/i })).toHaveCount(0);
});

// Live partial runs preserve useful activity/error states without a fallback action.
test("Diwali error and empty states", async ({ page }) => {
  await page.route("**/api/runs/live-errors", route => route.fulfill({ json: {
    run_id: "live-errors", mode: "live", demo: false, status: "partial", summary: {}, provider_modes: {},
    collaboration_mode: "band", actual_transport: "band", source_mode: "live", warnings: [], opportunities: [],
  } }));
  await page.route("**/api/runs/live-errors/events", route => route.fulfill({ json: [] }));
  await page.route("**/api/opportunities?run_id=live-errors", route => route.fulfill({ json: [] }));
  await page.route("**/agent-messages*", route => route.fulfill({ json: { items: [], next_seq: 0 } }));
  await page.goto("/runs/live-errors");
  await expect(page.getByTestId("agent-timeline")).toContainText("No accepted actor messages yet.");
  await page.unroute("**/agent-messages*");
  await page.route("**/agent-messages*", route => route.fulfill({ status: 503, json: { message: "Timeline unavailable" } }));
  await page.reload();
  await expect(page.getByRole("alert").filter({ hasText: "Timeline unavailable" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Check finished with limited results" })).toBeVisible();
  await expect(page.getByRole("button", { name: /recorded|replay|fallback/i })).toHaveCount(0);
});
