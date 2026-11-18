# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Consumers investigating purchase records for supported recalls and remedies. This redesign also serves hackathon judges watching that workflow, as confirmed by the user.

## Product Purpose

Turn purchase records into evidence-backed next steps. A Scout proposes a finding, a Skeptic challenges it, and a Builder explains the result or asks for missing information.

## Operating Context

Next.js frontend and FastAPI backend. Local development at localhost:3001, API at localhost:8000. The user requested a spectacular hackathon experience across the complete purchase investigation flow and chose code-first construction.

## Capabilities and Constraints

Preserve purchase import, receipt identifier confirmation, supported recall checks, source and provider labels, missing-fact handling, evidence review, local approval, and Markdown export. Public investigations use current sources and never substitute recordings. Internal replay endpoints and fixtures remain available for development. Deterministic checks remain authoritative. No automatic external claim submission, payment, or guarantee of compensation. Sponsor integrations must not be presented as live without actual execution evidence. Public UI excludes synthetic stored purchases and historical recorded cases. The live team uses Agent37 Scout, separate saved Lyzr Reviewer and Builder profiles, and addressed BAND handoffs.

## Brand Commitments

Name: Sueperman. Existing receipt-shaped S logo in apps/web/public/sueperman-receipt-logo.png. User asks for sheer coolness and strong hackathon presentation; no specific palette or typography prescribed.

## Evidence on Hand

Existing working UI and browser workflow tests; bounded live verification and controlled provider fixtures. No winning outcome or measured consumer improvement may be invented.

## Product Principles

- Show findings and their evidence together.
- Make collaboration understandable and its mode explicit.
- Preserve unknowns and user confirmation.
- Approval stays local and bound to current evidence.
