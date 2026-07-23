"""Back-compat shim — repo-relative paths moved to `pipelines._shared.paths` (Part 3.1, #37)."""

from __future__ import annotations

from pipelines._shared.paths import REPO, SPEC_SQL, SQLMESH_DIR

__all__ = ["REPO", "SPEC_SQL", "SQLMESH_DIR"]
