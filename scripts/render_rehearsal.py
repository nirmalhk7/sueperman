"""Create a truthful 110-second offline rehearsal; never claim AdaL production."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/sueperman-v2-rehearsal"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SEGMENTS = [
    (
        12,
        "A recall match needs more than a similar product name. Sueperman makes the challenge visible. This is an offline rehearsal using synthetic purchases.",
    ),
    (
        14,
        "First, the near match. Scout proposes the supported notice. Skeptic finds a model restriction. The purchase is P B twenty three. The notice requires P B twenty two. No draft is available.",
    ),
    (
        18,
        "When the model is missing, Builder asks for that one fact. The user checks the product, enters the model, and explicitly confirms it. The case gets a new revision. The original purchase stays unchanged.",
    ),
    (
        21,
        "The exact case survives deterministic checks. The case board retains the source and the challenge. The user reviews the draft, approves it locally, and exports Markdown. This does not submit a claim or promise payment.",
    ),
    (
        20,
        "The live path is implemented for BAND delegation, an Agent thirty seven source worker, AdaL review, and a Lyzr case board. A reviewed Finch delivered skill is required. These adapters have local tests, but this footage does not prove live sponsor use.",
    ),
    (
        15,
        "Changed evidence or skill bytes revoke old approval. Failures remain partial. The public demo accepts synthetic cases only. Real sponsor accounts, execution receipts, and an AdaL produced export remain required.",
    ),
    (
        10,
        "Sueperman: understand the evidence, challenge the match, and find the next step. This rehearsal is not the final hackathon entry.",
    ),
]


def run(args):
    subprocess.run(
        args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def duration(path):
    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ],
            text=True,
        )
    )


def timestamp(seconds):
    return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02},000"


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    timed = []
    captions = []
    cursor = 0
    for i, (seconds, words) in enumerate(SEGMENTS):
        text = OUT / f"narration-{i}.txt"
        text.write_text(words)
        wav = OUT / f"voice-{i}.wav"
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"flite=textfile={text}:voice=slt",
                str(wav),
            ]
        )
        speed = max(1.0, duration(wav) / (seconds - 0.4))
        if speed > 1.35:
            raise ValueError(
                "Narration too dense; shorten text instead of making it unintelligible"
            )
        segment = OUT / f"voice-timed-{i}.wav"
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav),
                "-af",
                f"atempo={speed},apad",
                "-t",
                str(seconds),
                "-ar",
                "48000",
                str(segment),
            ]
        )
        timed.append(segment)
        # Sentence-sized captions rather than a dense paragraph.
        sentences = [x.strip() + "." for x in words.split(".") if x.strip()]
        part = seconds / len(sentences)
        for j, sentence in enumerate(sentences):
            start = round(cursor + part * j)
            end = round(cursor + part * (j + 1))
            captions.append(
                f"{len(captions) + 1}\n{timestamp(start)} --> {timestamp(end)}\n{sentence}\n"
            )
        cursor += seconds
    (OUT / "narration-concat.txt").write_text("".join(f"file '{p}'\n" for p in timed))
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(OUT / "narration-concat.txt"),
            "-c",
            "copy",
            str(OUT / "rehearsal-narration.wav"),
        ]
    )
    (OUT / "rehearsal-captions.srt").write_text("\n".join(captions))
    cards = [
        (
            "intro",
            12,
            "SUEPERMAN V2\nCounterexample review\n\nSynthetic purchases / Offline replay\nNot AdaL-produced / No live sponsor proof",
        ),
        (
            "outro",
            45,
            "IMPLEMENTED, AWAITING LIVE PROOF\n\nBAND / Agent37 / AdaL / Finch / Lyzr\n\nSource-linked case board and deterministic gates\nLocal approval and export / No claim submission\n\ngithub.com/nirmalhk7/sueperman\nV2 changes remain local; final AdaL video pending",
        ),
    ]
    for name, seconds, text in cards:
        path = OUT / f"{name}-card.txt"
        path.write_text(text)
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x102c36:s=1920x1080:r=25",
                "-t",
                str(seconds),
                "-vf",
                f"drawtext=fontfile={FONT}:textfile={path}:fontsize=42:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=18",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                str(OUT / f"{name}.mp4"),
            ]
        )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(OUT / "replay-ui.mp4"),
            "-t",
            "53",
            "-vf",
            "scale=1620:1080,pad=1920:1080:(ow-iw)/2:0,fps=25",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            str(OUT / "ui-cut.mp4"),
        ]
    )
    (OUT / "video-concat.txt").write_text(
        "".join(
            f"file '{OUT / name}'\n"
            for name in ["intro.mp4", "ui-cut.mp4", "outro.mp4"]
        )
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(OUT / "video-concat.txt"),
            "-i",
            str(OUT / "rehearsal-narration.wav"),
            "-vf",
            f"subtitles={OUT / 'rehearsal-captions.srt'}:force_style='Fontsize=18,MarginV=28,Outline=2',drawtext=fontfile={FONT}:text='OFFLINE REHEARSAL - NOT ADAL-PRODUCED':fontcolor=white:fontsize=23:box=1:boxcolor=black@0.8:x=24:y=16",
            "-t",
            "110",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(OUT / "rehearsal-110s.mp4"),
        ]
    )
    measured = duration(OUT / "rehearsal-110s.mp4")
    if measured > 120:
        raise ValueError("Rehearsal exceeds time cap")
    (OUT / "rehearsal-edit.json").write_text(
        json.dumps(
            {
                "duration_seconds": measured,
                "segments": SEGMENTS,
                "mode": "offline replay",
                "adal_produced": False,
                "live_sponsor_proof": False,
                "voice": "local libflite slt; draft narration",
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Created offline rehearsal: {measured:.2f}s; NOT AdaL-produced.")
