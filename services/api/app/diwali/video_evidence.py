"""Executable media checks. Passing format/duration never proves AdaL use."""

import hashlib
import json
import math
import subprocess
from pathlib import Path


def inspect_video(path):
    path = Path(path)
    if not path.is_file() or path.suffix.lower() != ".mp4":
        raise ValueError("Existing MP4 required")
    try:
        process = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
            "format=duration,format_name:stream=codec_type,codec_name,width,height", "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=10)
        data = json.loads(process.stdout)
        duration = float(data["format"]["duration"])
        streams = data["streams"]
        video = [stream for stream in streams if stream["codec_type"] == "video"]
        audio = [stream for stream in streams if stream["codec_type"] == "audio"]
        if (not math.isfinite(duration) or not 0 < duration < 120 or len(video) != 1 or not audio
                or video[0]["width"] <= 0 or video[0]["height"] <= 0
                or video[0]["width"] * 9 != video[0]["height"] * 16
                or video[0]["codec_name"] not in {"h264", "hevc"}
                or "mp4" not in data["format"]["format_name"].split(",")):
            raise ValueError("Video must be playable 16:9 MP4, with audio, under 120 seconds")
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "duration_seconds": duration, "width": video[0]["width"], "height": video[0]["height"],
            "has_audio": True, "adal_proof": "NOT_VERIFIED", "release_ready": False,
            "manual_review_required": ["AdaL project and actual export", "real footage/provenance",
                                       "narration intelligibility", "captions", "UI readability", "anonymous access"]}
    except (OSError, subprocess.SubprocessError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Media inspection unavailable or malformed") from exc
