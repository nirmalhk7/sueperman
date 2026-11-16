"""Prepare hash-locked wheels using the host's existing TLS trust; never change trust."""

import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or sys.version_info[:2] != (3, 12)
    ):
        sys.exit(
            "Offline inputs require Linux x86_64 Python 3.12; no cross-platform guess"
        )
    target = ROOT / "services/api/container-wheels"
    target.mkdir(exist_ok=True)
    subprocess.run(
        [
            "uv",
            "export",
            "--project",
            str(ROOT / "services/api"),
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(target / "requirements.txt"),
        ],
        check=True,
        env=os.environ
        | {"UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", "/tmp/sueperman-uv-cache")},
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            str(target / "requirements.txt"),
            "-d",
            str(target),
        ],
        check=True,
    )

    (target / "LOCK.sha256").write_text(
        "".join(
            hashlib.sha256((ROOT / file).read_bytes()).hexdigest() + "  " + file + "\n"
            for file in ["services/api/pyproject.toml", "services/api/uv.lock"]
        )
    )
