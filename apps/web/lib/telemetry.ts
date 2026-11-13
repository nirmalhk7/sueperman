import type { Event, withStreamedSpan } from "@sentry/nextjs";

type StreamedSpanJSON = Parameters<Parameters<typeof withStreamedSpan>[0]>[0];
const scrubSource = (line: string) =>
  line.replace(/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/g, '"<redacted>"');
const verification =
  /^Sueperman Sentry verification [0-9]{10,16} (backend|frontend)$/;
const message = (value: unknown) =>
  typeof value === "string" && verification.test(value)
    ? value
    : "Application error details redacted";

export function sanitizeEvent<T extends Event>(event: T): T {
  const trace = event.contexts?.trace;
  const exception = event.exception?.values?.map((error) => ({
    type: error.type,
    value: message(error.value),
    mechanism: { type: "generic", handled: error.mechanism?.handled ?? false },
    stacktrace: {
      frames: error.stacktrace?.frames?.map((frame) => ({
        filename: frame.filename?.split("?")[0],
        function: frame.function,
        abs_path: frame.abs_path?.split("?")[0],
        lineno: frame.lineno,
        colno: frame.colno,
        in_app: frame.in_app,
        context_line: frame.context_line
          ? scrubSource(frame.context_line)
          : undefined,
        pre_context: frame.pre_context?.map(scrubSource),
        post_context: frame.post_context?.map(scrubSource),
      })),
    },
  }));
  return {
    event_id: event.event_id,
    timestamp: event.timestamp,
    platform: event.platform,
    environment: event.environment,
    release: event.release,
    sdk: event.sdk,
    level: event.level,
    debug_meta: event.debug_meta
      ? {
          images: event.debug_meta.images
            ?.filter((image) => image.type === "sourcemap")
            .map((image) => ({
              ...image,
              code_file: image.code_file?.split("?")[0],
            })),
        }
      : undefined,
    tags:
      typeof event.tags?.replayId === "string" &&
      /^[a-f0-9]{32}$/.test(event.tags.replayId)
        ? { replayId: event.tags.replayId }
        : undefined,
    message: message(event.message),
    exception: exception ? { values: exception } : undefined,
    contexts: trace
      ? {
          trace: {
            trace_id: trace.trace_id,
            span_id: trace.span_id,
            parent_span_id: trace.parent_span_id,
            op: trace.op,
            status: trace.status,
          },
        }
      : undefined,
  } as T;
}

export function sanitizeTransaction<T extends Event>(event: T): T {
  const base = sanitizeEvent(event);
  return {
    ...base,
    type: "transaction",
    message: undefined,
    exception: undefined,
    transaction: "Sueperman web request",
    start_timestamp: event.start_timestamp,
    spans: event.spans?.map((span) => ({
      span_id: span.span_id,
      trace_id: span.trace_id,
      parent_span_id: span.parent_span_id,
      start_timestamp: span.start_timestamp,
      timestamp: span.timestamp,
      op: span.op,
      description: span.op,
      data: {},
      status: span.status,
    })),
  } as T;
}

export const dataCollection = {
  userInfo: false,
  cookies: false,
  httpHeaders: false,
  httpBodies: [],
  urlQueryParams: false,
  graphQL: { document: false, variables: false },
  genAI: { inputs: false, outputs: false },
  mcp: { inputs: false, outputs: false },
  databaseQueryData: false,
  queues: false,
  stackFrameVariables: false,
  frameContextLines: 2,
};

export function sanitizeLog<
  T extends { message: unknown; attributes?: Record<string, unknown> },
>(log: T): T | null {
  return typeof log.message === "string" && verification.test(log.message)
    ? { ...log, attributes: {} }
    : null;
}

export function sanitizeSpan(span: StreamedSpanJSON): StreamedSpanJSON {
  const candidate = span.attributes["sentry.op"];
  const op =
    typeof candidate === "string" && /^[a-z][a-z0-9_.-]{0,80}$/.test(candidate)
      ? candidate
      : "operation";
  return {
    trace_id: span.trace_id,
    span_id: span.span_id,
    parent_span_id: span.parent_span_id,
    name: op,
    start_timestamp: span.start_timestamp,
    end_timestamp: span.end_timestamp,
    status: span.status,
    is_segment: span.is_segment,
    attributes: { "sentry.op": op },
  };
}
