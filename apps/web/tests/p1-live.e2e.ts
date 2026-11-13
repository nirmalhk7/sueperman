/** Explicit opt-in: at most two Gemini uploads, no Bright Data or OpenAI calls. */
import { test, expect } from "@playwright/test";
import path from "node:path";

test.skip(process.env.P1_LIVE_E2E !== "1", "Opt-in only: makes two capped Gemini requests and public-source reads.");

test("live image extraction, human confirmation and CPSC recall export", async ({ page }, info) => {
  test.setTimeout(90000);
  await page.goto("/");
  const upload = page.waitForResponse(r => r.url().endsWith("/api/uploads/purchases") && r.request().method() === "POST");
  await page.getByLabel("Upload purchases or receipt").setInputFiles(path.resolve("../../demo/receipt-synthetic.png"));
  const uploaded = await upload;
  expect(uploaded.ok()).toBeTruthy();
  const imported = await uploaded.json();
  const row = page.locator(`[data-product-id="${imported.product_ids[0]}"]`);
  await expect(row).toBeVisible({timeout:15000});
  if (await row.getByRole("button", { name: "Confirm identifiers" }).count()) {
    await row.getByLabel("I checked these identifiers against my receipt or product.").check();
    await row.getByRole("button", {name:"Confirm identifiers"}).click();
  }
  await expect(row.getByText("Identifiers confirmed by you")).toBeVisible();
  await page.getByText("Demo controls & provider health").click();
  await page.getByLabel("Run mode").selectOption("live");
  // Only the new purchase: API run starts with this upload's returned ID; avoids historic/demo model calls.
  const products = await (await page.request.get("http://localhost:8000/api/products")).json();
  const scan = products.find((p: {source_type:string;product:{user_confirmed_identifiers:boolean}}) => p.source_type === "image" && p.product.user_confirmed_identifiers);
  expect(scan).toBeTruthy();
  const response=await page.request.post("http://localhost:8000/api/runs",{data:{purchase_ids:[scan.purchase_id],mode:"live",idempotency_key:crypto.randomUUID()}});
  expect(response.ok()).toBeTruthy();
  const run=await response.json();
  await page.goto(`/runs/${run.run_id}`);
  await expect(page.getByText("Run completed",{exact:true})).toBeVisible({timeout:30000});
  await expect(page.getByText("recall: cpsc",{exact:true})).toBeVisible();
  await page.getByTestId("opportunity-card").filter({hasText:"Recall matched"}).getByRole("link",{name:"Review details"}).click();
  await expect(page.getByText(/LIVE CPSC lookup/)).toBeVisible();
  await expect(page.getByText("Selected action: produce_packet",{exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath("live-recall.png"),fullPage:true});
  await page.getByRole("button",{name:"Prepare claim packet"}).click();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button",{name:"Approve draft locally"}).click();
  await expect(page.getByRole("button",{name:"Export Markdown"})).toBeEnabled();
  const download=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export Markdown"}).click();
  expect((await download).suggestedFilename()).toBe("sueperman-draft.md");
});

test("live PDF extraction returns identifiers for review",async({page},info)=>{
  await page.goto("/");
  const upload=page.waitForResponse(r => r.url().endsWith("/api/uploads/purchases") && r.request().method() === "POST");
  await page.getByLabel("Upload purchases or receipt").setInputFiles(path.resolve("../../demo/receipt-synthetic.pdf"));
  const uploaded=await upload;
  expect(uploaded.ok()).toBeTruthy();
  const imported=await uploaded.json();
  const row=page.locator(`[data-product-id="${imported.product_ids[0]}"]`);
  await expect(row.getByText(/ZHX-PB22/).first()).toBeVisible({timeout:15000});
  await expect(row.getByRole("button",{name:"Confirm identifiers"})).toBeDisabled();
  await page.screenshot({path:info.outputPath("live-pdf-review.png"),fullPage:true});
});

test("live settlement sources stay distinct from personal eligibility and export locally",async({page},info)=>{
  test.setTimeout(90000);
  const response=await page.request.post("http://localhost:8000/api/uploads/purchases",{multipart:{file:{name:"synthetic-case-test.csv",mimeType:"text/csv",buffer:Buffer.from("product_name,merchant,purchased_at\nSYNTHETIC transaction for source verification,Kroger,2024-06-12\n")}}});
  expect(response.ok()).toBeTruthy();
  const imported=await response.json();
  const started=await page.request.post("http://localhost:8000/api/runs",{data:{purchase_ids:imported.purchase_ids,mode:"live",idempotency_key:crypto.randomUUID()}});
  const run=await started.json();
  await page.goto(`/runs/${run.run_id}`);
  await expect(page.getByText(/Run (completed|partial)/,{exact:true})).toBeVisible({timeout:60000});
  const card=page.getByTestId("opportunity-card").filter({hasText:"Kirkbride"});
  await expect(card.getByText("LIVE verified settlement sources",{exact:true})).toBeVisible();
  await card.getByRole("link",{name:"Review details"}).click();
  await expect(page.getByText("Personal eligibility unconfirmed — preparation only",{exact:true})).toBeVisible();
  await expect(page.getByText(/Official claim deadline: 2026-12-21/)).toBeVisible();
  await expect(page.getByRole("link",{name:/administrator-hosted order/})).toBeVisible();
  await expect(page.getByText("SIMULATED CASE — NO REAL CLAIM AVAILABLE",{exact:true})).toHaveCount(0);
  await page.screenshot({path:info.outputPath("live-settlement.png"),fullPage:true});
  await page.getByRole("button",{name:"Prepare claim packet"}).click();
  await expect(page.getByText("LIVE verified settlement sources",{exact:true})).toBeVisible();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await page.getByRole("button",{name:"Approve draft locally"}).click();
  await expect(page.getByRole("button",{name:"Export Markdown"})).toBeEnabled();
  const download=page.waitForEvent("download");
  await page.getByRole("button",{name:"Export Markdown"}).click();
  await download;
});
