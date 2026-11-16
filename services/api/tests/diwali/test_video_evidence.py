"""Synthetic media exercises checks; it never becomes AdaL or demo proof."""

import importlib
import subprocess

import pytest


def validator():
    try:
        return importlib.import_module("app.diwali.video_evidence")
    except ModuleNotFoundError:
        pytest.fail("Demo media validator is not implemented")


def clip(tmp_path, *, seconds=1, size="160x90", audio=True):
    path = tmp_path / "synthetic-test.mp4"
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={size}:r=1"]
    if audio:
        args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=8000"]
    args += ["-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        args += ["-c:a", "aac"]
    subprocess.run([*args, str(path)], check=True, capture_output=True, timeout=15)
    return path


def test_under_two_minutes_widescreen_audio_does_not_claim_adal_or_release(tmp_path):
    module = validator()
    result = module.inspect_video(clip(tmp_path))
    assert result["duration_seconds"] <= 120
    assert result["width"] == 160 and result["height"] == 90
    assert result["has_audio"] is True
    assert result["adal_proof"] == "NOT_VERIFIED"
    assert result["release_ready"] is False
    assert "captions" in result["manual_review_required"]


@pytest.mark.parametrize("kwargs", [{"seconds":120}, {"seconds":121}, {"size":"144x144"}, {"audio":False}])
def test_overlong_square_or_silent_export_cannot_pass(tmp_path, kwargs):
    module = validator()
    with pytest.raises(ValueError):
        module.inspect_video(clip(tmp_path, **kwargs))
