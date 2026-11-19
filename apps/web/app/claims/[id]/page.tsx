"use client";
import { useCallback, useEffect, useState } from "react";
import { EvidenceReadiness } from "@/components/p1-controls";
import { RemedyDraft } from "@/components/remedy-draft";
import Link from "next/link";
import { useParams } from "next/navigation";
import { API, api, post, type Packet } from "@/lib/api";
export default function Page() {
  const { id } = useParams<{ id: string }>();
  const [p, setP] = useState<Packet | null>(null);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [readinessBusy, setReadinessBusy] = useState(false);
  const readinessChanged = useCallback(async () => {
    setP(await api<Packet>(`/claim-packets/${id}`));
    setChecked(false);
  }, [id]);
  useEffect(() => {
    void api<Packet>(`/claim-packets/${id}`)
      .then(setP)
      .catch((e) => setError(e.message));
  }, [id]);
  async function approve() {
    setBusy(true);
    try {
      setP(
        await post<Packet>(`/claim-packets/${id}/approve-local`, {
          confirmed: true,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function download() {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/claim-packets/${id}/export`, {
        method: "POST",
      });
      if (!r.ok)
        throw new Error("Export unavailable; reload the draft and review current requirements before approving again.");
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "sueperman-draft.md";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setP(await api<Packet>(`/claim-packets/${id}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!p)
    return (
      <p role={error ? "alert" : "status"}>{error || "Loading packet…"}</p>
    );
  if (p.demo || p.mode !== "live") return <section className="panel"><h1>Investigation unavailable</h1><p>Start a new check from your imported purchases.</p><Link href="/">My purchases</Link></section>;
  const approved = ["approved_local", "exported"].includes(p.status);
  const blocked = p.status === "needs_evidence" || p.verification_status === "unavailable";
  return (
    <>
      <span className="eyebrow">Your review comes first</span>
      <h1>Review your remedy draft.</h1>
      <p className="mono small">
        {p.verification_status === "unavailable"
          ? "SETTLEMENT VERIFICATION UNAVAILABLE — PRIOR DRAFT ONLY"
          : p.kind === "settlement" ? "LIVE verified settlement sources" : "LIVE CPSC source"}
      </p>
      <div className="notice">
        <strong>Local draft only</strong>
        {blocked && <p>Run another live check to verify official sources before approving or exporting this draft.</p>}
        <p>
          Approval saves your review locally. It does not contact a manufacturer
          or submit a claim. Required documents and declarations remain your
          responsibility.
        </p>
      </div>
      <RemedyDraft markdown={p.markdown} facts={p.completed_fields} />
      {p.kind !== "settlement" && <EvidenceReadiness packetId={id} onChanged={readinessChanged} onPending={setReadinessBusy} />}
      <section className="section">
        <h2>Evidence still needed</h2>
        <ul>
          {p.missing_documents.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
        {p.contact_or_portal_url && (
          <a href={p.contact_or_portal_url} target="_blank" rel="noreferrer">
            Official program page — review independently
          </a>
        )}
        <label className="check">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          I reviewed this draft and understand approval stays local.
        </label>
        {approved && (
          <p role="status">
            <strong>Approved locally</strong>
          </p>
        )}
        {error && (
          <div role="alert" className="error">
            {error}
            <button type="button" className="secondary" onClick={() => window.location.reload()}>
              Reload draft
            </button>
          </div>
        )}
        <div className="actions">
          <button onClick={approve} disabled={!checked || busy || readinessBusy || approved || blocked}>
            Approve draft locally
          </button>
          <button
            className="secondary"
            onClick={download}
            disabled={!approved || busy || readinessBusy || blocked}
          >
            Export Markdown
          </button>
        </div>
      </section>
    </>
  );
}
