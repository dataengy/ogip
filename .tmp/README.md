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

## One-shot bundles

A bundle is a self-contained one-shot (`.tmp/.once/`) plus a gitignored `MANIFEST.*.md`
carrying its **context, requirements, actor, and metadata** — the record of *how* a body of
work was created, kept out of history but reproducible/verifiable on demand. The entry point
and intent are documented here (tracked); the contents are gitignored per the rule above.

| Bundle | Intent | Verify | Actor · date |
|---|---|---|---|
| `setup-vps-provisioning.sh` + `MANIFEST.vps-provisioning.md` | Reproduce/verify the VPS-provisioning tooling (`deploy/vps/hetzner.sh`, GUI secret ask, `deploy.hetzner` config) and the global skills it graduated into (`/provision-vps`, `/ask-secret-gui`). | `just -f .tmp/Justfile verify-vps-provisioning` (read-only: no box, no token, no writes) | Claude `claude-opus-4-8`, session `702f2198` · 2026-07-19 |
| `fetch-hushcrasher-newsletter.sh` + `MANIFEST.hushcrasher-newsletter.md` | Mirror the target domain's newsletter (5 posts) into `.ai/newsletter.hushcrasher.com/` as citable offline evidence — it is where `MobyGames`/`SteamDB`/`Gamalytic` are actually named, in footnotes a summary drops. Output is gitignored via `.git/info/exclude` (third-party text never enters history). | `just -f .tmp/Justfile verify-hushcrasher-newsletter` (read-only: no network, no writes) | Claude `claude-opus-4-8[1m]`, session `da3932e4` · 2026-07-23 |
| `agentic-otel-{spike,check}.sh` + `MANIFEST.agentic-obs.md` | Prove Claude Code native OTel telemetry lands in the obs stack (VM series names, Loki event labels/attrs) — gates the agentic-observability epic #33; probes graduate into `obs-verify.sh`, names into alerting rules + `ogip-agentic` dashboard. | `just -f .tmp/Justfile agentic-otel-check` (read-only) · full spike: `agentic-otel-spike` (runs one throwaway haiku session) | Claude `claude-fable-5` (xhigh), session `ca32d350` · 2026-07-19 |

Verify is **read-only and idempotent** — safe to re-run after a checkout/rebase to confirm the
bundle is intact. Once reviewed, a bundle can be deleted (`.tmp/.once/` is gitignored); the
durable artifacts already live in `deploy/vps/`, `src/`, and `~/.ai/skills/`.
