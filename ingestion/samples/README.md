# `ingestion/samples/` — demo fixtures (SYNTHETIC)

Small, **hand-authored** sample payloads so the pipeline runs end-to-end with **zero
credentials** (demo mode / CI). These are **not** captured API responses.

| File | Provenance |
|---|---|
| `rawg_games.json` | Synthetic. Real game titles + real RAWG IDs, RAWG `/api/games`-shaped, but metric values (`rating`, `ratings_count`, `added`, some `metacritic`) are **approximations**, not fetched. |

**dlt still does the ingest** — in demo mode dlt loads *these records*; in live mode dlt loads
records fetched from the real API. To capture a **real** sample instead, set a RAWG API key in
`.env` and run `just capture-sample rawg` (fetches live via dlt and overwrites the fixture).

**Size rule (Git LFS):** small text fixtures (like `rawg_games.json`) stay plain git —
diffable, reviewable. Binary/large samples (`*.parquet`, `*.zip`, `*.gz`) go through
**Git LFS** automatically via `.gitattributes`; run `make lfs-install` once per clone or
`git add` silently stores a raw blob and `.ci/run.sh lfs-guard` fails the build.
