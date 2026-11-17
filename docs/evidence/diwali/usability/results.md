# Offline comparison, November 16, 2026

Application revision and planned sample are in [the protocol](protocol.md). Four automated arms completed. Human sessions completed: 0 of 4. No participant times, errors, quotations or comprehension scores are available.

| Block | Workflow | Run time (ms) | Outcome disagreements / cases | Accepted actor messages |
| --- | --- | ---: | ---: | ---: |
| 1 | Existing | 42.42 | 0 / 5 | 0 |
| 1 | Local agent | 111.00 | 0 / 5 | 18 |
| 2 | Local agent | 81.38 | 0 / 5 | 18 |
| 2 | Existing | 61.29 | 0 / 5 | 0 |

All four arms matched PB22, rejected PB23, returned no opportunity for the bottle, left the missing power-bank model under review and identified the earbuds settlement as simulated. Each recall detail contained a quoted excerpt and the frozen CPSC notice URL with replay provenance. Only the exact match yielded a packet. Each preapproval export returned HTTP 409; after local approval the export included the model, notice URL and local-only disclaimer.

Separate integration checks exercised synthetic PNG and PDF upload, rejected unconfirmed identifiers, accepted explicit model confirmation and blocked later identifier changes after matching. The extractor returned a controlled mock response. The comparison used the same seeded CSV for both modes.

The local actor workflow took longer in both pairs and produced 18 timeline entries while returning the same decisions. Two measurements per mode, one host and in-process HTTP requests do not establish a general latency estimate. In the human sessions, record whether participants use a timeline entry to explain the PB23 rejection, and whether either group mistakes a recorded notice for a fresh lookup. No material software defect observed in these checks. Human usability, UI completion and live-provider quality remain unmeasured.

## Reproduction

From the repository root with the existing API environment installed:

```sh
PYTHONPATH=services/api:services/api/tests services/api/.venv/bin/python -m pytest -p conftest -q -s docs/evidence/diwali/usability/pilot.py
services/api/.venv/bin/pytest -q services/api/tests/integration/test_receipt_confirmation.py services/api/tests/diwali/test_api.py services/api/tests/integration/test_workflow.py
```

Observed 4 pilot arms passed and 29 regression checks passed. The first command loads the repository's offline provider fixture and prints one measurement per arm. Each arm creates a temporary database. Elapsed time includes run execution in TestClient and terminal status retrieval, excluding user interactions.
