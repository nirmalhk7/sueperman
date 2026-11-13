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
      } as Record<string, string>
    )[status] || "Needs information"
  );
}

export function sourceLabel(kind: string, mode: string, simulated: boolean, status = ""): string {
  if (simulated) return "SIMULATED CASE — NO REAL CLAIM AVAILABLE";
  if (kind === "settlement" && status === "unavailable") return "SETTLEMENT VERIFICATION UNAVAILABLE — PRIOR SOURCES ONLY";
  if (mode === "replay") return "OFFLINE REPLAY of a real published recall";
  return kind === "settlement" ? "LIVE verified settlement sources" : "LIVE CPSC lookup";
}
