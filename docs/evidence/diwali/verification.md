# Local V2 verification — 2026-11-15–16 UTC

Baseline `1dbd30ff4009cf357f28e70334703321a21c269f`, environment branch `work`.
Changes are uncommitted. Existing film assets are unchanged. This is local synthetic
acceptance, not deployed acceptance, live sponsor proof or a hackathon submission.

## Required checks

| Command | Observed result |
| --- | --- |
| `make test` | 143 backend tests passed (89 existing + 54 new), 11 frontend tests passed; existing Starlette TestClient deprecation warning remains. |
| `make lint` | Ruff and ESLint pass. |
| `make typecheck` | mypy (47 source files) and TypeScript pass. |
| `make seed` | Pass against isolated synthetic SQLite database. |
| `make demo` twice | Both pass: five purchases, one verified recall, one rejected near-match, one needs-review, one no-recall purchase, one simulated settlement, exactly one real-recall packet. |
| `make smoke WEB_PORT=3001` | Pass, matching frontend/API origins. |
| `make e2e WEB_PORT=3001` | 10 passed, 3 opt-in V1 live tests skipped. Includes three new V2 browser tests. |
| `make build` | Next production build passes; includes `/collaborations/[id]`. |
| `make container-test` with documented offline build inputs | Pass, including four production browser tests. Normal online dependency download remains blocked by environment CA mismatch; TLS/security settings unchanged. |

Final application database: `/tmp/sueperman-v2-complete.db`. Earlier disposable
acceptance database: `/tmp/sueperman-v2-acceptance.db`. Pytest creates per-test
SQLite files under its temporary directory. No user purchase database was seeded.
Backend origin `http://localhost:8000`; frontend `http://localhost:3001`.

Setup needed `pnpm --dir apps/web install --frozen-lockfile --store-dir /tmp/sueperman-pnpm-store`
because the default store was not writable. The standard Playwright Chromium
fetch failed with HTTP 403 `Domain forbidden`. Browser checks instead used the
installed `/usr/bin/chromium` and `/usr/bin/ffmpeg`, with:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
PLAYWRIGHT_BROWSERS_PATH=/tmp/sueperman-browsers \
make e2e WEB_PORT=3001
```

The temporary browser cache contains an FFmpeg symlink to the installed binary.
`playwright.config.ts` supports the explicit Chromium executable override; normal
downloaded Chromium remains the default elsewhere. Browser results do not prove
physical-phone camera behavior.

## Red → green evidence

The named TDD skill files were absent; the user explicitly authorized standard
red–green–refactor TDD instead. Backend behavior slices were tested before their
implementation:

- Collaboration workflow: six expected endpoint failures before adding APIs,
  followed by passing exact, negative, answer/revision, idempotency and partial-live tests.
  Initial fixture indexing was corrected to use purchase four for the missing model.
- Material source change: approved team export initially returned 200 after a new
  primary record; revised guard returns 409 and revokes approval while retaining history.
- Sponsor boundaries: four missing-module failures, then passing fixed-command,
  tool-policy, skill-integrity and Builder-response validation tests with doubles.
- Daily quota: reset initially permitted another run; persistent usage counter now
  survives demo reset and returns 429. Answer revisions also consume quota.
- Provider attribution: ledger initially accepted AdaL attribution on a replay
  Scout result; it now rejects mismatched provider/mode/role before persistence.

Frontend acceptance tests were authored first, but their initial execution was
blocked by browser/FFmpeg availability rather than reaching a behavioral assertion.
After the runtime workaround, the full new board path passed. The stale-export
browser test initially hit a selector ambiguity with Next's route announcer;
scoping to the visible error resolved the test. No live SDK enforcement is implied.

The migration test constructs a populated V1-only schema, adds V2 tables through
the existing initializer, compares every old row, preserves the historical approved
packet, and verifies foreign keys. No destructive database reset/migration was used.

## Remaining release gates

All five sponsor execution receipts, authenticated/isolated runtime setup, Finch
package delivery/invocation, Agent37 instance/sandbox verification, live budgets and
fault proof, AdaL-produced MP4 ≤120 seconds, team roster, submission channel,
usability observations and deployed V2 checks remain outstanding. The existing
public GitHub repository was anonymously readable; local V2 code has not been pushed.
See `../diwali/manifest.json` and `../../diwali-compliance.md` for R01–R18 mapping.

## Runtime continuation and additional red → green checks

Actual BAND 9.1.0 and pinned official AdaL SDK interfaces are installed through the optional `team` dependency group. Lyzr v3 HTTP profiles and Agent37 execution are wired through the same controller. All tests still use synthetic transports, not live proof. Additional failing assertions preceded fixes for omitted exclusions, incomplete Builder results, ZIP skill delivery, timed-out BAND provider cancellation, live source drift across cases, skill identity display, and citation requirements. Actual SDK option/mention models are used in the isolated tests; optional SDK tests skip if the extra is not installed.

The live-mode browser test first failed waiting for the missing mode selector; after implementation it verifies sharing disclosure and all five blocked provider labels. A preliminary browser attempt used the wrong port and is not counted as a behavior failure.

The container check was rerun with the optional dependency lock changes and still failed `UnknownIssuer`, this time on `jsonschema==4.26.0`. Earlier attempts failed on `pyjwt==2.15.1`. Read-only host/base-image trust inspection is in `container-diagnosis.md`; no TLS or security settings were changed.

`output/sueperman-v2-rehearsal/replay-ui.mp4` is 53.08 seconds of real local replay UI, with no audio. Three full-page screenshots and the synthetic Markdown export accompany it. It is source footage, not an AdaL-produced final demo, and has no live sponsor claim. The recording script executed successfully; its JavaScript syntax check passed. Existing `output/sueperman-film` and `output/playwright` have no diff.

## Final continuation

Added actual Docker sandbox tests and an actual AdaL SDK wire-protocol test using a synthetic native executable: filesystem writes outside workspace, backend-secret access, direct network, unapproved proxy hosts and four SDK tool requests are denied. Six sandbox tests pass. These are not native AdaL model calls. The portable draft passes five vectors in two clean processes. A cross-product source revision test first exposed stale approval and now revokes export when the same notice changes for another case.

The final offline production container run passes all four browser cases. Earlier TLS failures above are historical diagnosis, superseded for container acceptance by the documented offline route. The native AdaL installer returned HTTP 403; Finch listing download requires authentication and reviewed public upstream was unsuitable as-is. No third-party skill was installed.

The 110.000-second narrated/captioned rehearsal passes ffprobe duration/codec checks; sample frames at 20 and 80 seconds are readable. Full listening review is not claimed. It is not an AdaL export. The live runner's default preflight exits 2 with missing setup and makes no paid calls. Live proof remains absent.

PR preparation: log trailing whitespace was normalized without changing reported outcomes. The PR targets the unchanged baseline on `codex/sueperman`; the separate existing `codex/diwali-v2` branch is preserved. Reproducible media intermediates remain local and are excluded from the PR.
