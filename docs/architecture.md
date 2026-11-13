# Architecture

Sueperman is a local modular monolith: Next.js App Router uses native fetch against FastAPI, which owns SQLite and its bounded typed workflow. No account service, payment engine or external filing exists.

Stages: RECEIVED, PARSED, PRODUCT_NORMALIZED, CANDIDATES_FOUND, SOURCES_VERIFIED, ELIGIBILITY_EVALUATED, PACKET_PREPARED, AWAITING_USER_REVIEW, COMPLETED. Audit transitions are committed before UI polling sees them. Startup marks unfinished runs partial. BackgroundTasks cannot survive process shutdown.

Receipt CSV becomes Pydantic ProductInput, then persistent purchases/products. RecallRecord carries source authority, explicit model list, restrictions and observation timestamp. Exact normalized model equality preserves punctuation and suffixes. Any false restriction rejects; missing facts require review. Recall opportunity and assessment retain hard conditions and evidence. Unknown remedy stays unknown.

Trust boundaries: uploaded files are untrusted data; CSV contents never execute. No model determines eligibility or writes database records. No user URL fetch endpoint. Public sources require deterministic HTTPS host checks; live adapters additionally validate resolved addresses and redirects. Fixture settlements cannot become real claims.

SQLite WAL + foreign keys; UUID entity keys, unique import hashes and run idempotency keys, unique product/kind/source opportunity keys, unique run event sequence. Local packets prefill only known product facts. Required photos/disposal confirmation stay missing. Approval affects local status; export is gated by approval.

Provider adapters are optional and expose mode/provenance. CSV/rules/recorded CPSC make the no-key happy path. Failed live reads must expose fallback labels; manufacturer facts cannot replace CPSC model restrictions. Never accept external page instructions as agent permissions.
