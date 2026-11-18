"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  ApiError,
  post,
  type Audit,
  type DiwaliMessage,
  type Health,
  type Imported,
  type Opportunity,
  type Product,
  type Run,
} from "@/lib/api";
import { TeamStart } from "./collaborations/team";
import { opportunityLabel, sourceLabel } from "@/lib/labels";
import { DiwaliAgentTimeline } from "@/components/diwali-agent-timeline";
import { AgentWorkbench } from "@/components/agent-workbench";
import { DeletePurchase } from "@/components/delete-purchase";

export function Opportunities({ items }: { items: Opportunity[] }) {
  items = items.filter(item => !item.demo && !item.simulated && item.mode === "live");
  return (
    <section className="section" id="opportunities">
      <div className="section-head">
        <h2>Opportunities</h2>
        <span className="small">Evidence first. No guaranteed refunds.</span>
      </div>
      {items.length ? (
        <div className="cards">
          {items.map((o) => (
            <article className="card" data-testid="opportunity-card" key={o.id}>
              <span className={`pill ${o.simulated ? "simulated" : o.status}`}>
                {opportunityLabel(o.status, o.simulated)}
              </span>
              <h3>{o.title}</h3>
              <span className="mono small">
                Your model: {o.purchase_model || "not provided"}
              </span>
              <span className="small mono">
                {sourceLabel(o.kind, o.mode, o.simulated, o.status)}
              </span>
              <span className="small">
                Observed {new Date(o.source_observed_at).toLocaleString()}
              </span>
              <Link href={`/opportunities/${o.id}`}>Review details</Link>
            </article>
          ))}
        </div>
      ) : (
        <div className="panel empty">
          Run a check to see source-backed opportunities.
        </div>
      )}
    </section>
  );
}

export function RunResults({ id }: { id: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<Audit[]>([]);
  const [items, setItems] = useState<Opportunity[]>([]);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState<DiwaliMessage[]>([]);
  const [timelineError, setTimelineError] = useState("");
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    async function poll() {
      try {
        const [r, e] = await Promise.all([
          api<Run>(`/runs/${id}`),
          api<Audit[]>(`/runs/${id}/events`),
        ]);
        if (!active) return;
        setRun(r);
        setEvents(e);
        if (r.collaboration_mode && r.collaboration_mode !== "deterministic") {
          try {
            const page = await api<{ items: DiwaliMessage[] }>(`/runs/${id}/agent-messages`);
            if (active) { setMessages(page.items); setTimelineError(""); }
          } catch (err) {
            if (active) setTimelineError((err as Error).message);
          }
        }
        if (["completed", "partial", "failed"].includes(r.status)) {
          const o = await api<Opportunity[]>(`/opportunities?run_id=${id}`);
          if (active) setItems(o);
        } else if (Date.now() - started < 95000) {
          timer = setTimeout(poll, 800);
        } else
          setError(
            "Run exceeded expected time. Refresh to inspect partial results.",
          );
      } catch (err) {
        if (active) setError((err as Error).message);
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id]);
  if (run && (run.demo || (run.mode && run.mode !== "live") || run.source_mode === "recorded" || run.source_mode === "fixture" || Object.values(run.provider_modes).some(mode => /replay|recorded|fixture|simulated/.test(mode)))) {
    return <section className="panel"><h2>Investigation unavailable</h2><p>Start a new check from your imported purchases.</p><Link href="/">My purchases</Link></section>;
  }
  return (
    <>
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      {run && (
        <>
          <section className="section">
            <div className="section-head">
              <h2>
                {run.status === "completed"
                  ? "Run completed"
                  : `Run ${run.status}`}
              </h2>
              <span className="small mono">
                {id.slice(0, 8)} · {run.status}
              </span>
            </div>
            <div className="providers">
              {Object.entries(run.provider_modes).map(([k, v]) => (
                <span key={k}>
                  {k}: {v}
                </span>
              ))}
            </div>
            {run.warnings.map((w) => (
              <div className="notice" key={w}>
                {w}
              </div>
            ))}
            {(run.job?.recoveries ?? 0) > 0 && (
              <p className="notice">Queued work recovered after restart.</p>
            )}
            {Object.keys(run.summary).length > 0 && (
              <div className="stats">
                {[
                  ["Products scanned", "products_scanned"],
                  ["Recall matched", "verified_matches"],
                  ["Needs information", "needs_review"],
                  ["Not affected", "rejected"],
                ].map(([label, key]) => (
                  <div key={key}>
                    <strong>{run.summary[key] || 0}</strong>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
          <DiwaliAgentTimeline run={run} messages={messages} error={timelineError} />
          <Opportunities items={items} />
          <section className="section" id="activity">
            <h2>Activity</h2>
            <div className="panel">
              <ol className="timeline">
                {events.map((e) => (
                  <li key={e.id}>
                    <span className="number">
                      {String(e.seq).padStart(2, "0")}
                    </span>
                    <div>
                      <strong>{e.stage.replaceAll("_", " ")}</strong>
                      <div className="small">
                        {e.provider} · {e.outcome}
                      </div>
                    </div>
                    <time>{new Date(e.timestamp).toLocaleTimeString()}</time>
                  </li>
                ))}
              </ol>
            </div>
          </section>
        </>
      )}
      {!run && !error && <p role="status">Loading run and audit trail…</p>}
    </>
  );
}

function IdentifierReview({ product, onConfirmed, correction = false }: { product: Product; onConfirmed: () => Promise<void>; correction?: boolean }) {
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function confirm(form: FormData) {
    if (!checked || busy) return;
    setBusy(true);
    try {
      await post(`/products/${product.id}/${correction ? "corrections" : "confirm-identifiers"}`, {
        confirmed: true,
        brand: String(form.get("brand") || "").trim() || null,
        model_number: String(form.get("model_number") || "").trim(),
        upc: String(form.get("upc") || "").trim() || null,
      });
      await onConfirmed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form action={confirm}>
      {correction && <p>Current identifiers: {product.product.brand || "Unknown brand"} · {product.product.model_number || "Unknown model"} · {product.product.upc || "Unknown UPC"}. Saving requires a new investigation and local review.</p>}
      <label>Brand (verify)
        <input name="brand" maxLength={100} defaultValue={product.product.brand || ""} />
      </label>
      <label>Model number
        <input name="model_number" required maxLength={100} defaultValue={product.product.model_number || product.product.suggested_identifiers?.model_number || ""} />
      </label>
      <label>UPC (optional)
        <input name="upc" pattern="[0-9]{8,14}" defaultValue={product.product.upc || product.product.suggested_identifiers?.upc || ""} />
      </label>
      <label className="check">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />
        I checked these identifiers against my receipt or product.
      </label>
      <button disabled={!checked || busy}>{correction ? "Save correction" : "Confirm identifiers"}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

export function Dashboard() {
  const [correcting, setCorrecting] = useState("");
  const [correctionMessage, setCorrectionMessage] = useState("");
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [lastRun, setLastRun] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [reimport, setReimport] = useState<{ file: File; token: string } | null>(null);
  const [confirmReimport, setConfirmReimport] = useState(false);
  async function refresh() {
    setProducts((await api<Product[]>("/products")).filter(p => !p.demo));
  }
  useEffect(() => {
    void api<Product[]>("/products")
      .then((p) => {
        setProducts(p.filter(product => !product.demo));
        setLastRun(localStorage.getItem("sueperman-last-run") || "");
      })
      .catch((e) => setError(e.message));
    void api<Health>("/health")
      .then(setHealth)
      .catch(() => {});
  }, []);
  async function upload(file: File, token?: string) {
    setBusy(true);
    setError("");
    setReimport(null); setConfirmReimport(false);
    setUploadMessage(file.type.startsWith("image/") || file.type === "application/pdf"
      ? "Reading receipt…" : "Importing purchases…");
    try {
      const form = new FormData();
      form.append("file", file);
      if (token) form.append("reimport_confirmation", token);
      await api<Imported>("/uploads/purchases", { method: "POST", body: form });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof ApiError && e.details.code === "REIMPORT_CONFIRMATION_REQUIRED" && e.details.reimport_token) {
        setReimport({ file, token: e.details.reimport_token });
      }
    } finally {
      setUploadMessage("");
      setBusy(false);
    }
  }
  async function start() {
    setBusy(true);
    setError("");
    try {
      const r = await post<Run>("/runs", {
        purchase_ids: products.map((p) => p.purchase_id),
        mode: "live",
        allow_recorded_fallback: false,
        idempotency_key: crypto.randomUUID(),
      });
      localStorage.setItem("sueperman-last-run", r.run_id);
      router.push(`/runs/${r.run_id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <h1>Find recalls and settlements <span>hiding in your</span> purchase history.</h1>
          <p>
            Turn forgotten orders into evidence-backed next steps. Check
            official recalls, understand what applies, and review a remedy draft
            before taking action.
          </p>
          <div className="actions hero-actions">
            <button aria-busy={busy} disabled={busy || !products.length} onClick={start}>
              Check my purchases
            </button>
          </div>
          <details className="coverage"><summary>Supported recall coverage</summary><p className="small">Automatic verification covers NEWDERY 26-792, plus Flaunt 26-610, iStore 25-390 and Baseus 25-248 when reviewed coverage is enabled. Baseus requires the exact model and a complete serial number in the CSV. Other notices or missing restrictions require review.</p></details>
        </div>
        <AgentWorkbench />
      </section>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <section className="section" id="purchases">
        {correctionMessage && <p role="status">{correctionMessage}</p>}
        <div className="section-head">
          <h2>
            My purchases{" "}
            <span className="small">/ {products.length} items</span>
          </h2>
          <span className="small">CSV · Receipt photo · PDF · Up to 10MB</span>
        </div>
        <div
          className="upload"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files[0];
            if (f && !busy) void upload(f);
          }}
        >
          <label htmlFor="csv">
            <strong>Drop your purchase history here</strong>
            <span className="small">
              {" "}
              — or choose a CSV or receipt. Uncertain identifiers stay
              uncertain.
            </span>
          </label>
          <input
            id="csv"
            aria-label="Upload purchases or receipt"
            type="file"
            accept=".csv,.png,.jpg,.jpeg,.pdf"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) void upload(f);
            }}
          />
          <div className="receipt-upload">
            <label htmlFor="receipt-camera"><strong>Take receipt photo</strong></label>
            <p className="small">
              Use your phone’s rear camera, or choose a saved JPEG or PNG photo.
              Capture the whole receipt in good light. We read visible text;
              review the merchant, date and items before checking purchases.
            </p>
            <input
              id="receipt-camera"
              aria-label="Take receipt photo"
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (f) void upload(f);
              }}
            />
          </div>
          {uploadMessage && <p role="status">{uploadMessage}</p>}
          {reimport && <div role="group" aria-label="Confirm fresh import">
            <p>This file contains previously deleted purchases. Importing again recreates them. Receipt files will be read again and normal usage limits apply.</p>
            <label><input type="checkbox" checked={confirmReimport} onChange={event => setConfirmReimport(event.target.checked)} /> I want to import this previously deleted file again</label>
            <div className="actions">
              <button disabled={busy || !confirmReimport} onClick={() => upload(reimport.file, reimport.token)}>Import again</button>
              <button disabled={busy} onClick={() => { setReimport(null); setConfirmReimport(false); setError(""); }}>Cancel import</button>
            </div>
          </div>}
        </div>
        {products.length > 0 && (
          <div className="panel table-wrap section">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Model / identifier</th>
                  <th>Purchased</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr data-testid="purchase-row" data-product-id={p.id} key={p.id}>
                    <td>
                      <strong>{p.product.product_name}</strong>
                      <span className="small">
                        {p.product.brand} · {p.product.merchant}
                      </span>
                      <TeamStart productId={p.id} />
                      <DeletePurchase purchaseId={p.purchase_id} onDeleted={async () => {
                        localStorage.removeItem("sueperman-last-run"); setLastRun("");
                        await refresh(); setCorrectionMessage("Purchase and associated local records deleted.");
                      }} />
                    </td>
                    <td className="mono">
                      {p.product.model_number || "Missing model number"}
                      {p.product.suggested_identifiers?.model_number && !p.product.user_confirmed_identifiers && (
                        <div className="small">
                          Unverified scan:{" "}
                          {p.product.suggested_identifiers.model_number}
                        </div>
                      )}
                      {correcting === p.id ? <IdentifierReview product={p} correction onConfirmed={async () => { await refresh(); setCorrecting(""); setCorrectionMessage("Purchase corrected. Check my purchases to investigate the new revision."); }} /> : p.product.user_confirmed_identifiers ? (
                        <p className="small">Identifiers confirmed by you</p>
                      ) : ["image", "pdf"].includes(p.source_type || "") ? (
                        <IdentifierReview product={p} onConfirmed={refresh} />
                      ) : null}
                      <button onClick={() => setCorrecting(p.id)}>Correct identifiers</button>
                    </td>
                    <td>{p.product.date_purchased || "Unknown"}</td>
                    <td>
                      <span className="pill">
                        {["image", "pdf"].includes(p.source_type || "") ? "Receipt extraction" : "CSV upload"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {busy && <p role="status">Processing…</p>}
      </section>
      <details className="section panel">
        <summary>Connected services</summary>
        <p>Investigations use current official sources. Unavailable services are reported without substituting recorded results.</p>
        <div className="providers section">
          {health?.providers.map((p) => (
            <span key={p.name}>
              {p.name}: {p.enabled ? "enabled" : "disabled"} /{" "}
              {p.configured ? "configured" : "no credentials"}
            </span>
          ))}
        </div>
      </details>
      {lastRun && <RunResults id={lastRun} />}
    </>
  );
}
