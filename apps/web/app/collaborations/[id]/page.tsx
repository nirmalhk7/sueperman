"use client";
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { API, api, post, type Collaboration, type TeamEvent } from '@/lib/api';

const active = new Set(['queued', 'investigating', 'challenging', 'building']);
export default function Page() {
  const { id } = useParams<{id: string}>();
  const [c, setCase] = useState<Collaboration | null>(null);
  const [events, setEvents] = useState<TeamEvent[]>([]);
  const [error, setError] = useState('');
  const [value, setValue] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [showPacket, setShowPacket] = useState(false);
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const [data, timeline] = await Promise.all([
          api<Collaboration>(`/collaborations/${id}`), api<TeamEvent[]>(`/collaborations/${id}/events`),
        ]);
        if (cancelled) return;
        setCase(data);
        setEvents(timeline);
        if (active.has(data.status)) timer = setTimeout(load, 700);
      } catch (e) { if (!cancelled) setError((e as Error).message); }
    }
    void load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [id, refresh]);
  async function act(action: string, body: object) {
    setBusy(true); setError('');
    try {
      const data = await post<Collaboration>(`/collaborations/${id}/${action}`, body);
      setCase(data); setRefresh(x => x + 1);
      if (action === 'answers') {setConfirmed(false); setValue(''); setReviewed(false); setShowPacket(false);}
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function download() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`${API}/api/collaborations/${id}/export`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({revision: c?.revision}),
      });
      if (!response.ok) throw new Error('This revision cannot be exported. Refresh and review the current draft.');
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a'); link.href = url; link.download = 'sueperman-team-draft.md'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  if (!c) return <p role={error ? 'alert' : 'status'}>{error || 'Opening case…'}</p>;
  const working = active.has(c.status);
  return <>
    <p><Link className="back" href="/#opportunities">Back to opportunities</Link></p>
    <span className="eyebrow">Scout → Skeptic → Builder</span>
    <h1>Your remedy case</h1>
    <p className="notice">{c.mode === 'replay' ? 'OFFLINE REPLAY — no live sponsor execution' : c.status === 'partial' ? 'PARTIAL TEAM — inspect unavailable or incomplete roles below' : 'LIVE TEAM — sponsor execution evidence requires separate review'}</p>
    <p role="status"><strong>{c.status.replaceAll('_', ' ')}</strong> · Synthetic purchase · Local review only</p>
    {c.warnings.map(w => <p className="notice" key={w}>{w}</p>)}
    {c.blocked_providers.length > 0 && <p>Blocked providers: {c.blocked_providers.join(', ')}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    <div className="split section">
      <section className="panel"><span className="eyebrow">Scout</span><h2>Finding</h2><p>{c.board.finding || 'Waiting for source investigation.'}</p></section>
      <section className="panel"><span className="eyebrow">Skeptic</span><h2>Challenge</h2><p>{c.board.challenge || 'Waiting for a cited challenge.'}</p></section>
    </div>
    <section className="panel section"><span className="eyebrow">Builder</span><h2>Missing information</h2><p>{c.board.missing_information}</p>
      {c.question && !working && <form onSubmit={e => {e.preventDefault(); void act('answers', {revision: c.revision, field: c.question!.field, value, confirmed: true});}}>
        <label>{c.question.field === 'model_number' ? 'Model number' : c.question.field.replaceAll('_', ' ')}<input required maxLength={100} value={value} onChange={e => setValue(e.target.value)} /></label>
        <label className="check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />I checked this fact against the product or record.</label>
        <p className="small">This answer creates a new case revision. Your original purchase stays unchanged. You may leave this question unanswered.</p>
        <button disabled={busy || !confirmed || !value.trim()}>Confirm answer</button>
      </form>}
    </section>
    <section className="section"><h2>Decision</h2><p>{c.board.decision}</p>
      {c.conditions.length > 0 && <div className="panel table-wrap"><table><thead><tr><th>Condition</th><th>Required</th><th>Observed</th><th>Result</th></tr></thead><tbody>{c.conditions.map(condition => <tr key={condition.name}><td>{condition.name}</td><td>{JSON.stringify(condition.expected)}</td><td>{JSON.stringify(condition.observed) ?? 'Unknown'}</td><td>{condition.status === 'true' ? 'Passed' : condition.status === 'false' ? 'Excluded' : 'Unknown'}</td></tr>)}</tbody></table></div>}
    </section>
    <section className="section"><h2>Evidence</h2>{c.board.evidence?.map(e => <article className="panel" key={e.id}><a href={e.url} target="_blank" rel="noreferrer">{e.publisher} · {e.id}</a><p>{e.excerpt}</p><p className="small">{e.mode.toUpperCase()} · Observed {e.fetched_at}</p><p className="mono small">SHA-256 {e.content_sha256}</p></article>)}</section>
    {c.skill.hash && <details className="section"><summary>Challenge skill · {c.skill.identity} · {c.skill.version}</summary><p>{c.skill.mode === 'local_replay' ? 'Local replay checklist — not Finch delivery' : 'Reviewed pinned package — live delivery proof requires separate review'}</p><p className="mono small">SHA-256 {c.skill.hash}</p></details>}
    <section className="section"><h2>Agent timeline</h2><p className="small">{c.mode === 'replay' ? 'Local replay roles exchange addressed requests and validated replies. BAND, Agent37, AdaL, Finch and Lyzr have not executed this replay.' : 'BAND transports addressed requests and replies between the configured Agent37, AdaL and Lyzr roles. The challenge uses the pinned reviewed skill. Completion is not proof of prize qualification.'}</p>
      <ol>{events.map(e => <li className="source" key={e.seq} data-testid="role-event"><strong>{e.sender} → {e.recipient}</strong> · {e.kind} · {e.task_kind.replaceAll('_', ' ')}<p>{e.status} · {e.provider} · {e.mode} · {e.source_refs.join(', ') || 'No source'}</p></li>)}</ol>
    </section>
    {c.status === 'ready_for_review' && c.packet && <section className="section">
      <button onClick={() => setShowPacket(true)}>Prepare claim packet</button>
      {showPacket && <><h2>Review your remedy draft</h2><p>Approval records local review. Required photos and declarations remain your responsibility.</p><div className="panel"><pre>{c.packet.markdown}</pre></div>
        <label className="check"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I reviewed this draft and understand approval stays local.</label>
        {c.approval && <p role="status">Approved locally</p>}
        <div className="actions"><button disabled={!reviewed || busy || !!c.approval} onClick={() => act('approve-local', {revision: c.revision, confirmed: true})}>Approve draft locally</button><button className="secondary" disabled={!c.approval || busy} onClick={download}>Export Markdown</button></div>
      </>}
    </section>}
    <details className="section"><summary>{c.history.length} retained {c.history.length === 1 ? "revision" : "revisions"}</summary>{c.history.map(h => <article className="source" key={h.revision}><p className="mono small">{h.revision}</p><p>{h.created_at} · {h.board?.decision}</p>{h.evidence.map(e => <p key={e.id}><a href={e.url}>{e.id}</a> · {e.content_sha256}</p>)}</article>)}</details>
  </>;
}
