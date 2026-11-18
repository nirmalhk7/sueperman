# Issue 2 evidence refresh

Application source: `03010a6`. The previous human walkthrough referenced removed demo controls, so `protocol-current.md` records the current buttons, separate workflow entry points, three synthetic public-workspace cases, controlled-vendor limitations, and a new empty observation sheet. Historical protocol/results remain unchanged.

Human sessions completed: **0 of 4**. Human task observations: **0 of 48**. No participants, quotations, comprehension scores, or human improvement measurements are invented. Issue 2 remains open.

## Fresh software preflight

The existing internal replay comparison was rerun in the clean verified application snapshot. It still uses the historical five synthetic cases and frozen oracle; it does not measure the current public UI or real model value.

```sh
PYTHONPATH=services/api:services/api/tests services/api/.venv/bin/python -m pytest -p conftest -q -s docs/evidence/diwali/usability/pilot.py
services/api/.venv/bin/pytest services/api/tests/integration/test_receipt_confirmation.py -q
```

| Block | Internal workflow | Service milliseconds | Outcome disagreements | Accepted actor messages |
| --- | --- | ---: | ---: | ---: |
| 1 | Deterministic | 70.74 | 0/5 | 0 |
| 1 | Local actors | 80.26 | 0/5 | 18 |
| 2 | Local actors | 76.46 | 0/5 | 18 |
| 2 | Deterministic | 46.91 | 0/5 | 0 |

Actual results: four replay arms passed; four synthetic receipt-confirmation checks passed. The receipt checks use mocked extraction and exercise PNG/PDF identifier review, confirmation, and duplicate-import behavior. Neither command makes paid/live provider calls. Timings cover run submission through terminal read in-process; they exclude import, inspection, export, and human activity. This sample does not establish a speed or usefulness advantage.

Raw results are retained beside this review. The pilot emits an existing pytest-asyncio configuration warning; both runs also report the existing Starlette/httpx deprecation warning. Those warnings are not relabeled test failures or hidden as an all-warning-free run.

The same application revision already passed the six recorded engineering checks in `docs/evidence/preparation/report.json`. This refresh adds documents and observations only; it makes no application/runtime change and does not claim release acceptance. Human recruitment, moderated sessions, actionable observed findings, and independent review of their results remain incomplete.
