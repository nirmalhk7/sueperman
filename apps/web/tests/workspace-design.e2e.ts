import { test, expect } from "@playwright/test";

// Catches a disconnected role selector, stale role explanation, or a preview
// presented as actual sponsor execution. No provider calls needed.
test("workflow preview explains each selected agent without claiming execution", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  const preview = page.getByRole("region", { name: "How the agent team works" });
  await expect(preview).toBeVisible();
  await preview.getByRole("tab", { name: /Skeptic/ }).click();
  await expect(preview.getByRole("tabpanel")).toContainText("challenge");
  await expect(preview.getByRole("tabpanel")).toContainText("exclusions");
  await preview.getByRole("tab", { name: /Skeptic/ }).press("ArrowRight");
  await expect(preview.getByRole("tab", { name: /Builder/ })).toBeFocused();
  await expect(preview.getByRole("tabpanel")).toContainText("missing fact");
  await expect(preview).toContainText("How it works");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: "../../.impeccable/review/desktop.png", fullPage: true, animations: "disabled" });
  await page.setViewportSize({ width: 572, height: 852 });
  await page.screenshot({ path: "../../.impeccable/review/user-572.png", fullPage: true, animations: "disabled" });
});

// Catches clipped mobile controls or a fixed desktop layout that forces the
// entire page to scroll sideways; the purchase table may scroll independently.
test("purchase workspace remains usable in a narrow viewport with reduced motion", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByLabel("Upload purchases or receipt")).toBeVisible();
  const preview = page.getByRole("region", { name: "How the agent team works" });
  await preview.getByRole("tab", { name: /Builder/ }).click();
  await expect(preview.getByRole("tabpanel")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: "../../.impeccable/review/mobile.png", fullPage: true, animations: "disabled" });
});
