"use client";

import { useEffect, useState } from "react";
import { api, type CaseHistory } from "@/lib/api";

export function CaseHistoryPanel({ id, currentRevision }: { id: string; currentRevision: number }) {
  const [history, setHistory] = useState<CaseHistory | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const request = new AbortController();
    void api<CaseHistory>(`/collaborations/${id}/history`, { signal: request.signal })
      .then(setHistory)
      .catch(() => { if (!request.signal.aborted) setError(true); });
    return () => request.abort();
  }, [id]);

  if (error) return <p role="alert">Couldn’t load case history. Close and reopen this section to try again.</p>;
  if (!history) return <p role="status">Loading case history…</p>;
  const snapshots = history.snapshots.filter(snapshot => snapshot.mode === "live");
  return <div className="section">
    <h3>Case revisions</h3>
    {history.revisions.length ? <ol>
      {history.revisions.map(revision => <li key={revision.revision}>
        Revision {revision.revision}{revision.revision === currentRevision ? " (current)" : ""}
        {" · "}{new Date(revision.created_at).toLocaleString()}
      </li>)}
    </ol> : <p>No revisions have been recorded.</p>}
    <h3>Evidence snapshots</h3>
    {snapshots.length ? snapshots.map(snapshot => <article className="source" key={`${snapshot.source_id}-${snapshot.fetched_at}-${snapshot.content_sha256}`}>
      <a href={snapshot.url} target="_blank" rel="noreferrer">{snapshot.publisher} · {snapshot.source_id}</a>
      <p className="small">Observed {new Date(snapshot.fetched_at).toLocaleString()}</p>
      <p>{snapshot.excerpt}</p>
      <p className="small mono">Source fingerprint: {snapshot.content_sha256}</p>
    </article>) : <p>No live evidence has been saved for this case.</p>}
  </div>;
}
