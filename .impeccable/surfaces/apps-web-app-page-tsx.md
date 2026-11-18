---
version: 1
slug: "apps-web-app-page-tsx"
primary_target: "apps/web/app/page.tsx"
related_targets: ["apps/web/app/globals.css","apps/web/app/layout.tsx","apps/web/app/components.tsx","apps/web/app/collaborations/team.tsx"]
---

# Consumer workspace

Mode: Operate. Audience: consumers and hackathon judges. Full existing purchase-to-local-export workflow remains authoritative.

## Direction contract

THESIS: Consumer Test Lab makes agent review a tangible evidence workbench. Purchase records, exact identifiers and source comparisons lead; generic marketing cards do not.

OWN-WORLD: Cool off-white work surface, saturated laboratory blue, warm yellow labels, deep blue-black text. Condensed Barlow headings, DM Sans controls, precise ruled records, generous workbench spacing.

STORY: Import purchases, investigate with the agent team, inspect finding versus challenge, answer missing facts, then review and export locally.

FIRST VIEWPORT: Wide left headline and purchase actions face a blue inspection desk on the right. A large typographic agent identity sits above three connected role selectors. Selecting a role changes the explanation with one restrained scanning reveal. On narrow screens the desk follows the actions and all controls remain reachable.

FORM: Consumer Test Lab, grounded candidate 1, explicitly chosen model-pick from seed b2d62a56. Case boards inherit the same workbench, with finding and challenge paired and a distinct decision band. No decorative live claims or invented stats.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Acceptance

- New role preview: click and arrow-key selection change the matching explanation; visibly labeled How it works.
- Existing import/confirmation, imported purchases, exact/negative/unknown cases, local approval and export: existing browser suites.
- Narrow viewport and reduced motion: workspace-design.e2e.ts plus visual captures at 1440, 390 and user viewport 572.
- Regression: frontend tests, lint, typecheck, production build; API suite and browser workflows against isolated synthetic database.
- Changed files: app/globals.css, app/layout.tsx, app/components.tsx, app/collaborations/team.tsx; new components/agent-workbench.tsx, self-hosted fonts and frontend acceptance tests. Other UI selectors may receive scoped presentation classes only if needed for consistent result screens.

## Animation enhancement — November 17, 2026

Focal moment: agent selection moves a shared selection marker; the selected tool is drawn while a bounded inspection scan crosses the role panel. The preview stays explicitly labeled.
Continuity: new purchase rows settle into their records; case findings, challenge and decision receive one short sequential emphasis on arrival. No navigation or controls wait for animation.
Feedback: primary actions expose real pending state and a spinner only while a request is outstanding; pressed controls acknowledge input.
Budget: CSS only, no new dependency, no autonomous preview loop. Inspection sequence <=800ms; list stagger capped at 180ms. Prefer transform, clip and stroke on isolated elements. Reduced motion replaces spatial effects with static selected/pending states and brief color transitions.
Files: components/agent-workbench.tsx, app/globals.css, app/components.tsx, app/collaborations/team.tsx; motion acceptance in tests/motion.e2e.ts.
Verification: expected-failure then passing motion tests, existing preview/mobile and full import/case/export browser regression; lint, typecheck, frontend unit tests, production build; desktop/mobile capture once, optional single fix/confirmation pass. Live provider boundaries verified separately; internal replay endpoints retained.
