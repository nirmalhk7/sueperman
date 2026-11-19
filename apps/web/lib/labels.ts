export function opportunityLabel(status: string, simulated: boolean): string {
  if (simulated) return "Simulated settlement";
  return (
    (
      {
        verified_match: "Recall matched",
        rejected: "Not affected",
        ineligible: "Not affected",
        expired: "Deadline passed",
        unavailable: "Sources unavailable",
        needs_review: "Needs information",
        uncertain: "Eligibility unconfirmed",
        eligible_candidate: "Potential opportunity",
      } as Record<string, string>
    )[status] || "Needs information"
  );
}

export function readableLabel(value: string): string {
  const words = value.replaceAll("_", " ");
  return words ? words[0].toUpperCase() + words.slice(1) : "";
}

export function decisionLabel(value: string): string {
  return ({
    inspect_more: "Review more evidence",
    request_user_info: "Ask for missing information",
    produce_packet: "Prepare a remedy draft",
    reject_candidate: "Exclude this product",
  } as Record<string, string>)[value] ?? "Review evidence";
}

export function caseStatusLabel(value: string): string {
  return ({
    queued: "Waiting to start",
    investigating: "Looking up official sources",
    challenging: "Checking the proposed match",
    building: "Preparing the case summary",
    partial: "Investigation incomplete",
    rejected: "Not affected",
    needs_information: "Needs information",
    ready_for_review: "Ready for review",
  } as Record<string, string>)[value] ?? readableLabel(value);
}

export function sourceLabel(kind: string, mode: string, simulated: boolean, status = ""): string {
  if (simulated) return "SIMULATED CASE — NO REAL CLAIM AVAILABLE";
  if (kind === "settlement" && status === "unavailable") return "SETTLEMENT VERIFICATION UNAVAILABLE — PRIOR SOURCES ONLY";
  if (mode === "replay") return "OFFLINE REPLAY of a real published recall";
  return kind === "settlement" ? "LIVE verified settlement sources" : "LIVE CPSC lookup";
}
