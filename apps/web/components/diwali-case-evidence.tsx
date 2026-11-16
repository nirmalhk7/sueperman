import type { DiwaliMessage } from "@/lib/api";

export function diwaliTransportLabel(actual?: string | null, requested?: string): string {
  if (actual === "band") return "BAND LIVE";
  if (actual === "local") return "LOCAL TEST";
  return requested === "band" ? "BAND NOT STARTED" : "LOCAL TEST";
}

export function DiwaliCaseEvidence({ messages }: { messages: DiwaliMessage[] }) {
  const reviews = [...new Map(messages.filter(m => m.type === "ReviewReport")
    .map(m => [m.case_id, m])).values()];
  return <div className="cards section">{reviews.map(message => {
    const review = message.payload;
    return <article className="card" key={message.case_id}>
      <h3>Purchase and official source</h3>
      <dl data-testid="model-comparison" className="split">
        <div><dt>Purchase model</dt><dd className="mono">{review.compared_identifiers?.purchase_model || "Not provided"}</dd></div>
        <div><dt>Official affected models</dt><dd className="mono">{review.compared_identifiers?.source_models.join(", ") || "Unknown"}</dd></div>
      </dl>
      <p>{review.rule_result}</p>
      {review.challenge_code === "MODEL_MISMATCH" && <p data-testid="challenge-reason">MODEL_MISMATCH</p>}
      {review.challenge_code === "MISSING_PURCHASE_FACT" && <p>Which model number is printed on your purchase?</p>}
      {!!review.requested_fields?.length && <div><h4>Evidence questions</h4>
        <ul>{review.requested_fields.map(field => <li key={field}>{field.replaceAll("_", " ")}</li>)}</ul></div>}
      {review.review_note && <p>Review note: {review.review_note}</p>}
      <p className="small break-all">Sources: {message.source_refs.join(", ")}</p>
    </article>;
  })}</div>;
}
