# Secrets management — minimal default vs opt-in backends

**Question asked:** how do secrets travel with the repo — across CI, a VPS, and a **new
workstation** — without ever landing in git? **Verdict: keep the ADR-0011 minimal default**
(gitignored `.env` + GitHub Actions secrets); use the now-implemented **opt-in backends**
(Bitwarden CLI, git-secret) when a second machine needs the same secrets
([ADR-0011](../adr/ADR-0011-minimal-secrets.md) ·
[#52](https://github.com/dataengy/ogip/issues/52)).

## The default path (no opt-in)

Slot *names* are the SSoT (`config/.env-render.py → SECRET_SLOTS`); `make render-env` writes
them blank into the gitignored root `.env`; you fill them by hand. CI uses GitHub Actions
encrypted secrets under the same names. Zero dependencies, nothing to sync — and nothing that
*can* sync: a new workstation starts from blank slots.

## Opt-in backends (`config/.env-secrets-render.sh`)

Both fill **only blank** slots (merge-safe — a hand-entered value is never overwritten) and
never print secret values. Backend is selected by `config/config.yml → secrets.backend` or
`--backend`; `just secrets-doctor` reports readiness of both without writing anything.

| Dimension | **Bitwarden CLI** (`bw`) | **git-secret** (GPG) |
|---|---|---|
| Where secrets live | your Bitwarden vault (secure-note item `OGIP .env.secrets`, hidden fields per slot) | in the repo — committed encrypted blob `config/secrets/.env.secrets.secret` |
| New-workstation flow | `bw login` → `export BW_SESSION="$(bw unlock --raw)"` → `just secrets-render` | import your GPG key → `just secrets-render` (backend `git-secret`) |
| Old-workstation flow | `just secrets-push` (creates/updates the vault item) | `just secrets-hide` → commit the `.secret` blob |
| Extra account/key | Bitwarden account (already in use here) | a GPG keypair you must carry yourself |
| Offline clone-and-go | no — vault must be reachable once | yes — the blob is already in the clone |
| Multi-user sharing | vault sharing / org collections | `git secret tell <email>` per recipient key |
| Rotation story | edit vault → `just secrets-render` everywhere | re-hide + commit; every clone pulls |
| Failure mode to know | vault locked ⇒ loud stop with the unlock command | no GPG secret key ⇒ backend unusable (doctor says so) |

## Recommendation

- **One person, ≥2 machines, Bitwarden already in daily use (this repo's case):** Bitwarden
  backend — the vault is the moving part you already trust; nothing secret is ever in the repo.
- **Fork-and-run collaborators or air-gapped bootstrap:** git-secret — the clone carries the
  blob; key distribution is the cost.
- **CI:** stays on GitHub Actions secrets regardless of the local opt-in.

Both can coexist: `git-secret` blobs as an in-repo escrow, Bitwarden as the everyday sync.

## Rejected

- **Vault daemon / SOPS+KMS / cloud secret managers** — over-built for a portfolio platform
  (same reasoning that shaped [ADR-0011](../adr/ADR-0011-minimal-secrets.md)).
- **Committing an encrypted full `.env`** — the derived non-secret values would churn the blob
  on every config change; only the secret slots are escrowed.
