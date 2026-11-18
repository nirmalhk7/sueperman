# Release audit for issue #3

The application walkthrough was recorded on commit `49968cb090e85f13edbaa76ec2f11740bd5f94a9` in a disposable Compose project. The local API and web images matched the recorded application source hashes. The filesystem and database were isolated from the shared demo. Only CSV import and free official CPSC reads were enabled for the walkthrough.

| Requirement | Evidence and current status |
| --- | --- |
| Identified code, configuration and engineering checks | The [purchase-status verification](../purchase-status/report.json) binds the walkthrough application revision to successful test, lint, type, build, smoke, browser, container and storage checks. The release verifier and approved documentation changes passed [six engineering checks](engineering.json). Container and storage passed on the preceding candidate, whose only subsequent change was waiting for the new run in the browser correction test. |
| Anonymous repository and demo access | GitHub returned HTTP 200 and reported a public default branch of `main`. The historical DigitalOcean hostname failed local resolution and an independent public DNS lookup returned NXDOMAIN. Deployment-side data and cost controls could not be checked there. See [public access observations](public-access.json). |
| Reliable local fallback | The owner-approved [durable Compose runbook](../../../deploy/DURABLE_STORAGE.md) covers operator setup, snapshots and restore. With providers disabled, the compose workflow supports CSV, deletion and recovery. For a source-cited local walkthrough, enable only free CPSC reads and use synthetic purchases. The isolated recorded configuration is in [runtime evidence](local-runtime-live-cpsc.json). |
| Real application footage | The local original is a 72.433-second 1920×1080 WebM. Full video decoding passed. The recorded browser imported five synthetic purchases, completed an actual CPSC lookup, showed the exact match, rejected near-match and missing model, and exercised local approval and download. See [footage manifest](live-footage-manifest.json). |
| Timed rehearsal and final presentation | The automated interaction took 75.222 seconds. A human presenter rehearsal and final audio, captions, AdaL provenance and anonymous video playback still need evidence. |
| Human usability and accounts | Four human sessions remain outstanding under #2. The public workspace remains shared while private accounts are deferred under #8. |

| Feature or provider | Evidence boundary |
| --- | --- |
| CPSC and deterministic matching | Actual official notice 26-792 was retrieved. PB22 matched, PB23 was rejected, and a missing model required review. See [public lookup](public-cpsc-probe.json). |
| Receipt extraction | Controlled regression coverage and separate historical provider receipts. The walkthrough imports CSV. |
| Evidence guidance and export | Current walkthrough shows local approval before Markdown export on synthetic data. Browser automation performed the approval. |
| Retention and restore | Local Compose and regression evidence cover deletion, explicit re-import consent, backup retention and restore. The earlier raw capture discovered stale status text, repaired in `49968cb`. |
| BAND, Lyzr and Agent37 | Earlier synthetic team execution is recorded in [historical evidence](../../../output/live-workspace-live-verification.json). The present CPSC-only recording demonstrates the deterministic workflow. Integrated footage and current release proof remain outstanding. |
| Finch | The procedural package and its local checks exist. Delivery and reviewer consumption still require verified external evidence. |
| AdaL | Owner-deferred. A final AdaL project and narrated, captioned MP4 under 120 seconds are still missing. |

Formal G0 fails on prior changes to two protected files. The [gate log](formal-g3-protected-drift.log) records those paths. The [lower-gate test nodes](independent-gate-nodes.json) and [mutation checks](independent-mutations.json) passed separately. Issue #3 remains open. Footage files are retained locally at the paths and hashes in their manifests. The approved README correction records the historical deployment boundary and current workflow. The original README versions, original baseline and exact patch accompany the [approval record](readme-authorization.json).
