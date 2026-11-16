#!/usr/bin/env python3
"""AdaL SDK launcher. Configure reviewed local image/bundle and scoped cached auth.

Only --help and --sdk-runtime are accepted. This never installs or authenticates.
"""

import signal
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app.collaboration.adal_sandbox import EgressBridge, bundle_digest, sandbox_command
from app.config import Settings

if __name__ == "__main__":
    if sys.argv[1:] == ["--help"]:
        print("Sueperman restricted AdaL launcher: --sdk-runtime")
        sys.exit(0)
    if sys.argv[1:] != ["--sdk-runtime"]:
        sys.exit("Only the SDK runtime is permitted")

    def stop(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        workspace = Path.cwd().resolve()
        if workspace.parent != Path(
            tempfile.gettempdir()
        ).resolve() or not workspace.name.startswith("sueperman-skeptic-"):
            raise ValueError("Only an isolated Skeptic temporary workspace is allowed")
        settings = Settings()
        bundle = Path(settings.adal_bundle_dir).resolve(strict=True)
        if bundle_digest(bundle) != settings.adal_bundle_sha256:
            raise ValueError("Runtime bundle hash differs")
        image = settings.adal_sandbox_image
        auth = Path(settings.adal_auth_directory).resolve(strict=True)
        allowed = [h for h in settings.adal_allowed_hosts.split(",") if h]
        name = "sueperman-adal-" + uuid.uuid4().hex
        with (
            tempfile.TemporaryDirectory(prefix="sueperman-egress-") as directory,
            EgressBridge(Path(directory) / "proxy.sock", allowed),
        ):
            command = sandbox_command(
                image, Path.cwd(), bundle, auth, directory, name=name
            )
            try:
                completed = subprocess.run(command, check=False, timeout=95)
            finally:
                subprocess.run(
                    ["docker", "rm", "--force", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=5,
                )
        sys.exit(completed.returncode)
    except (KeyError, ValueError, OSError, subprocess.SubprocessError):
        sys.exit("Isolated AdaL setup or execution unavailable; no fallback")
