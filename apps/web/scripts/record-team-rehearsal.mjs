// Actual local UI footage, explicitly replay-only. Not an AdaL-produced final demo.
// Run only against an isolated synthetic demo database; resets synthetic demo data.
import { chromium, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';

if (process.env.SYNTHETIC_DEMO_RECORDING !== '1') throw new Error('Set SYNTHETIC_DEMO_RECORDING=1 for an isolated synthetic database.');
const web = process.env.WEB_URL || 'http://localhost:3001';
const api = process.env.API_URL || 'http://localhost:8000';
const output = resolve(process.cwd(), '../../output/sueperman-v2-rehearsal');
await mkdir(output, {recursive: true});
const browser = await chromium.launch({executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined});
const context = await browser.newContext({viewport: {width: 1440, height: 960}, recordVideo: {dir: output, size: {width: 1440, height: 960}}});
const page = await context.newPage();
const seed = await (await page.request.post(`${api}/api/demo/reset`)).json();
await page.request.post(`${api}/api/runs`, {data: {purchase_ids: seed.purchase_ids, mode: 'demo', idempotency_key: crypto.randomUUID()}});
const opportunities = await (await page.request.get(`${api}/api/opportunities`)).json();
for (const state of ['rejected', 'needs_review', 'verified_match']) {
  const item = opportunities.find(o => o.kind === 'recall' && o.status === state);
  await page.goto(`${web}/opportunities/${item.id}`);
  await page.getByRole('button', {name: 'Investigate with agent team'}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(2500);
  await page.getByRole('button', {name: 'Investigate with agent team'}).click();
  await expect(page.getByTestId('role-event')).toHaveCount(6);
  await page.screenshot({path: resolve(output, `${state}.png`), fullPage: true});
  await page.waitForTimeout(5000);
  if (state === 'needs_review') {
    await page.getByLabel('Model number').fill('ZHX-PB22');
    await page.getByLabel('I checked this fact against the product or record.').check();
    await page.waitForTimeout(2500);
    await page.getByRole('button', {name: 'Confirm answer'}).click();
    await expect(page.getByRole('button', {name: 'Prepare claim packet'})).toBeVisible();
  }
  await page.getByRole('heading', {name: 'Agent timeline'}).scrollIntoViewIfNeeded();
  await page.waitForTimeout(5000);
  if (state === 'verified_match') {
    await page.getByRole('button', {name: 'Prepare claim packet'}).click();
    await page.getByRole('heading', {name: 'Review your remedy draft'}).scrollIntoViewIfNeeded();
    await page.waitForTimeout(5000);
    await page.getByLabel('I reviewed this draft and understand approval stays local.').check();
    await page.getByRole('button', {name: 'Approve draft locally'}).click();
    await expect(page.getByText('Approved locally', {exact: true})).toBeVisible();
    const download = page.waitForEvent('download');
    await page.getByRole('button', {name: 'Export Markdown'}).click();
    await (await download).saveAs(resolve(output, 'synthetic-local-draft.md'));
    await page.waitForTimeout(4000);
  }
}
const video = page.video();
await context.close();
await video.saveAs(resolve(output, 'replay-ui.webm'));
await browser.close();
console.log('Recorded replay UI only: output/sueperman-v2-rehearsal/replay-ui.webm');
