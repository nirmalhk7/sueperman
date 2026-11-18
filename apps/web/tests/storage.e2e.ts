import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

test("restored approval exports the original draft after persistent Compose recovery", async ({ page }, testInfo) => {
  const packet = process.env.STORAGE_RESTORE_PACKET_ID;
  const expected = process.env.STORAGE_EXPORT_SHA256;
  expect(packet, "storage acceptance must provide the restored packet").toBeTruthy();
  expect(expected, "storage acceptance must bind the original export").toBeTruthy();
  await page.goto(`/claims/${packet}`);
  await expect(page.getByRole("heading", { name: "Review your remedy draft." })).toBeVisible();
  await expect(page.getByText("Approved locally", { exact: true })).toBeVisible();
  await expect(page.getByText("Local draft only", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeEnabled();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const download = await pending;
  const path = testInfo.outputPath("restored-draft.md");
  await download.saveAs(path);
  expect(createHash("sha256").update(await readFile(path)).digest("hex")).toBe(expected);
  await page.screenshot({ path: testInfo.outputPath("restored-approval.png"), fullPage: true });
});
