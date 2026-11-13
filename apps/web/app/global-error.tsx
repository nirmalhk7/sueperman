"use client";
import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);
  return (
    <html lang="en">
      <body>
        <h1>Sueperman hit an unexpected error.</h1>
        <p>An unexpected error interrupted this page. You can try again.</p>
        <button onClick={reset}>Try again</button>
      </body>
    </html>
  );
}
