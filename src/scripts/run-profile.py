#!/usr/bin/env python
"""Run-profile launcher (A12): `just run-profile <name>` → `config/config.yml → run_profiles`.

A profile picks orchestrator/ingestion/transform. Prefect-orchestrated profiles drive the
production flow with the profile's transform engine (`pipelines/flows/main.py`); the
Dagster-orchestrated profile is a complete separate setup under
`experimental/orchestration/dagster_ogip/` and is pointed to, not half-run from here.
`services` listed by a profile are compose conveniences (Prefect runs ephemerally by default)
— nothing here starts them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

import yaml

REPO = Path(__file__).resolve().parents[2]

_DAGSTER_HINT = (
    "is the Dagster complete alternative setup — run it from its own project:\n"
    "  cd experimental/orchestration/dagster_ogip && bash jobs/dg-tasks.sh build-dwh-full"
)


def load_profiles() -> dict[str, dict[str, Any]]:
    """`run_profiles` from config/config.yml — the SSoT for every profile."""
    loaded: object = yaml.safe_load((REPO / "config" / "config.yml").read_text(encoding="utf-8"))
    data = cast("dict[str, Any]", loaded) if isinstance(loaded, dict) else {}
    profiles = data.get("run_profiles")
    if not isinstance(profiles, dict):
        raise SystemExit("config/config.yml has no run_profiles mapping")
    return cast("dict[str, dict[str, Any]]", profiles)


def resolve_profile(
    profiles: dict[str, dict[str, Any]], name: str | None
) -> tuple[str, dict[str, Any]]:
    """The named profile, or the one marked `default: true` when no name is given."""
    if name is None:
        for pname, profile in profiles.items():
            if profile.get("default"):
                return pname, profile
        raise SystemExit("run_profiles: no profile is marked `default: true`")
    if name not in profiles:
        raise SystemExit(f"unknown profile {name!r} — one of: {', '.join(profiles)}")
    return name, profiles[name]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run-profile", description=__doc__)
    parser.add_argument(
        "profile", nargs="?", default=None, help="profile name (default: the default profile)"
    )
    parser.add_argument("--list", action="store_true", help="list profiles and exit")
    args = parser.parse_args(argv)

    profiles = load_profiles()
    if args.list:
        for pname, profile in profiles.items():
            mark = "  (default)" if profile.get("default") else ""
            print(
                f"{pname}: orchestrator={profile.get('orchestrator')} "
                f"ingestion={profile.get('ingestion')} transform={profile.get('transform')}{mark}"
            )
        return 0

    name, profile = resolve_profile(profiles, args.profile)
    if profile.get("orchestrator") == "dagster":
        print(f"profile {name!r} {_DAGSTER_HINT}")
        return 2

    sys.path.insert(0, str(REPO))  # `pipelines`/`transform` are repo-root packages
    import importlib

    from pipelines._shared.engines import ENGINE_FLOWS

    transform = str(profile.get("transform", "sqlmesh"))
    module_path = ENGINE_FLOWS.get(transform)
    if module_path is None:
        raise SystemExit(
            f"no Prefect setup for transform {transform!r} — known: {sorted(ENGINE_FLOWS)}"
        )
    engine_flow = importlib.import_module(module_path).flow  # each setup exposes exactly one flow
    counts = engine_flow()
    print(f"profile {name}: outputs {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
