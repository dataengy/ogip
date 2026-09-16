# `config/secrets/` — git-secret working directory (opt-in, ADR-0011)

Home of the **git-secret** opt-in backend
([ADR-0011](../../docs/adr/ADR-0011-minimal-secrets.md) ·
[docs/comparisons/secrets-management.md](../../docs/comparisons/secrets-management.md)).

| File | Tracked? | What it is |
|---|---|---|
| `.env.secrets` | **never** (gitignored) | plaintext `KEY=VALUE` export of the filled secret slots from the root `.env` |
| `.env.secrets.secret` | **yes** | the GPG-encrypted blob — safe to commit; this is what syncs machines |
| `README.md` | yes | this file |

The ignore rules in the root `.gitignore` enforce exactly that split: everything in this
directory is ignored **except** the README and `*.secret` blobs.

## Flow

```bash
just secrets-setup-git-secret   # one-time: git secret init + tell + add (needs a GPG key)
just secrets-hide               # .env filled slots -> .env.secrets -> .env.secrets.secret
git add config/secrets/*.secret .gitsecret && git commit   # blob + keyring metadata
# ...on the new workstation (with the same GPG key imported):
just secrets-render             # reveal + fill the blank slots of .env
```

Slot names are declared once in `config/.env-render.py` (`SECRET_SLOTS`); this backend
never invents its own list. `just secrets-doctor` reports readiness (GPG key present,
init state, blob presence) without writing anything.

**Never** commit plaintext here — `git secret hide` is the only path from `.env` to a
committed artifact.
