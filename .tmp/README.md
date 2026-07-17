# `.tmp/` — temporary scripts & files

Scratch space for one-off, experimental, and in-progress **scripts and other temporary
files** (scratch data, notes, exports, downloads). **Everything here is gitignored except
this `README.md` and `Justfile`** — so the contents stay out of history while the entry
points and intent are documented.

## Layout

| Path | Purpose |
|---|---|
| `.tmp/*.sh` · `.tmp/*.py` | working scripts (gitignored) |
| `.tmp/*` (any other files) | scratch data / notes / exports / downloads (gitignored) |
| `.tmp/.once/` | one-shot migrations / bootstraps, run once then discarded (gitignored) |
| `Justfile` | local recipes for the scripts here (`just -f .tmp/Justfile <recipe>`) |

## Graduation rule

`.tmp/` is a staging area, not a home. When a script proves durable, **graduate** it — don't
let it rot here:

- reusable dev/ops tooling → `integrations/` (with a proper client + config)
- a repeatable agent workflow → a **skill** (`~/.ai/skills`, via `/create-skill`)
- product/runtime logic → `src/ogip/` (typed, tested) or `src/scripts/` (common utilities)

Durable interfaces belong in `Makefile` / root `Justfile` + docs — never left as a `.tmp/` script.
