export function opportunityLabel(status: string, simulated: boolean): string {
  if (simulated) return "Simulated settlement";
  return (
    (
      {
        verified_match: "Recall matched",
        rejected: "Not affected",
        needs_review: "Needs information",
      } as Record<string, string>
    )[status] || "Needs information"
  );
}
