# `spec/sources/` — data-source reach descriptors (GENERATED)

**Every file here is generated — do not edit.** Each descriptor is a one-way projection
from the ingestion registry SSoT (`~/.ai/skills/.settings/de/ingestion/sources/`), stamped
with a DO-NOT-EDIT header and the regeneration command. Hardlinking SSoT↔projection was
measured unsafe (`git checkout` severs the inode and the copies diverge silently) — hence
the projection.

## What these are (vs `spec/contracts/`)

| Tree | Answers | Example content |
|---|---|---|
| `spec/contracts/` | what the data **IS** | ODCS schema, quality rules, SLA, ownership |
| `spec/sources/` | how to **REACH** it, and whether we **MAY** | url, auth slots, tier, robots/ToS verdicts (verbatim, dated), measured rate limits, traps, `dlt:`/`scrape:`/`airbyte:` ingestion shape, `provenance:` audit trail |

Verdicts (KEYLESS-VERIFIED, SCRAPE-VERIFIED, FORBIDDEN, …) are **never stored** — they are
re-proven live by the probe on every check. A stored verdict rots into a lie; the
descriptors carry the *evidence and its date*, not the conclusion.

## Scoping

OGIP receives the **games area only** (`--area games`). The registry also carries other
areas (e.g. cinema) for other projects — emitting them here is a bug, not a feature.

## Commands (registry Justfile: `~/.ai/skills/_scripts/de/ingestion/Justfile`)

```sh
JF=~/.ai/skills/_scripts/de/ingestion/Justfile
just -f "$JF" probe <key>              # live-verify one source (real GET, real verdict)
just -f "$JF" probe-all                # the pre-flight sweep
just -f "$JF" spec-emit-check . games  # drift gate: exit 1 if these files are stale
just -f "$JF" spec-emit . games        # regenerate after editing the registry
```

## Reading a descriptor

Trust order: `traps:` (measured failure modes) > `robots:`/`license_note:` (verbatim,
dated — recheck if old) > everything else. `do_not_fetch: true` means the probe refuses to
open a connection; a source can be technically reachable and still forbidden (HLTB,
SteamDB — see their `license_note:` for the verbatim prohibitions). `publishable: false`
protects the *data*; `do_not_fetch` protects the *fetch* — they are independent gates.
