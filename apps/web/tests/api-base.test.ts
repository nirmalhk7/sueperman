/** Catch deployed browser requests accidentally targeting the visitor's localhost. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

for (const [base, expected] of [
  [undefined, "http://localhost:8000/api/health"],
  ["", "/api/health"],
  ["https://app.example.test", "https://app.example.test/api/health"],
] as const) {
  test(`API request respects ${base === undefined ? "local default" : JSON.stringify(base)} base`, () => {
    const env = { ...process.env };
    if (base === undefined) delete env.NEXT_PUBLIC_API_BASE_URL;
    else env.NEXT_PUBLIC_API_BASE_URL = base;
    const result = spawnSync(process.execPath, ["--import", "tsx", "--input-type=module", "-e", `
      globalThis.fetch = async url => {
        process.stdout.write(String(url));
        return new Response('{}', { status: 200 });
      };
      const loaded = await import('./lib/api.ts');
      const api = loaded.api || loaded.default.api;
      await api('/health');
    `], { env, encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stdout, expected);
  });
}
