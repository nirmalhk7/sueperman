"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  api,
  post,
  type Audit,
  type Health,
  type Imported,
  type Opportunity,
  type Product,
  type Run,
} from "@/lib/api";
import { opportunityLabel, sourceLabel } from "@/lib/labels";

export function Opportunities({ items }: { items: Opportunity[] }) {
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
                {sourceLabel(o.kind, o.mode, o.simulated)}
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

function IdentifierReview({ product, onConfirmed }: { product: Product; onConfirmed: () => Promise<void> }) {
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function confirm(form: FormData) {
    if (!checked || busy) return;
    setBusy(true);
    try {
      await post(`/products/${product.id}/confirm-identifiers`, {
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
      <label>Brand (verify)
        <input name="brand" maxLength={100} defaultValue={product.product.brand || ""} />
      </label>
      <label>Model number
        <input name="model_number" required maxLength={100} defaultValue={product.product.suggested_identifiers?.model_number || ""} />
      </label>
      <label>UPC (optional)
        <input name="upc" pattern="[0-9]{8,14}" defaultValue={product.product.suggested_identifiers?.upc || ""} />
      </label>
      <label className="check">
        <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />
        I checked these identifiers against my receipt or product.
      </label>
      <button disabled={!checked || busy}>Confirm identifiers</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

export function Dashboard() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [lastRun, setLastRun] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"demo" | "live">("demo");
  async function refresh() {
    setProducts(await api<Product[]>("/products"));
  }
  useEffect(() => {
    void api<Product[]>("/products")
      .then((p) => {
        setProducts(p);
        setLastRun(localStorage.getItem("sueperman-last-run") || "");
      })
      .catch((e) => setError(e.message));
    void api<Health>("/health")
      .then(setHealth)
      .catch(() => {});
  }, []);
  async function demo() {
    setBusy(true);
    setError("");
    try {
      const imported = await post<Imported>("/demo/reset");
      localStorage.removeItem("sueperman-last-run");
      setLastRun("");
      const all = await api<Product[]>("/products");
      setProducts(all.filter((p) => imported.product_ids.includes(p.id)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function upload(file: File) {
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api<Imported>("/uploads/purchases", { method: "POST", body: form });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function start() {
    setBusy(true);
    setError("");
    try {
      const r = await post<Run>("/runs", {
        purchase_ids: products.map((p) => p.purchase_id),
        mode,
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
        <div>
          <span className="eyebrow">Your purchases. Your rights.</span>
          <h1>Find recalls and settlements hiding in your purchase history.</h1>
          <p>
            Turn forgotten orders into evidence-backed next steps. Check
            official recalls, understand what applies, and review a remedy draft
            before taking action.
          </p>
          <div className="actions">
            <button disabled={busy || !products.length} onClick={start}>
              Check my purchases
            </button>
            <button className="secondary" disabled={busy} onClick={demo}>
              Try demo data
            </button>
          </div>
        </div>
        <aside className="hero-aside">
          <strong>Evidence, first.</strong>
          <p>
            Exact product identifiers.
            <br />
            Official sources.
            <br />
            Your approval, always.
          </p>
        </aside>
      </section>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <section className="section" id="purchases">
        <div className="section-head">
          <h2>
            My purchases{" "}
            <span className="small">/ {products.length} items</span>
          </h2>
          <span className="small">CSV · Up to 10MB · No account needed</span>
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
              if (f) void upload(f);
            }}
          />
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
                    </td>
                    <td className="mono">
                      {p.product.model_number || "Missing model number"}
                      {p.product.suggested_identifiers?.model_number && !p.product.user_confirmed_identifiers && (
                        <div className="small">
                          Unverified scan:{" "}
                          {p.product.suggested_identifiers.model_number}
                        </div>
                      )}
                      {p.product.user_confirmed_identifiers ? (
                        <p className="small">Identifiers confirmed by you</p>
                      ) : ["image", "pdf"].includes(p.source_type || "") ? (
                        <IdentifierReview product={p} onConfirmed={refresh} />
                      ) : null}
                    </td>
                    <td>{p.product.date_purchased || "Unknown"}</td>
                    <td>
                      <span className="pill">
                        {p.demo ? "Synthetic demo" : ["image", "pdf"].includes(p.source_type || "") ? "Receipt extraction" : "CSV upload"}
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
        <summary>Demo controls & provider health</summary>
        <p>
          Recorded sources work without paid keys. Live calls require explicit
          backend flags; unavailable providers are labeled.
        </p>
        <label>
          Run mode{" "}
          <select
            aria-label="Run mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as "demo" | "live")}
          >
            <option value="demo">Offline replay</option>
            <option value="live">Live APIs with labeled fallback</option>
          </select>
        </label>
        <div className="actions">
          <button className="secondary" disabled={busy} onClick={demo}>
            Reset demo purchases
          </button>
        </div>
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
