"""Read-only setup report: never starts a runtime, sends a message or prints credentials."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))

from app.collaboration.live import blockers
from app.config import Settings

if __name__ == "__main__":
    settings = Settings()
    missing = blockers(settings.model_copy(update={"collaboration_live_enabled": True}))
    report = {
        "live_kill_switch_enabled": settings.collaboration_live_enabled,
        "configuration_blockers": missing,
        "live_execution_performed": False,
        "live_proof_verified": False,
    }
    print(json.dumps(report, indent=2))
    sys.exit(2 if missing or not settings.collaboration_live_enabled else 0)
