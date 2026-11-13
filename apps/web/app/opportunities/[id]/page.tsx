"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, post, type Detail, type Packet } from "@/lib/api";
import { opportunityLabel } from "@/lib/labels";
export default function Page() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    void api<Detail>(`/opportunities/${id}`)
      .then(setD)
      .catch((e) => setError(e.message));
  }, [id]);
  async function prepare() {
    setBusy(true);
    try {
      const p = await post<Packet>(`/opportunities/${id}/claim-packet`);
      router.push(`/claims/${p.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  if (!d)
    return (
      <p role={error ? "alert" : "status"}>{error || "Loading evidence…"}</p>
    );
  return (
    <>
      <Link className="back" href="/#opportunities">
        Back to opportunities
      </Link>
      <div className="section">
        <span className={`pill ${d.simulated ? "simulated" : d.status}`}>
          {opportunityLabel(d.status, d.simulated)}
        </span>
        <h1 className="detail-title">
          {d.status === "verified_match"
            ? "Recall matched — review details"
            : d.status === "needs_review"
              ? "Needs information"
              : d.status === "rejected"
                ? "Not affected"
                : d.title}
        </h1>
        {d.simulated ? (
          <div className="simulation">
            SIMULATED CASE — NO REAL CLAIM AVAILABLE
          </div>
        ) : (
          <p className="mono small">
            {d.mode === "replay"
              ? "OFFLINE REPLAY of a real published recall"
              : "LIVE CPSC lookup"}{" "}
            · Observed {new Date(d.source_observed_at).toLocaleString()}
          </p>
        )}
        <h2>{d.title}</h2>
        {d.status === "rejected" && (
          <div className="error">
            {d.matching_reasons.includes("REJECTED — MODEL MISMATCH")
              ? "REJECTED — MODEL MISMATCH"
              : "Official evidence excludes this product"}
          </div>
        )}
        {d.status === "needs_review" && !d.product.product.model_number && (
          <div className="notice">Missing model number</div>
        )}
        <div className="split section">
          <section className="panel">
            <span className="eyebrow">Your purchase</span>
            <h3>{d.product.product.product_name}</h3>
            <p>{d.product.product.brand}</p>
            <strong className="mono">
              {d.product.product.model_number || "Unknown"}
            </strong>
            <p className="small">
              {d.product.product.merchant} ·{" "}
              {d.product.product.date_purchased || "Date unknown"}
            </p>
          </section>
          <section className="panel">
            <span className="eyebrow">Official affected product</span>
            <h3>
              {d.simulated
                ? "Fictional class definition"
                : "CPSC recall " + d.source_id}
            </h3>
            <strong className="mono">
              {d.recall?.models.join(", ") || "DC-EARBUDS-1 — SIMULATION"}
            </strong>
            <p>
              {d.simulated
                ? "Fictional deadline: " + d.deadline_at
                : "Exact model required. Similar names do not establish a match."}
            </p>
          </section>
        </div>
        {d.recall?.safety_instructions && (
          <aside className="notice">
            <strong>Stop use · Battery safety notice</strong>
            <p>{d.recall.instructions}</p>
            <p>{d.recall.safety_instructions}</p>
            <a href={d.official_url} target="_blank" rel="noreferrer">
              Read official safety and remedy instructions
            </a>
          </aside>
        )}
        <section className="section">
          <h2>Hard-condition checks</h2>
          <div className="panel table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Condition</th>
                  <th>Official requirement</th>
                  <th>Your evidence</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {d.assessment.hard_conditions.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td className="mono">{JSON.stringify(c.expected)}</td>
                    <td className="mono">
                      {c.observed === null
                        ? "Unknown"
                        : JSON.stringify(c.observed)}
                    </td>
                    <td>
                      {c.status === "true"
                        ? "Passed"
                        : c.status === "false"
                          ? "Excluded"
                          : "Needs information"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="section">
          <h2>Source evidence</h2>
          <div className="panel">
            {d.evidence.map((e) => (
              <div className="source" key={e.id}>
                {e.source_type === "fixture" ? (
                  <strong>
                    {e.publisher} · {e.url}
                  </strong>
                ) : (
                  <a href={e.url} target="_blank" rel="noreferrer">
                    {e.publisher}
                  </a>
                )}
                <p>{e.quoted_excerpt}</p>
                <div className="small">
                  {e.source_type} · Observed {e.fetched_at}
                </div>
                <div className="small mono">SHA-256 {e.content_sha256}</div>
              </div>
            ))}
          </div>
        </section>
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        {d.status === "verified_match" && !d.simulated && (
          <div className="actions">
            <button disabled={busy} onClick={prepare}>
              Prepare claim packet
            </button>
            <span className="small">
              Potential remedy; user must provide missing evidence.
            </span>
          </div>
        )}
      </div>
    </>
  );
}
