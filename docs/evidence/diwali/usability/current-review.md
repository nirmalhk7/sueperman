# Issue #2 independent review — November 17, 2026 Pacific

Application revision: `bbc37e3cbef1f5931e39288ee7d669924817f205`.

The existing protocol and results are historical working documents. Their original application revision and measurements are preserved. This review does not replace missing human observations with automated results.

An independent verification subagent ran:

```sh
PYTHONPATH=services/api:services/api/tests services/api/.venv/bin/python -m pytest -p conftest -q -s docs/evidence/diwali/usability/pilot.py
services/api/.venv/bin/pytest -q services/api/tests/integration/test_receipt_confirmation.py services/api/tests/diwali/test_api.py services/api/tests/integration/test_workflow.py
```

Observed: four pilot arms passed; 29 targeted regression checks passed. Current run service times, in execution order:

| Block | Workflow | Milliseconds |
| --- | --- | ---: |
| 1 | Existing | 108.02 |
| 1 | Local agent | 102.15 |
| 2 | Local agent | 85.68 |
| 2 | Existing | 45.75 |

These are in-process API timings, not participant task times. They do not reproduce the historical observation that local processing was slower in both pairs. Neither sample establishes general speed or user value.

The historical receipt check uses the legacy confirmation endpoint, which still blocks identifier changes after matching. The newer purchase-correction flow is separate and preserves revisions; the historical text must not be read as a claim that correction is unavailable throughout the current app.

## Acceptance accounting

- Protocol/sample: a four-person, counterbalanced protocol is written; participant recruitment and completion remain pending.
- Automated outcome/evidence/export comparison: four fresh arms passed against the frozen oracle.
- Receipt import/confirmation: targeted synthetic integration checks passed; extractor output is controlled, not live-provider evidence.
- Human completion, mistakes, elapsed task time, and understanding of uncertainty/source/workflow labels: no observations exist.
- Material usability defects: unknown until observed; no defects or participant quotations are invented.

Issue #2 remains incomplete and must not be closed. Complete the moderated sessions, record actual observations, and obtain independent review of the completed evidence before closure.

## Fresh baseline checks

Root verification on the same application revision:

- `make test` inside the restricted sandbox: 370 passed, three browser setup errors because loopback socket binding was denied. Frontend unit checks were not reached in that attempt.
- `make test` rerun with approved local-server/browser access: exit 0; 373 backend tests and 12 frontend unit tests passed. Includes isolated Diwali and P1 browser acceptance. Existing Starlette/httpx deprecation warning remains.
- `make lint typecheck`: exit 0; Ruff, ESLint, mypy (61 files), and TypeScript passed.

These checks establish software regression evidence, not human usability. Full release acceptance, final deployment checks, and required video remain separate issue #3 work.
