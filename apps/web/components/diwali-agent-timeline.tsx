"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { post, type DiwaliMessage, type Run } from "@/lib/api";
import { DiwaliCaseEvidence, diwaliTransportLabel } from "./diwali-case-evidence";

export function DiwaliAgentTimeline({ run, messages, error }: {
  run: Run; messages: DiwaliMessage[]; error: string;
}) {
  const router = useRouter();
  const [fallbackBusy, setFallbackBusy] = useState(false);
  const [fallbackError, setFallbackError] = useState("");
  async function startFallback() {
    setFallbackBusy(true);
    setFallbackError("");
    try {
      const next = await post<Run>("/runs", { purchase_ids: run.purchase_ids, mode: "demo",
        collaboration_mode: "deterministic", fallback_of: run.run_id, idempotency_key: crypto.randomUUID() });
      router.push(`/runs/${next.run_id}`);
    } catch (err) {
      setFallbackError((err as Error).message);
      setFallbackBusy(false);
    }
  }
  if (!run.collaboration_mode || run.collaboration_mode === "deterministic") return null;
  return <section className="section">
    <h2>Agent collaboration</h2>
    <div className="providers">
      <span data-testid="transport-mode">{diwaliTransportLabel(run.actual_transport, run.collaboration_mode)}</span>
      <span data-testid="source-mode">{run.source_mode === "live" ? "SOURCE LIVE" : "SOURCE RECORDED"}</span>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {fallbackError && <p role="alert" className="error">{fallbackError}</p>}
    {["partial", "failed"].includes(run.status) && <div className="actions">
      <button disabled={fallbackBusy || !run.purchase_ids?.length} onClick={startFallback}>
        Run recorded-source workflow separately
      </button>
      <p className="small">Starts a new run. This run keeps its original failure and evidence.</p>
    </div>}
    <div data-testid="agent-timeline" className="panel">
      {messages.length ? <ol className="timeline">{messages.map(message =>
        <li key={message.message_id}>
          <span className="number">{String(message.seq).padStart(2, "0")}</span>
          <div><strong>{message.type}</strong><p className="small">{message.sender} to {message.recipient}</p></div>
        </li>)}</ol> : <p>No accepted actor messages yet.</p>}
    </div>
    <DiwaliCaseEvidence messages={messages} />
  </section>;
}
