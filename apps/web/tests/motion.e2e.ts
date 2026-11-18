import { test, expect } from "@playwright/test";

// Catches a stationary selector, leaking/repeating motion, or a role change
// whose feedback disappears when the user requests reduced motion.
for (const reducedMotion of ["no-preference", "reduce"] as const) {
  test(`role motion settles and remains usable with ${reducedMotion}`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion });
    await page.goto("/");
    const preview = page.getByRole("region", { name: "How the agent team works" });
    const rail = preview.getByTestId("agent-selection-marker");
    await expect(rail).toBeVisible();
    const before = await rail.boundingBox();
    await preview.getByRole("tab", { name: "Skeptic", exact: true }).click();
    await preview.getByRole("tab", { name: "Builder", exact: true }).click();
    await expect(preview.getByRole("tabpanel")).toContainText("missing fact");
    if (reducedMotion === "no-preference") {
      const effects = await preview.evaluate(element => element.getAnimations({ subtree: true })
        .filter(a => a.playState === "running"));
      expect(effects.length).toBeGreaterThan(1);
    }
    await expect.poll(async () => (await rail.boundingBox())!.x).toBeGreaterThan(before!.x + 50);
    await expect.poll(() => preview.evaluate(element =>
      element.getAnimations({ subtree: true }).filter(a => a.playState === "running").length,
    )).toBe(0);
    if (reducedMotion === "reduce") {
      expect(await preview.evaluate(element => element.getAnimations({ subtree: true })
        .filter(a => a.effect instanceof KeyframeEffect && a.effect.getKeyframes()
          .some(frame => "transform" in frame || "clipPath" in frame || "strokeDashoffset" in frame)).length)).toBe(0);
    }
    await preview.getByRole("tab", { name: "Builder", exact: true }).press("Home");
    await expect(preview.getByRole("tab", { name: "Scout", exact: true })).toBeFocused();
  });
}

// Holding the HTTP boundary makes pending feedback observable without paid
// calls. A rejected operation must restore the control and show its error.
test("purchase check shows pending work until the request finishes", async ({ page }) => {
  let finish: () => void = () => {};
  const pending = new Promise<void>(resolve => { finish = resolve; });
  await page.route("**/api/runs", async route => {
    await pending;
    await route.fulfill({ status: 503, json: { message: "Check temporarily unavailable" } });
  });
  await page.route("**/api/products", route => route.fulfill({ json: [{ id: "product", purchase_id: "purchase", demo: false,
    product: {product_name: "Power bank", brand: "NEWDERY", model_number: "ZHX-PB22"} }] }));
  await page.goto("/");
  const button = page.getByRole("button", { name: "Check my purchases", exact: true });
  await button.click();
  try {
    await expect(button).toHaveAttribute("aria-busy", "true");
    await expect(button).toBeDisabled();
  } finally { finish(); }
  await expect(page.getByRole("alert").filter({ hasText: "Check temporarily unavailable" })).toBeVisible();
  await expect(button).toBeEnabled();
  await expect(button).toHaveAttribute("aria-busy", "false");
});
