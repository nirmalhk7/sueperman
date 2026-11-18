"use client";

import { useState } from "react";
import { api, post } from "@/lib/api";

interface Preview {
  binding: string;
  shared_investigations: number;
  investigations: number;
  other_drafts_requiring_new_check: number;
  active: boolean;
  blocked_reason: string | null;
}

export function DeletePurchase({ purchaseId, onDeleted }: { purchaseId: string; onDeleted: () => Promise<void> }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [shared, setShared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function review() {
    setBusy(true); setError(""); setConfirmed(false); setShared(false);
    try {
      setPreview(await api<Preview>(`/purchases/${purchaseId}/deletion-preview`));
    } catch (cause) { setError((cause as Error).message); }
    finally { setBusy(false); }
  }

  async function remove() {
    if (!preview) return;
    setBusy(true); setError("");
    try {
      await post(`/purchases/${purchaseId}/delete`, { confirmed: true,
        expected_binding: preview.binding, shared_history_confirmed: shared });
      await onDeleted();
    } catch (cause) {
      setError((cause as Error).message);
      setConfirmed(false); setShared(false);
    } finally { setBusy(false); }
  }

  return <div className="section">
    {!preview ? <button disabled={busy} onClick={review}>Delete purchase</button> :
      <div role="group" aria-label="Review purchase deletion">
        <p>This permanently removes this purchase, every identifier revision, findings, drafts, local evidence and source watches.</p>
        <p>Shared workspace: this removes local records for everyone using this demo. Private accounts are not enabled.</p>
        <p>Backups normally expire after seven days. The last valid recovery copy may be kept longer during an outage; restores reapply deletions. Minimal deletion identifiers and file hashes remain to prevent recovery or delayed uploads from recreating records. Files you downloaded and records held by external providers are outside this deletion.</p>
        {preview.shared_investigations > 0 && <p>{preview.shared_investigations} shared investigation histories will also be removed. Other purchases and their findings remain.</p>}
        {preview.other_drafts_requiring_new_check > 0 && <p>{preview.other_drafts_requiring_new_check} drafts for other purchases depend on this history and will require a fresh check and approval.</p>}
        {preview.active && <p role="status">{preview.blocked_reason}</p>}
        <label><input type="checkbox" checked={confirmed} disabled={busy || preview.active} onChange={event => setConfirmed(event.target.checked)} /> I understand this permanently deletes this purchase and its local records</label>
        {preview.shared_investigations > 0 && <label><input type="checkbox" checked={shared} disabled={busy || preview.active} onChange={event => setShared(event.target.checked)} /> I also agree to remove these shared investigation histories</label>}
        <div className="actions">
          <button disabled={busy || preview.active || !confirmed || (preview.shared_investigations > 0 && !shared)} onClick={remove}>Delete permanently</button>
          <button disabled={busy} onClick={review}>Refresh deletion preview</button>
          <button disabled={busy} onClick={() => { setPreview(null); setError(""); }}>Cancel deletion</button>
        </div>
      </div>}
    {error && <p role="alert">{error}</p>}
  </div>;
}
