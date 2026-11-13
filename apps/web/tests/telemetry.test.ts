import { test } from "node:test";
import assert from "node:assert/strict";
import { sanitizeEvent, sanitizeTransaction } from "../lib/telemetry";

test("browser events keep readable stack locations but drop uploaded facts and credentials", () => {
  const clean = sanitizeEvent({
    event_id: "safe-id",
    message: "receipt private-order",
    user: { email: "private@example.test" },
    request: { headers: { Authorization: "secret-token" } },
    extra: { receipt: "private-order" },
    exception: {
      values: [
        {
          type: "Error",
          value: "secret-token",
          stacktrace: {
            frames: [
              {
                filename: "http://localhost:3001/app/page.tsx",
                function: "Page",
                lineno: 7,
                context_line: 'throw new Error("fixed")',
                vars: { receipt: "private-order" },
              },
            ],
          },
        },
      ],
    },
  });
  assert.equal(clean.exception?.values?.[0].type, "Error");
  assert.equal(clean.exception?.values?.[0].stacktrace?.frames?.[0].lineno, 7);
  assert.ok(!JSON.stringify(clean).includes("secret-token"));
  assert.ok(!JSON.stringify(clean).includes("private-order"));
  assert.ok(!JSON.stringify(clean).includes("private@example.test"));
});

test("trace attributes cannot retain request bodies or URL parameters", () => {
  const clean = sanitizeTransaction({
    event_id: "safe-id",
    transaction: "/orders?secret=private-order",
    contexts: { trace: { trace_id: "a".repeat(32), span_id: "c".repeat(16) } },
    spans: [
      {
        op: "http.client",
        description: "https://example.test/?key=secret-token",
        data: { "http.request.body": "private receipt" },
        span_id: "b".repeat(16),
        trace_id: "a".repeat(32),
        start_timestamp: 1,
        timestamp: 2,
        status: "ok",
      },
    ],
  });
  assert.ok(!JSON.stringify(clean).includes("private-order"));
  assert.ok(!JSON.stringify(clean).includes("secret-token"));
  assert.ok(!JSON.stringify(clean).includes("private receipt"));
});

test("privacy filtering preserves source-map debug IDs needed for readable stacks", () => {
  const event = {
    event_id: "safe",
    debug_meta: {
      images: [
        {
          type: "sourcemap" as const,
          debug_id: "07cffb3b-5aa1-469b-b536-80fa6149316e",
          code_file: "http://localhost:3001/_next/static/chunks/app.js",
        },
      ],
    },
  };
  const clean = sanitizeEvent(event);
  assert.equal(
    clean.debug_meta?.images?.[0].debug_id,
    "07cffb3b-5aa1-469b-b536-80fa6149316e",
  );
});

test("streamed spans scrub URL names and request attributes before export", async () => {
  const telemetry = await import("../lib/telemetry");
  assert.equal(typeof telemetry.sanitizeSpan, "function");
  const clean = telemetry.sanitizeSpan({
    name: "https://example.test/?token=secret-token",
    trace_id: "a".repeat(32),
    span_id: "b".repeat(16),
    start_timestamp: 1,
    end_timestamp: 2,
    status: "ok",
    is_segment: true,
    attributes: { "sentry.op": "http.client", body: "private receipt" },
  });
  assert.ok(!JSON.stringify(clean).includes("secret-token"));
  assert.ok(!JSON.stringify(clean).includes("private receipt"));
});

test("replay correlation survives filtering while user tags are removed", () => {
  const clean = sanitizeEvent({
    tags: { replayId: "a".repeat(32), receipt: "private receipt" },
  });
  assert.equal(clean.tags?.replayId, "a".repeat(32));
  assert.ok(!JSON.stringify(clean).includes("private receipt"));
});
