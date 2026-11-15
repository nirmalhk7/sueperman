"""Coordinator-facing facade: operations stage rows but never commit.

Pure matcher/composer logic remains in V1. Persistence owns additive case metadata
and adapted ORM staging glue; legacy commit-owning helpers are not invoked.
"""

from app.diwali.persistence import invalidate_stale, stage_finalization

__all__ = ["invalidate_stale", "stage_finalization"]
