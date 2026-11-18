"use client";

import { type DiwaliMessage, type Run } from "@/lib/api";
import { DiwaliCaseEvidence, diwaliTransportLabel } from "./diwali-case-evidence";

export function DiwaliAgentTimeline({ run, messages, error }: {
  run: Run; messages: DiwaliMessage[]; error: string;
}) {
  if (run.source_mode !== "live" || !run.collaboration_mode || run.collaboration_mode === "deterministic") return null;
  return <section className="section">
    <h2>Agent collaboration</h2>
    <div className="providers">
      <span data-testid="transport-mode">{diwaliTransportLabel(run.actual_transport, run.collaboration_mode)}</span>
      <span data-testid="source-mode">{run.source_mode === "live" ? "SOURCE LIVE" : "SOURCE RECORDED"}</span>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
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
