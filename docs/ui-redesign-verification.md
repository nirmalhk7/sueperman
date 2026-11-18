# Consumer Test Lab UI verification

November 17, 2026, America/Los_Angeles.

## Scope and acceptance

- Full demo flow remains: purchase import and identifier confirmation, supported recall investigation, agent case board, missing-fact answers, evidence, local approval and Markdown export. Existing workflow, collaboration, corrections, receipt and stale-packet browser suites exercise these paths.
- New agent-role preview switches explanations through click and arrow/Home/End keys, uses tab semantics, and labels itself a workflow preview. `tests/workspace-design.e2e.ts` checks selection, explanation and keyboard focus.
- Narrow-screen and reduced-motion acceptance checks page overflow and usable controls. Desktop (1440), mobile (390), and in-app panel (572) captures were inspected, plus desktop/mobile case captures.
- No sponsor execution, recovery, eligibility, compensation or hackathon outcome claims added. Existing offline labels and deterministic gates retained.

## Red / green

Before implementation:

`WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/workspace-design.e2e.ts --timeout=15000`

Two expected failures: the agent-preview region did not exist; Builder selection was unavailable.

After implementation:

`WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/workspace-design.e2e.ts --timeout=20000`

Two passed. Full browser rerun below includes the same checks and screenshot instrumentation.

## Final checks

- `pnpm --dir apps/web test`: 12 passed.
- `pnpm --dir apps/web lint`: passed.
- `pnpm --dir apps/web typecheck`: passed.
- `node node_modules/eslint/bin/eslint.js components/agent-workbench.tsx` from `apps/web`: passed. This explicitly covers the new component directory outside the repository lint script's paths.
- `pnpm --dir apps/web build`: production build passed.
- `WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test --timeout=45000`: 15 passed, 3 opt-in paid live-provider tests skipped. Browser tests used a disposable SQLite database `/tmp/sueperman-design-acceptance.db`; paid providers were disabled. Original API/database restored afterward.
- `WEB_URL=http://localhost:3001 pnpm --dir apps/web exec playwright test tests/collaboration.e2e.ts --timeout=45000`: 2 passed after adding desktop/mobile case capture instrumentation.
- Impeccable detector over all five changed UI sources: no findings.
- Independent Impeccable finish reviewer: `ship`; all five requested viewport/case captures valid, no material fixes.
- `git diff --check`: passed.

## Broader regression

`services/api/.venv/bin/pytest services/api/tests -q`: 438 passed, one P1 browser harness timed out. Its evidence includes Chromium launch timeout in the sandbox. No source change was made to bypass or weaken this check. Targeted rerun with browser access: `services/api/.venv/bin/pytest services/api/tests/p1/test_p1_browser.py -q` passed (1 harness test, containing 4 passing browser scenarios) in 95.88 seconds. The existing Starlette TestClient deprecation warning remains. All 439 collected backend-suite tests are accounted for across the full run and this targeted rerun.

## Evidence and limits

Captures: `.impeccable/review/desktop.png`, `mobile.png`, `user-572.png`, `case.png`, `case-mobile.png`. Code-first direction has no approved image comp; review makes no fidelity-to-comp claim. Existing receipt logo is preserved; font sources and licenses are in `apps/web/public/fonts/`.

Only local development is delivered by this work. Live sponsor execution and paid-provider end-to-end checks are outside this redesign's verification.

Design documentation: `DESIGN.md` and `.impeccable/design.json` created from the implemented system; root reviewed both. Existing non-UI work was not reverted.

## Animation enhancement verification

November 17, 2026. Preserved the Consumer Test Lab visual system; added shared role-marker movement, single inspection sweep, tool-icon drawing, role-copy reveal, bounded record/case arrivals, press feedback and real `aria-busy` indicators. No autonomous preview loop. Reduced motion removes spatial, clipping and stroke animation while preserving static selected/pending states and brief color feedback.

Red: `WEB_URL=http://localhost:3001 /opt/homebrew/bin/node node_modules/@playwright/test/cli.js test tests/motion.e2e.ts --timeout=15000` from `apps/web` failed as expected for the absent selection marker and missing busy attribute. Green: the same suite plus `tests/workspace-design.e2e.ts --timeout=20000` passed all 5 checks after implementation. During green verification, the new error assertion was narrowed to the app's alert rather than Next.js's additional route announcer; a TypeScript guard uses `KeyframeEffect` before reading keyframes.

Final frontend verification from `apps/web`:

- `/opt/homebrew/bin/node node_modules/eslint/bin/eslint.js app lib tests components/agent-workbench.tsx`: passed.
- `/opt/homebrew/bin/node node_modules/typescript/bin/tsc --noEmit`: passed.
- `/opt/homebrew/bin/node --import tsx --test tests/*.test.ts`: 12 passed.
- `/opt/homebrew/bin/node node_modules/next/dist/bin/next build --webpack`: passed after correcting the test's keyframe type guard.
- `WEB_URL=http://localhost:3001 /opt/homebrew/bin/node node_modules/@playwright/test/cli.js test --timeout=45000`: 18 passed, 3 paid-provider scenarios skipped. Used `/tmp/sueperman-motion-acceptance.db`, paid providers disabled; original API restored afterward.
- Impeccable detector over changed UI targets: no findings.
- Desktop/mobile settled captures and six-frame role-motion contact sheet inspected; role changes remain usable during rapid input, motion settles, reduced-motion path passes, and request failure restores the pending button.
- `git diff --check` and design sidecar JSON validation: passed.

Backend behavior unchanged; backend suite was not repeated for this animation-only extension. DESIGN.md and the design sidecar motion records updated from the implemented effects.
