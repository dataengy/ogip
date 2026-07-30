"""Repo-relative paths shared by every flow module (no imports → no cycles)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC_SQL = REPO / "spec" / "sql"
SQLMESH_DIR = REPO / "transform" / "sqlmesh"
