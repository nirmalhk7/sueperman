# Finch package review — November 16, 2026

No third-party package was installed or executed, and no publication, signing, acquisition transaction or login was performed.

The official [Brain2 Roundtable listing](https://www.finchtech.ai/en/market/chips/base/brain2-roundtable_finchip) exposes version 1, MIT license, skill 185, primary-document hash `722dd354a2b069fd3c51c7fdaccf5c235aecdabf9aa32cc099c2b67d8f242552` and content commitment `1d16398817257a3543ba634e5c647036fae838d177b0322e4e197840f85e8268`. A commitment is not assumed to be the downloaded ZIP hash. The listing requires login to download. Its public information links to [EnormousMush/brain2](https://github.com/EnormousMush/brain2), inspected read-only at `8fdcfa84e736ce60d937913bbb8251f1117bfdec`.

The upstream `backend/app/debate/roles.py` and `engine.py` require Skeptic to attack every round (engine rejects a Skeptic stance other than attack). Sueperman must allow a supported match to survive with no additional exclusion. The four-role debate also introduces an analogist outside this bounded task. Therefore this candidate is unsuitable as-is. The upstream repository is not the actual Finch-delivered skill package; its inspection cannot certify undisclosed package contents.

[Test Scenarios](https://www.finchtech.ai/en/market/chips/base/test-scenarios_finchip) and [Pre-Mortem](https://www.finchtech.ai/en/market/chips/base/pre-mortem_finchip) are general QA/planning listings, not established recall reviewers. No suitable downloadable public package was established. Following [Finch delivery guidance](https://www.finchtech.ai/en/story/use-skills), actual downloaded bytes, license, identity/version, review and invocation remain mandatory. Installation confirmation remains separate from static review.

## Prepared alternative, not Finch proof

`skills/counterexample-review/` contains an event-authored MIT 1.0.0 draft with a fixed checklist, no network/tool execution, citation constraints and five vectors. The reproducible ZIP is `output/sueperman-v2-rehearsal/counterexample-review-draft.zip`. Two clean Python processes agree on all five vectors; hashes are in `docs/evidence/diwali/portable-skill.json`. This is a local draft, not a Finch installation or delivery. Sponsor-supported delivery or authorized publication through Finch is still needed if no suitable existing package becomes accessible. Publication is not authorized by this task.
