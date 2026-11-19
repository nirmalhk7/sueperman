"use client";

import { useState } from "react";
import { post, type Product } from "@/lib/api";

export function IdentifierReview({ product, onConfirmed, correction = false }: { product: Product; onConfirmed: () => Promise<void>; correction?: boolean }) {
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function confirm(form: FormData) {
    if (!checked || busy) return;
    setBusy(true);
    setError("");
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
