# V2.1 sponsor evidence

These rows distinguish isolated live probes from completed application gates. Probe artifacts under `docs/evidence/diwali/v2.1/` include execution timestamps and tested source digests. No full provider application gate is claimed.

| Provider | Current execution proof | Existing setup and next required evidence |
| --- | --- | --- |
| BAND / G4 | PARTIAL | Python SDK 8.1.0 custom adapter completed a two-message live handshake, then all five frozen cases over 18 live messages. Actual SDK sender metadata, replies and reducer consumption were checked; four connections stopped cleanly. Sources and worker decisions were recorded/deterministic. Application DB/UI transport wiring remains incomplete. See `G4/live-probe.json` and `G4/five-case-live-probe.json`. |
| Lyzr / G5 | PARTIAL | GET v3 configuration and one authorized synthetic inference returned HTTP 200. Existing Builder returned schema-valid JSON preserving the PB23 model exclusion in 3.29 seconds, without retry. This does not satisfy the required Skeptic reviewer configuration/schema or application integration. See `G5/live-probe.json`. |
| Finch / G6 | PARTIAL | Fresh signed-in Brave delivery of Strategy Red Team v1 matched every previously reviewed archive member and published Markdown SHA-256. Archive path checks and local tamper test passed. This candidate is not the specified event-authored Recall Evidence Auditor package; no model invocation loaded it. See `G6/delivery-probe.json`. Publication requires separate authorization. |
| Agent37 / G7 | NOT_STARTED | Key exists; last observed balance was $0.00, with no instance. Verify execution/result/deletion contracts, obtain authorized compute and prove a consumed source result plus cleanup. |
| AdaL / G8–G9 | NOT_STARTED | Deferred by owner. No AdaL project/export or presentation MP4 is claimed. This remains a release requirement in the supplied event contract. |

Account setup is not execution. Environment flags are not health. Mocked/recorded tests are not provider receipts. G4+ live calls need a named target and explicit applicable authorization/budget. Reuse existing credentials; do not rotate keys or create duplicate identities just because the conversation resumed.
