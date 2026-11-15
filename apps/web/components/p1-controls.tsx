"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, post } from "@/lib/api";

type Readiness = {
  binding: string;
  eligible: boolean;
  previous_versions: number;
  items: { id: string; label: string; ready: boolean; confirmed_at: string | null }[];
};
type PublicRecord = { models: string[]; excerpt: string; instructions: string };
type SourceCheck = { id: string; sequence: number; status: string; observed_at: string;
  before: PublicRecord; after: PublicRecord | null };
type Monitor = { enabled: boolean; available: boolean; status: string; interval_hours: number;
  next_check_at: string | null; checks: SourceCheck[] };

export function EvidenceReadiness({ packetId, onChanged, onPending }: {
  packetId: string; onChanged: () => Promise<void>; onPending: (pending: boolean) => void;
}) {
  const [state, setState] = useState<Readiness | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState<{ id: string; ready: boolean } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void api<{ enabled: boolean }>("/p1/status", { signal: controller.signal }).then(async capability => {
      if (capability.enabled) setState(await api<Readiness>(`/claim-packets/${packetId}/obligations`, {
        signal: controller.signal,
      }));
    }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [packetId]);
  async function change(id: string, ready: boolean) {
    if (!state) return;
    setPending({ id, ready }); onPending(true); setSaved(false); setError("");
    try {
      setState(await post<Readiness>(`/claim-packets/${packetId}/obligations`, {
        binding: state.binding, item_id: id, ready, confirmed: true,
      }));
      await onChanged();
      setSaved(true);
    } catch (e) { setError((e as Error).message); }
    finally { setPending(null); onPending(false); }
  }
  if (!state && !error) return null;
  return <section className="section panel" data-testid="evidence-readiness">
    <h2>Evidence readiness</h2>
    <p>Track what you have ready locally. These are self-reported preparation notes, not verified proof or declarations.</p>
    {state && <>
      {!state.eligible && <p role="status">Current source or purchase requires a new review. Readiness updates are paused.</p>}
      {state.previous_versions > 0 && <p>Earlier readiness belongs to a previous version and has been reset.</p>}
      {!state.items.length && <p>No document checklist is available for this draft.</p>}
      {state.items.map(item => <label className="check" key={item.id}>
        <input type="checkbox" checked={pending?.id === item.id ? pending.ready : item.ready}
          disabled={!!pending || !state.eligible} onChange={e => void change(item.id, e.target.checked)} />
        I have this ready locally: {item.label}
      </label>)}
    </>}
    {pending && <p role="status">Saving readiness…</p>}
    {saved && <p role="status" data-testid="readiness-saved">Readiness saved locally</p>}
    {error && <p role="alert">Evidence checklist unavailable: {error}</p>}
    <p className="small">Changing readiness requires a new local approval before export. Required documents remain your responsibility.</p>
  </section>;
}

export function SourceMonitor({ opportunityId, onChanged }: {
  opportunityId: string; onChanged: () => Promise<void>;
}) {
  const [state, setState] = useState<Monitor | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const lastCheck = useRef("");
  const accept = useCallback(async (next: Monitor) => {
    setState(next);
    const check = next.checks.at(-1);
    if (check && check.id !== lastCheck.current) {
      lastCheck.current = check.id;
      if (["changed", "unavailable", "stale"].includes(check.status)) await onChanged();
    }
  }, [onChanged]);
  const enabled = state?.enabled;
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const capability = await api<{ enabled: boolean }>("/p1/status", { signal: controller.signal });
        if (capability.enabled) await accept(await api<Monitor>(`/opportunities/${opportunityId}/source-monitor`, {
          signal: controller.signal,
        }));
      } catch (e) { if (!controller.signal.aborted) setError((e as Error).message); }
    }
    void load();
    const timer = enabled ? setInterval(() => void load(), 2000) : null;
    return () => { controller.abort(); if (timer) clearInterval(timer); };
  }, [opportunityId, enabled, accept]);
  async function toggle() {
    if (!state) return;
    setBusy(true); setError("");
    try { await accept(await post<Monitor>(`/opportunities/${opportunityId}/source-monitor`, { enabled: !state.enabled })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  if (!state && !error) return null;
  const latest = state?.checks.at(-1);
  return <section className="section panel" data-testid="source-monitor">
    <h2>Source monitoring</h2>
    <p>Optional daily checks of this official public recall. A changed or unavailable source revokes local approval.</p>
    {state && <>
      {!state.available && <p>Scheduled public reads are unavailable. The operator must enable monitoring.</p>}
      <button className="secondary" disabled={busy || (!state.available && !state.enabled)} onClick={() => void toggle()}>
        {state.enabled ? "Disable source checks" : "Enable daily source checks"}
      </button>
      {state.next_check_at && <p>Next check: {new Date(state.next_check_at).toLocaleString()}</p>}
      {latest ? <p data-testid="monitor-result">Last result: {latest.status}</p> : <p>No source checks recorded yet.</p>}
      {latest?.status === "changed" && <p role="status">Source changed — review required</p>}
      {latest?.status === "unavailable" && <p role="status">Source unavailable — prior evidence only. Run a fresh investigation before review.</p>}
      {latest?.status === "stale" && <p role="status">Source check superseded — review current sources before approving again.</p>}
      {state.status === "interrupted" && <p>Source check interrupted. Review sources before enabling it again.</p>}
      <div data-testid="source-history">{state.checks.map(check => <details key={check.id}>
        <summary>Check {check.sequence}: {check.status} · {new Date(check.observed_at).toLocaleString()}</summary>
        <p>Previous affected models: {check.before.models.join(", ") || "Unknown"}</p>
        <p>Previous source: {check.before.excerpt}</p>
        {check.after ? <>
          <p>Current affected models: {check.after.models.join(", ") || "Unknown"}</p>
          <p>Current source: {check.after.excerpt}</p>
          {check.after.instructions !== check.before.instructions && <p>Updated remedy instructions: {check.after.instructions}</p>}
        </> : <p>No current source observation; previous snapshot retained.</p>}
      </details>)}</div>
    </>}
    {error && <p role="alert">Source monitoring unavailable: {error}</p>}
  </section>;
}
