import { expect, test } from "@playwright/test";

// Retired presentation sign-in must send old bookmarks to the real workspace.
for (const width of [1280, 390]) {
  test(`retired sign-in redirects to purchases at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/demo-login");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: /My purchases/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /demo/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /sign in/i })).toHaveCount(0);
  });
}
