# Issue 8: approved demo sign-in

The owner deferred proper authentication and chose a prefilled fake login form. This implements that presentation only. Original issue #8 remains open: private accounts, ownership, authorization, recovery, and data isolation are not implemented.

The primary navigation links to `/demo-login`. Fixed read-only synthetic credentials start an in-page simulated session. No credentials are submitted or stored. Continue opens the existing workspace; ending the session changes only the presentation. Reload resets the simulated session. Workspace routes remain accessible without signing in. Shared records must contain synthetic data only.

## Acceptance coverage

`apps/web/tests/demo-login.e2e.ts` exercises the real page in Chromium:

- Without JavaScript, submission stays disabled. This prevents native form navigation before hydration.
- At 1280px and 390px, fixed fake credentials and explicit shared-data boundaries remain visible.
- Keyboard submit starts the simulated session; the workspace link remains available.
- Ending the session returns to the form. Reload also returns to the form.
- No non-GET requests occur during these interactions, and the page does not overflow horizontally.

Implementation is limited to a new route and stylesheet, a browser test, and one navigation link. Concurrent design edits are separate and must not be included in the issue commit.

## Red and green evidence

Initial tests failed at both widths because `/demo-login` returned 404 and the sign-in heading was absent. After implementation, a browser run exposed submission before hydration. `hydration-red.log` records the focused regression failing with `Expected: disabled` / `Received: enabled`. The final readiness guard uses React's server/client snapshot boundary; it never performs authentication.

`ready-green.log` records all three tests passing. Earlier failed runs are retained. Initial development compilation exceeded 30 seconds; subsequent runs also exposed the native submission bug. Final checks allow 90 seconds per scenario without weakening assertions.

Screenshots show desktop and mobile form/session states. Independent reviewer inspected the code, tests, and mobile screenshot and found no blocker in the dummy presentation. That review explicitly did not approve closing the original private-account issue.

No external platform is required for this demo flow. It provides no access control. Downloaded exports, existing data, and background jobs are unaffected by the simulated sign-in/sign-out.

## Final verification

The shared checkout changed during initial broad checks, including new backend provider work. Those checks were not used to approve this change. Final verification used a clean archive of commit `f79cd6f` plus only the route, CSS, browser test, and one navigation link. `candidate.json` records hashes of all four files. The dependency directories were reused; no environment files or unrelated design/provider edits were copied.

Actual final commands and results:

- `make test`: 439 backend tests and 12 frontend tests passed. The backend suite emitted one existing Starlette/httpx deprecation warning; no test skipped.
- `make lint`: passed.
- `make typecheck`: passed, including 63 Python source files and TypeScript.
- `make build`: passed; `/demo-login` prerendered successfully.
- `WEB_URL=http://127.0.0.1:3028 pnpm exec playwright test demo-login.e2e.ts --timeout=90000`: all three acceptance scenarios passed against that production build.

Results and full logs are in `checks.json` and `clean-*.log`. Final screenshots show the clean candidate, not the concurrent redesign. This verifies the approved fake-login behavior; it does not satisfy original issue #8's private-account criteria or claim a complete release audit.
