export const API =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}/api${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message || "Service unavailable. Please retry.");
  }
  return response.json();
}
export function post<T>(path: string, body?: unknown): Promise<T> {
  return api<T>(path, {
    method: "POST",
    ...(body
      ? {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {}),
  });
}
export interface ProductFacts {
  product_name: string;
  brand: string | null;
  model_number: string | null;
  merchant: string | null;
  date_purchased: string | null;
  order_reference_redacted: string | null;
  suggested_identifiers?: Record<string, string>;
}
export interface Product {
  id: string;
  purchase_id: string;
  product: ProductFacts;
  demo: boolean;
}
export interface Opportunity {
  id: string;
  title: string;
  product_id: string;
  source_id: string;
  purchase_model?: string | null;
  kind: string;
  status: string;
  official_url: string;
  source_observed_at: string;
  simulated: boolean;
  mode: string;
  matching_reasons: string[];
  deadline_at?: string;
  recall?: {
    models: string[];
    safety_instructions: string;
    instructions: string;
    contact_url: string;
  };
}
export interface Evidence {
  id: string;
  url: string;
  publisher: string;
  fetched_at: string;
  source_type: string;
  quoted_excerpt: string;
  content_sha256: string;
}
export interface Condition {
  name: string;
  expected: unknown;
  observed: unknown;
  status: string;
}
export interface Detail extends Opportunity {
  product: Product;
  evidence: Evidence[];
  assessment: {
    outcome: string;
    hard_conditions: Condition[];
    missing_fields: string[];
  };
}
export interface Run {
  run_id: string;
  status: string;
  summary: Record<string, number>;
  provider_modes: Record<string, string>;
  warnings: string[];
  opportunities: string[];
}
export interface Audit {
  id: string;
  seq: number;
  stage: string;
  provider: string;
  outcome: string;
  timestamp: string;
  source_refs: string[];
}
export interface Packet {
  id: string;
  status: string;
  markdown: string;
  mode: string;
  missing_documents: string[];
  contact_or_portal_url: string | null;
}
export interface Imported {
  purchase_ids: string[];
  product_ids: string[];
  parse_warnings: string[];
}
export interface Health {
  db: string;
  demo_ready: boolean;
  providers: { name: string; enabled: boolean; configured: boolean }[];
}
