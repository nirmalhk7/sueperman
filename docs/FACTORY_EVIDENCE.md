# Implementation evidence

This describes work actually performed in this repository. It is not proof of Whirlwind use or a sponsor award.

1. **Specification:** `SPEC.md` copied from the accessible implementation-contract child Page of Sueperman — AIE × MLH Hackathon. Locked §0 choices drove Python 3.12 / FastAPI / SQLite / Next.js / exact-model matching.
2. **Task instruction:** implement P0 fixture-first in vertical slices, test every checkpoint, then add integrations in priority order; never submit claims or invent facts.
3. **Component:** `services/api/app/matching/recall.py`, normalization and source policy. Model suffixes, punctuation and digit differences remain meaningful; unknown conditions require review.
4. **Tests before implementation:** `test_core.py` initially produced 15 missing-feature failures. API contract tests then failed with 404 responses against the empty FastAPI scaffold. UI acceptance failed on missing hero heading before UI implementation. Frontend label test failed on an empty result before label implementation.
5. **Observed green:** core 15 passed; API + core 18 passed; browser end-to-end flow passed. Later provider and regression checks expanded coverage; final counts are in actual logs.
6. **Review/fix loop:** changed evidence could leave an old packet approvable (observed 200 where 409 required); invalidation and approval/export gates repaired it. CSV history made demo selection show six rows (observed browser count 6 vs 5); selecting returned seed IDs repaired it without deleting imported history. Unknown source identity initially produced rejection instead of review; corrected. Duplicate CPSC rows returned twice and candidate overflow raised unavailability; deduplication and explicit truncation repaired both.
7. **Live proof:** production CPSC adapter executed a public network request; exact/near-match outcomes and observation time saved to `docs/evidence/live-cpsc.json`. Optional sponsor transports were tested with doubles, explicitly distinguished from live execution.
8. **Final checks:** `docs/evidence/final-checks.log`, `browser-checks.log`, `offline-smoke.log`, and screenshots/recording in `output/playwright/`. Current local checkpoint is available through `git log -1`; no PR or external publication was requested.

See `implementation-log.md` for commands, observed red/green evidence, scope and limits. Source, tests, docs and recorded evidence are included in the same repository checkpoint.

Implementation checkpoint: `a0751b4` (`codex/sueperman`). Clean-clone verification at that exact source revision passed setup, 41 backend tests, frontend unit test, lint/type/build, repeated offline smoke and both Playwright flows with keys empty and providers disabled. Actual output: `docs/evidence/clean-clone.log`. Later evidence-only commit does not change application code.
