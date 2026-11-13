# Architecture

Sueperman is a local modular monolith: Next.js App Router uses native fetch against FastAPI, which owns SQLite and its bounded typed workflow. No account service, payment engine or external filing exists.

Stages: RECEIVED, PARSED, PRODUCT_NORMALIZED, CANDIDATES_FOUND, SOURCES_VERIFIED, ELIGIBILITY_EVALUATED, PACKET_PREPARED, AWAITING_USER_REVIEW, COMPLETED. Audit transitions are committed before UI polling sees them. Startup marks unfinished runs partial. BackgroundTasks cannot survive process shutdown.

Receipt CSV becomes Pydantic ProductInput, then persistent purchases/products. RecallRecord carries source authority, explicit model list, restrictions and observation timestamp. Exact normalized model equality preserves punctuation and suffixes. Any false restriction rejects; missing facts require review. Recall opportunity and assessment retain hard conditions and evidence. Unknown remedy stays unknown.

Trust boundaries: uploaded files are untrusted data; CSV contents never execute. No model determines eligibility or writes database records. No user URL fetch endpoint. Public sources require deterministic HTTPS host checks; live adapters additionally validate resolved addresses and redirects. Fixture settlements cannot become real claims.

SQLite WAL + foreign keys; UUID entity keys, unique import hashes and run idempotency keys, unique product/kind/source opportunity keys, unique run event sequence. Local packets prefill only known product facts. Required photos/disposal confirmation stay missing. Approval affects local status; export is gated by approval.

Provider adapters are optional and expose mode/provenance. CSV/rules/recorded CPSC make the no-key happy path. Failed live reads must expose fallback labels; manufacturer facts cannot replace CPSC model restrictions. Never accept external page instructions as agent permissions.

P1 adds typed INVESTIGATION_ROUTED and NEEDS_INFO audit events. OpenAI performs the System 1 role with four advisory choices; inspect_more can request bounded official-page research for an ambiguous candidate. It cannot change hard eligibility. The per-run model budget defaults to three calls; budget exhaustion uses labeled rules. Selected/proposed actions and guardrail overrides appear in opportunity details.

Gemini uses a provider-accepted structural JSON schema followed by strict Pydantic date, length and extra-field validation. Extracted model/UPC remain suggestions. Explicit brand/model/UPC review is required before using them; omitted brand stays unknown. Identical receipt hashes return existing imports before another remote call. Corrections to already-checked products require a new import rather than silently invalidating prior evidence.

Verified settlement discovery is intentionally limited to exact Kroger merchant records and one source-reviewed case. Four fixed HTTPS endpoints provide administrator identity/index, class notice and administrator-linked court order. Redirects are rejected; primary PDFs must match reviewed hashes. Every observation retains URL, timestamp and hash. Insurance, geography, transaction type, exclusions and proof remain unknown; only preparation-only information drafts are supported. Expired/unverified/simulated cases cannot use real local-approval/export paths. No claim portal is scraped or submitted.
