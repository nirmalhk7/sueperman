# Sueperman commercial

**Use `sueperman-90s.mp4` for submission.** 90 seconds, 1920×1080, 30 FPS, H.264/AAC, about 87 MB. `sueperman-90s-captioned.mp4` contains selectable English captions (enabled by default in compatible players); `captions.srt` is also supplied.

Editable preview: http://localhost:3017/#project/sueperman-film

From this directory:

```sh
npx --yes hyperframes preview --background --port 3017
npx --yes hyperframes check --json
npx --yes hyperframes render --quality delivery --workers 3 --fps 30 -o sueperman-90s.mp4
python3 verify_delivery.py
```

The HyperFrames desktop app also edits this project; the preview's Edit with Framey button opens it. Close the preview before handing the project to the desktop app.

`STORYBOARD.md` is the supplied brief; `PRODUCTION.md` records the production choices; `REVIEW.md` and `ACCEPTANCE.md` document verification and unmet criteria; `assets/SOURCES.md` records media sources and artwork prompts. Voice timing: `audio-cues.json`.

This version uses illustrated motion-comic acting, not fully rigged/lip-synced theatrical character animation. Unverified X posts were omitted. Real production screenshots preserve replay/simulation and local-only approval labels. No application code or root SPEC.md changed; nothing uploaded or submitted externally.
