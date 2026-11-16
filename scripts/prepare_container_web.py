"""Build same-origin production web assets on a trusted host for offline Docker."""

import hashlib
import os
import platform
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web"
if __name__ == "__main__":
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("Requires matching Linux x86_64 host")
    subprocess.run(
        [
            "pnpm",
            "install",
            "--frozen-lockfile",
            "--store-dir",
            "/tmp/sueperman-pnpm-store",
        ],
        cwd=WEB,
        check=True,
    )
    subprocess.run(
        ["pnpm", "build"],
        cwd=WEB,
        check=True,
        env=os.environ
        | {
            "NEXT_PUBLIC_API_BASE_URL": "",
            "NEXT_PUBLIC_SHARED_DEMO": "true",
            "NEXT_PUBLIC_SENTRY_DSN": "",
            "SENTRY_AUTH_TOKEN": "",
            "NEXT_TELEMETRY_DISABLED": "1",
        },
    )
    target = WEB / "container-deps"
    for directory in ["node_modules", ".next"]:
        source = WEB / directory
        for path in source.rglob("*"):
            if directory == ".next" and path.relative_to(source).parts[0] in {
                "cache",
                "dev",
            }:
                continue
            if path.is_symlink() and not path.resolve().is_relative_to(
                source.resolve()
            ):
                raise ValueError("Dependency symlink escapes the prepared tree")

        def production_only(info):
            parts = Path(info.name).parts
            return (
                None
                if len(parts) > 1
                and parts[0] == ".next"
                and parts[1] in {"dev", "cache"}
                else info
            )

        temporary = target / (directory + ".tgz.tmp")
        with tarfile.open(temporary, "w:gz", compresslevel=1) as archive:
            archive.add(source, arcname=directory, filter=production_only)
        temporary.replace(target / (directory + ".tgz"))
    files = ["node_modules.tgz", ".next.tgz"]
    (target / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256((target / f).read_bytes()).hexdigest() + "  " + f + "\n"
            for f in files
        )
    )
    (target / "LOCK.sha256").write_text(
        "".join(
            hashlib.sha256((WEB / file).read_bytes()).hexdigest() + "  " + file + "\n"
            for file in ["pnpm-lock.yaml", "package.json", "next.config.ts"]
        )
    )
