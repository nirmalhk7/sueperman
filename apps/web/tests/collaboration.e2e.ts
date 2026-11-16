import { test, expect } from '@playwright/test';

const api = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
test('team case board explains exact, excluded and missing cases, persists answers and exports locally', async ({ page }) => {
  const seed = await (await page.request.post(`${api}/api/demo/reset`)).json();
  await page.request.post(`${api}/api/runs`, {data: {purchase_ids: seed.purchase_ids, mode: 'demo', idempotency_key: crypto.randomUUID()}});
  const opportunities = await (await page.request.get(`${api}/api/opportunities`)).json();
  for (const state of ['rejected', 'needs_review', 'verified_match']) {
    const item = opportunities.find((o: {kind: string; status: string}) => o.kind === 'recall' && o.status === state);
    await page.goto(`/opportunities/${item.id}`);
    await page.getByRole('button', {name: 'Investigate with agent team'}).click();
    await expect(page.getByRole('heading', {name: 'Your remedy case'})).toBeVisible();
    await expect(page.getByText('OFFLINE REPLAY — no live sponsor execution', {exact: true})).toBeVisible();
    await expect(page.getByTestId('role-event')).toHaveCount(6);
    await expect(page.getByRole('heading', {name: 'Challenge', exact: true})).toBeVisible();
    if (state === 'rejected') {
      await expect(page.getByText('Excluded by official conditions: model_number')).toBeVisible();
      await expect(page.getByRole('button', {name: 'Approve draft locally'})).toHaveCount(0);
    } else if (state === 'needs_review') {
      await page.getByLabel('Model number').fill('ZHX-PB22');
      await page.getByLabel('I checked this fact against the product or record.').check();
      await page.getByRole('button', {name: 'Confirm answer'}).click();
      await expect(page.getByRole('button', {name: 'Prepare claim packet'})).toBeVisible();
      await page.reload();
      await expect(page.getByText('2 retained revisions')).toBeVisible();
    } else {
      await page.getByRole('button', {name: 'Prepare claim packet'}).click();
      await expect(page.getByRole('button', {name: 'Export Markdown'})).toBeDisabled();
      await page.getByLabel('I reviewed this draft and understand approval stays local.').check();
      await page.getByRole('button', {name: 'Approve draft locally'}).click();
      await expect(page.getByText('Approved locally', {exact: true})).toBeVisible();
      const download = page.waitForEvent('download');
      await page.getByRole('button', {name: 'Export Markdown'}).click();
      expect((await download).suggestedFilename()).toBe('sueperman-team-draft.md');
    }
  }
});

test('a stale team export reports a review error instead of downloading', async ({ page }) => {
  const seed = await (await page.request.post(`${api}/api/demo/reset`)).json();
  const started = await (await page.request.post(`${api}/api/collaborations`, {data: {
    product_ids: [seed.product_ids[0]], mode: 'replay', idempotency_key: crypto.randomUUID(),
  }})).json();
  await page.goto(`/collaborations/${started.id}`);
  await page.getByRole('button', {name: 'Prepare claim packet'}).click();
  await page.getByLabel('I reviewed this draft and understand approval stays local.').check();
  await page.getByRole('button', {name: 'Approve draft locally'}).click();
  await expect(page.getByText('Approved locally', {exact: true})).toBeVisible();
  // Backend source-change invalidation has separate SQLite integration coverage.
  await page.route(`**/api/collaborations/${started.id}/export`, route => route.fulfill({status: 409, json: {message: 'Evidence changed'}}));
  await page.getByRole('button', {name: 'Export Markdown'}).click();
  await expect(page.getByRole('alert').filter({hasText: 'This revision cannot be exported'})).toHaveText('This revision cannot be exported. Refresh and review the current draft.');
});

test('live team selection explains sanitized sharing and shows missing providers honestly', async ({ page }) => {
  const seed = await (await page.request.post(`${api}/api/demo/reset`)).json();
  await page.request.post(`${api}/api/runs`, {data: {purchase_ids: seed.purchase_ids, mode: 'demo', idempotency_key: crypto.randomUUID()}});
  const opportunities = await (await page.request.get(`${api}/api/opportunities`)).json();
  const item = opportunities.find((o: {kind: string; status: string}) => o.kind === 'recall' && o.status === 'verified_match');
  await page.goto(`/opportunities/${item.id}`);
  await page.getByLabel('Investigation mode').selectOption('live');
  await expect(page.getByText('Only sanitized product facts and public evidence go to BAND, Agent37, AdaL and Lyzr. The challenge uses a reviewed Finch skill. Raw receipts and unrelated purchases stay out.')).toBeVisible();
  await page.getByRole('button', {name: 'Investigate with agent team'}).click();
  await expect(page.getByText('Blocked providers: band, agent37, adal, finch, lyzr')).toBeVisible();
  await expect(page.getByRole('button', {name: 'Approve draft locally'})).toHaveCount(0);
});
