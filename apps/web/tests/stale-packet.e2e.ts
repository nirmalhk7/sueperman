import { test, expect } from "@playwright/test";

test("withdrawn source verification disables local approval and export", async ({ page }) => {
  await page.route("**/api/claim-packets/stale-packet", route => route.fulfill({ json: {
    id: "stale-packet", created_at: "2026-11-13T00:00:00Z", updated_at: "2026-11-13T00:00:00Z",
    demo: false, kind: "settlement", status: "needs_evidence", mode: "live",
    verification_status: "unavailable", markdown: "Prior information draft; sources require review.",
    contact_or_portal_url: null, required_documents: [], missing_documents: ["Renew primary sources"],
    user_declaration_required: true, completed_fields: {}, instructions: "Preparation only",
    generated_at: "2026-11-13T00:00:00Z", approved_at: null, reviewed_at: null,
  } }));
  await page.goto("/claims/stale-packet");
  await expect(page.getByText("SETTLEMENT VERIFICATION UNAVAILABLE — PRIOR DRAFT ONLY", { exact: true })).toBeVisible();
  await page.getByLabel("I reviewed this draft and understand approval stays local.").check();
  await expect(page.getByRole("button", { name: "Approve draft locally" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Export Markdown" })).toBeDisabled();
});
