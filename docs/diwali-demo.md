# 110-second AdaL production brief

**Status: preparation, not final video.** The local recording script captures real replay UI and labels it honestly. It is not sponsor execution or AdaL production. Existing HyperFrames assets are preserved. Final production needs actual live footage, an authenticated AdaL Video Producer project, an exported MP4 and the project/export receipt.

## Footage available locally

`apps/web/scripts/record-team-rehearsal.mjs` records near-match, missing-model answer, case revision, exact match, local approval and Markdown export from the actual running application. It requires explicit `SYNTHETIC_DEMO_RECORDING=1` because it resets synthetic demo data. Run only against an isolated seeded database. The generated `output/sueperman-v2-rehearsal/` contains replay footage, screenshots and a synthetic exported draft. These are source assets, not a qualifying final video.

From `apps/web`, with local isolated apps on ports 3001/8000:

```sh
SYNTHETIC_DEMO_RECORDING=1 WEB_URL=http://localhost:3001 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
node scripts/record-team-rehearsal.mjs
```

## Final edit and narration

| Seconds | Actual footage required | Narration draft |
| --- | --- | --- |
| 0–12 | Confirmed synthetic NEWDERY purchase; synthetic disclosure | “A purchase record can suggest a recall. But a similar model is not enough. Sueperman makes the challenge visible before you prepare a remedy draft.” |
| 12–32 | Live Agent37 source lookup receipt, CPSC URL and timestamp | “Scout reads the supported official notice in an isolated Agent37 worker. The case keeps the source, observation time and version.” |
| 32–58 | Actual BAND addressed handoff, AdaL challenge, Finch identity/version/hash; PB23 rejection | “BAND delegates the candidate to a separate Skeptic. AdaL uses a reviewed Finch-delivered skill to test the restrictions. This model is PB23; the notice requires PB22. The candidate is rejected.” |
| 58–80 | Lyzr-produced board and missing-model question | “Lyzr turns the checked findings into this case board. When the model is missing, Builder asks for that one fact. It does not borrow a model from a similar purchase.” |
| 80–100 | Exact case, passed conditions, draft review, approval and export | “The exact model survives deterministic checks. You review the draft locally and export it. This does not submit a claim, certify ownership, or promise payment.” |
| 100–110 | Five actual sponsor role labels, limits, public repository link | “One supported recall, synthetic demo data, visible evidence and explicit failures. Sueperman helps you understand the next step.” |

Keep captions readable at phone size and preserve enough UI time to read PB22 versus PB23. Disclose time compression. Any replay excerpt must retain an on-screen replay label; do not cover it with sponsor badges. Do not record fake provider receipts or show blocked setup as successful execution.

## AdaL handoff

Import actual live application clips and the approved narration into an authenticated AdaL Video Producer project. Record the real project reference and export result in `docs/evidence/diwali/manifest.json`; do not put account tokens there. No AdaL project or export was created in this environment because no authenticated runtime/account is available.

After export, run:

```sh
ffprobe -v error -show_entries format=duration -of csv=p=0 final-demo.mp4
```

Require ≤120 seconds, audible narration, readable captions and visible real UI. Review content against the captured live receipts, then check public repository/video access anonymously after separately authorized publication. Do not submit or publish from this brief.

## Research observations still needed

Five pilot participants: count how many explain the PB23 exclusion and name the missing model without coaching; target four of five. No participants have been observed here. For the agent-value comparison, use exact, near-match, missing model, changed evidence, unsupported notice, source outage and injected instructions. Compare rule-only, Scout+Builder and full-team outputs; record supported extra findings, false assertions, latency and actual calls. Zero false verified positives is a release gate. Local deterministic tests are not proof that model collaboration improves comprehension.

## Available offline rehearsal

`output/sueperman-v2-rehearsal/rehearsal-110s.mp4` is 110.000 seconds, 1920×1080 H.264/AAC, with local synthetic narration, captions and actual replay UI. `scripts/render_rehearsal.py` regenerates it from the preserved source footage. Sample frames at 20 and 80 seconds were visually inspected; final audio intelligibility and full caption review still require listening/viewing. It is explicitly labeled **OFFLINE REHEARSAL — NOT ADAL-PRODUCED**. Import the footage, captions and edit recipe into authenticated AdaL Video Producer after live footage exists. No AdaL project/export has been fabricated.
