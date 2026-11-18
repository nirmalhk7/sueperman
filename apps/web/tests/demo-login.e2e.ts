import { expect, test } from "@playwright/test";

test("fake sign-in cannot submit before JavaScript is ready", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    await page.goto("/demo-login");
    await expect(page.getByRole("button", { name: "Sign in to demo", exact: true })).toBeDisabled();
  } finally {
    await context.close();
  }
});

// Catches removing the explicit demo boundary, submitting credentials, or
// failing to switch back to the form after ending the simulated session.
for (const width of [1280, 390]) {
  test(`fake sign-in is local and reversible at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const submissions: string[] = [];
    page.on("request", request => {
      if (!["GET", "HEAD"].includes(request.method())) submissions.push(request.url());
    });
    await page.goto("/demo-login");
    await expect(page.getByRole("heading", { name: "Demo sign in", exact: true })).toBeVisible();
    await expect(page.getByText(/no private account or data isolation/i)).toBeVisible();
    await expect(page.getByLabel("Demo email")).toHaveValue("visitor@example.invalid");
    await expect(page.getByLabel("Demo password")).toHaveValue("demo-only");
    await expect(page.getByLabel("Demo email")).toHaveAttribute("readonly", "");
    await expect(page.getByLabel("Demo password")).toHaveAttribute("readonly", "");
    await page.screenshot({ path: `test-results/demo-login-form-${width}.png`, fullPage: true });
    await expect(page.getByRole("button", { name: "Sign in to demo", exact: true })).toBeEnabled();
    await page.getByRole("button", { name: "Sign in to demo", exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("status")).toContainText("Demo session started");
    await expect(page.getByRole("link", { name: "Continue to workspace" })).toHaveAttribute("href", "/");
    await expect(page.getByText(/no private account or data isolation/i)).toBeVisible();
    await page.screenshot({ path: `test-results/demo-login-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole("button", { name: "End demo session" }).click();
    await expect(page.getByRole("button", { name: "Sign in to demo", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Sign in to demo", exact: true }).click();
    await expect(page.getByRole("status")).toContainText("Demo session started");
    await page.reload();
    await expect(page.getByRole("button", { name: "Sign in to demo", exact: true })).toBeVisible();
    expect(submissions).toEqual([]);
  });
}
