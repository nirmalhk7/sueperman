"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API, api, post, type Collaboration, type TeamDraft, type TeamEvent } from "@/lib/api";

export function TeamStart({ productId }: { productId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function start() {
    setBusy(true);
    setError("");
    try {
      const run = await post<Collaboration>("/collaborations", {
        product_ids: [productId], idempotency_key: crypto.randomUUID(), mode: "live",
      });
      router.push(`/collaborations/${run.id}`);
    } catch (err) { setError((err as Error).message); setBusy(false); }
  }
  return <div className="team-entry">
    <button className="secondary" aria-busy={busy} disabled={busy} onClick={() => void start()}>{busy ? "Opening investigation…" : "Investigate with agent team"}</button>
    <span className="small">Official evidence · three-role investigation</span>
    {error && <p role="alert">{error}</p>}
  </div>;
}

const active = ["queued", "investigating", "challenging", "building"];
export function TeamBoard({ id }: { id: string }) {
  const router = useRouter();
  const [run, setRun] = useState<Collaboration | null>(null);
  const [events, setEvents] = useState<TeamEvent[]>([]);
  const [draft, setDraft] = useState<TeamDraft | null>(null);
  const [answer, setAnswer] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let mounted = true;
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    async function poll() {
      try {
        const [data, timeline] = await Promise.all([
          api<Collaboration>(`/collaborations/${id}`), api<TeamEvent[]>(`/collaborations/${id}/events`),
        ]);
        if (!mounted) return;
        setRun(data); setEvents(timeline);
        if (active.includes(data.status) && Date.now() - started < 95000) timer = setTimeout(poll, 800);
        else if (active.includes(data.status)) setError("Run exceeded expected time. Refresh for partial results.");
      } catch (err) { if (mounted) setError((err as Error).message); }
    }
    void poll();
    return () => { mounted = false; clearTimeout(timer); };
  }, [id]);

  async function act(operation: () => Promise<void>) {
    setBusy(true); setError("");
    try { await operation(); }
    catch (err) {
      setError((err as Error).message);
      setDraft(null); setReviewed(false);
      const current = await api<Collaboration>(`/collaborations/${id}`).catch(() => null);
      if (current) setRun(current);
    } finally { setBusy(false); }
  }
  if (!run) return <><h1>Agent team case</h1><p role={error ? "alert" : "status"}>{error || "Loading case…"}</p></>;
  if (run.demo || run.mode !== "live") return <section className="panel"><h1>Investigation unavailable</h1><p>Start a new investigation from your imported purchases.</p><Link href="/">My purchases</Link></section>;
  const current = run.current && run.revision === run.current_revision;
  return <>
    <section className="case-heading">
      <Link href="/">My purchases</Link>
      <h1>Agent team case</h1>
      <p className={`pill case-status ${run.status}`} data-testid="case-status">{run.status}</p>
      <p>Live investigation · inspect sources and role outcomes</p>
      <p>Case revision {run.revision} · Current revision {run.current_revision}</p>
      {!current && <p role="alert">Historical case. Review current revision before preparing or exporting a draft.</p>}
      {run.warnings.map(w => <p className="error" role="status" key={w}>{w}</p>)}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
    <div className="case-workbench section">
      <section className="case-finding"><h2>Finding</h2><span className="role-credit">Scout / source research</span><p>{run.board.finding || "No completed finding."}</p></section>
      <section className="case-challenge"><h2>Challenge</h2><span className="role-credit">Skeptic / counterexample review</span><p data-testid="challenge">{run.board.challenge || "Challenge unavailable."}</p></section>
      <section className="case-missing"><h2>Missing information</h2>
        <p>{run.board.missing_information?.join(", ") || "No missing hard condition reported. Remedy documents may still be required."}</p>
        {run.board.question_field && run.status === "needs_information" && current && <form onSubmit={e => {
          e.preventDefault();
          void act(async () => {
            const next = await post<Collaboration>(`/collaborations/${id}/answers`, {
              revision: run.revision, field: run.board.question_field, value: answer, confirmed,
              idempotency_key: crypto.randomUUID(),
            });
            router.push(`/collaborations/${next.id}`);
          });
        }}>
          <p>{run.board.question}</p>
          <label>{run.board.question_field.replaceAll("_", " ")}
            <input required maxLength={100} value={answer} onChange={e => { setAnswer(e.target.value); setConfirmed(false); }} />
          </label>
          <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
            I checked this answer against my product or record.</label>
          <button disabled={!confirmed || !answer.trim() || busy}>Send answer</button>
        </form>}
      </section>
      <section className="case-decision"><h2>Decision</h2><span className="role-credit">Deterministic verification</span><p>{run.board.decision || "Unresolved"}</p>
        <p>Deterministic checks control review and export. Local approval sends no claim.</p>
        {run.board.conditions?.map(c => <p key={c.name}><strong>{c.name}</strong>: {c.status}</p>)}
      </section>
    </div>
    <section className="section panel"><h2>Evidence</h2>
      {run.evidence.map(e => <article key={`${e.source_id}-${e.content_sha256}`}>
        <a href={e.url} target="_blank" rel="noreferrer">{e.publisher} · {e.source_id}</a>
        <p>{e.excerpt}</p><p>{e.mode.toUpperCase()} · Observed {new Date(e.fetched_at).toLocaleString()}</p>
        <p className="small mono">Normalized source hash: {e.content_sha256}</p>
      </article>)}
      <p><a href={`${API}/api/collaborations/${id}/history`} target="_blank" rel="noreferrer">Inspect revision and evidence history</a></p>
    </section>
    <section className="section panel case-timeline"><h2>Role timeline</h2>
      <p>Addressed tasks and validated results from this investigation.</p>
      <ol>{events.map(e => <li key={e.id} data-testid={e.kind === "result" ? "role-result" : undefined}>
        <strong>{e.sender} to {e.recipient}</strong> · {e.kind} · {e.task_kind?.replaceAll("_", " ")} · {e.mode} {e.status}
        {e.source_refs.length > 0 && <span> · Sources: {e.source_refs.join(", ")}</span>}
      </li>)}</ol>
    </section>
    {run.status === "ready_for_review" && current && <section className="section panel"><h2>Local remedy draft</h2>
      {!draft ? <button disabled={busy} onClick={() => void act(async () => {
        setDraft(await post<TeamDraft>(`/collaborations/${id}/claim-packet`));
      })}>Prepare claim packet</button> : <>
        <pre style={{ whiteSpace: "pre-wrap" }}>{draft.markdown}</pre>
        <label><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />
          I reviewed this draft and understand approval stays local.</label>
        <button disabled={!reviewed || busy} onClick={() => void act(async () => {
          setDraft(await post<TeamDraft>(`/collaborations/${id}/approve-local`, { confirmed: true }));
        })}>Approve draft locally</button>
        <p>{draft.status === "approved_local" ? "Approved locally" : draft.status}</p>
        <button disabled={busy || !["approved_local", "exported"].includes(draft.status)} onClick={() => void act(async () => {
          const response = await fetch(`${API}/api/collaborations/${id}/export`, { method: "POST" });
          if (!response.ok) { const body = await response.json(); throw new Error(body.message || "Current review required"); }
          const url = URL.createObjectURL(await response.blob());
          const link = document.createElement("a"); link.href = url; link.download = "sueperman-team-draft.md"; link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        })}>Export Markdown</button>
      </>}
    </section>}
    {current && !active.includes(run.status) && <button disabled={busy} onClick={() => void act(async () => {
      const next = await post<Collaboration>("/collaborations", { product_ids: run.product_ids,
        case_id: run.case_id, mode: run.mode, idempotency_key: crypto.randomUUID() });
      router.push(`/collaborations/${next.id}`);
    })}>Review current sources</button>}
  </>;
}
