# spec/orchestration — ODOS 0.1 (Open Data Orchestration Standard)

> 🇷🇺 Русская версия: [README.ru.md](README.ru.md)

The orchestration SSoT: *when, in what order, and how it survives failure* — never *what*
is computed (that is ODTS, `spec/sql`). One file per group; `_defaults.yml` is merged into
every job. Any key ODOS does not define is a compile error (design §4.9).

Compile: `just odos-compile` → `defs/orchestration/<group>.py` (Dagster — flattened layout
since PR #34; `warehouse/` is a subpackage split into jobs/schedules/sensors; the
Prefect adapter is plan 3). Round-trip is enforced by `src/tests/unit/test_odos_to_dagster.py`:
if you edit these files (or add a `spec/sql` model — selections expand statically), re-run
the compile and commit the regenerated output.

Design: `docs/superpowers/specs/2026-07-20-odos-orchestration-spec-design.md` · issue #37.
