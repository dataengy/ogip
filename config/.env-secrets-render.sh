#!/usr/bin/env bash
# config/.env-secrets-render.sh — fill the blank secret slots of the root .env from an
# opt-in backend (ADR-0011): Bitwarden CLI (`bw`) or git-secret (GPG).
#
# Actions (default: pull):
#   pull               fill BLANK secret slots in .env from the chosen backend (merge-safe:
#                      values already set by hand are never overwritten)
#   push               bitwarden only — write the FILLED slots of .env into the vault item
#                      (creates the secure-note item on first push)
#   hide               git-secret — export filled slots to the plaintext file and encrypt it
#                      into the committed *.secret blob
#   reveal             git-secret — decrypt committed blobs back to the plaintext file
#   setup-git-secret [email]
#                      one-time init: git secret init + tell + add (needs a GPG secret key)
#   doctor             report backend readiness (read-only, no writes)
#
# Flags:
#   --backend bitwarden|git-secret   override config/config.yml -> secrets.backend
#   --dry-run                        print what would change (slot NAMES only)
#
# Safety: secret VALUES are never printed; all reporting is slot names + set/blank state.
# Slot names come from config/.env-render.py (SECRET_SLOTS) — the single source of truth.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
CONFIG_YML="$REPO_ROOT/config/config.yml"
# Canonical project venv (same convention the build files export).
: "${UV_PROJECT_ENVIRONMENT:=$REPO_ROOT/.run/venv}"
export UV_PROJECT_ENVIRONMENT

log() { printf '[secrets] %s\n' "$*" >&2; }
die() {
  log "ERROR: $*"
  exit 1
}

py() { uv run --project "$REPO_ROOT" python "$@"; }

# --- config/config.yml -> secrets.{backend,bitwarden.item,git_secret.plaintext} ----------
read_config() {
  [[ -f "$CONFIG_YML" ]] || die "missing $CONFIG_YML"
  local out
  out="$(
    py - "$REPO_ROOT" <<'PY'
import pathlib
import sys

import yaml

root = pathlib.Path(sys.argv[1])
cfg = yaml.safe_load((root / "config" / "config.yml").read_text(encoding="utf-8"))
try:
    sec = cfg["secrets"]
    print(sec["backend"], sec["bitwarden"]["item"], sec["git_secret"]["plaintext"], sep="\t")
except KeyError as exc:  # fail loud: name the missing key and the file it belongs in
    raise SystemExit(f"config/config.yml: missing secrets.{exc.args[0]} key") from exc
PY
  )"
  IFS=$'\t' read -r CFG_BACKEND BW_ITEM GS_PLAINTEXT <<<"$out"
  [[ -n "$CFG_BACKEND" && -n "$BW_ITEM" && -n "$GS_PLAINTEXT" ]] ||
    die "config/config.yml secrets section is incomplete"
}

# --- slot names from config/.env-render.py (SECRET_SLOTS) --------------------------------
slot_names() {
  py - "$REPO_ROOT" <<'PY'
import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
path = root / "config" / ".env-render.py"
spec = importlib.util.spec_from_file_location("envrender", path)
assert spec is not None and spec.loader is not None, f"cannot load {path}"
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("\n".join(mod.SECRET_SLOTS))
PY
}

# --- merge KEY=VALUE source file into blank .env slots (names-only reporting) ------------
merge_into_env() { # $1=source-file $2=dry(0|1)
  py - "$ENV_FILE" "$1" "$2" <<'PY'
import pathlib
import sys

env_path = pathlib.Path(sys.argv[1])
src_path = pathlib.Path(sys.argv[2])
dry = sys.argv[3] == "1"

src: dict[str, str] = {}
for raw in src_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, val = line.partition("=")
    if val:
        src[key.strip()] = val

out: list[str] = []
filled = kept = 0
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw
    if "=" in line and not line.lstrip().startswith("#"):
        key, _, val = line.partition("=")
        key = key.strip()
        if key in src:
            if val == "":
                print(f"  fill {key}", file=sys.stderr)
                filled += 1
                line = f"{key}={src[key]}"
            else:
                print(f"  keep {key} (already set locally)", file=sys.stderr)
                kept += 1
    out.append(line)

env_keys = {ln.partition("=")[0].strip() for ln in out if "=" in ln}
unmatched = [k for k in src if k not in env_keys]
for key in unmatched:
    print(f"  skip {key} (no slot in .env — re-run `make render-env`?)", file=sys.stderr)

if not dry and filled:
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
verb = "DRY-RUN: would fill" if dry else "filled"
print(
    f"{verb} {filled} slot(s); kept {kept} local; unmatched {len(unmatched)}",
    file=sys.stderr,
)
PY
}

# --- export FILLED slots of .env to a KEY=VALUE file; echo names, comma-joined -----------
export_filled_slots() { # $1=out-file
  local slots_csv
  slots_csv="$(slot_names | paste -sd, -)"
  py - "$ENV_FILE" "$1" "$slots_csv" <<'PY'
import pathlib
import sys

env_path = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
slots = set(sys.argv[3].split(","))

vals: dict[str, str] = {}
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, val = line.partition("=")
    key = key.strip()
    if key in slots and val:
        vals[key] = val

out_path.write_text("".join(f"{k}={v}\n" for k, v in vals.items()), encoding="utf-8")
print(",".join(vals))
PY
}

# --- doctor helper: slot fill state of .env (names only) ---------------------------------
slot_state() {
  local slots_csv
  slots_csv="$(slot_names | paste -sd, -)"
  py - "$ENV_FILE" "$slots_csv" <<'PY'
import pathlib
import sys

env_path = pathlib.Path(sys.argv[1])
slots = sys.argv[2].split(",")
vals: dict[str, str] = {}
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            vals[key.strip()] = val
for slot in slots:
    if slot not in vals:
        state = "NO-SLOT"
    elif vals[slot]:
        state = "set"
    else:
        state = "blank"
    print(f"  {slot}: {state}")
PY
}

secure_tmp() {
  local tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/ogip-secrets.XXXXXX")"
  chmod 600 "$tmp"
  printf '%s' "$tmp"
}

# --- bitwarden backend -------------------------------------------------------------------
bw_require() {
  command -v bw >/dev/null 2>&1 || die "bitwarden-cli (bw) not installed — brew install bitwarden-cli"
  command -v jq >/dev/null 2>&1 || die "jq not installed — brew install jq"
  if [[ -z "${BW_SESSION:-}" ]]; then
    local status
    status="$(bw status 2>/dev/null | jq -r .status)"
    [[ "$status" == "unlocked" ]] || die \
      "bitwarden vault is '$status' — run: export BW_SESSION=\"\$(bw unlock --raw)\" (or bw login first)"
  fi
}

bw_pull() { # $1=dry
  bw_require
  bw sync -q 2>/dev/null || log "warn: bw sync failed (offline?) — using cached vault"
  local item_json tmp
  item_json="$(bw get item "$BW_ITEM" 2>/dev/null)" ||
    die "vault item '$BW_ITEM' not found — run \`just secrets-push\` once from a machine with a filled .env"
  tmp="$(secure_tmp)"
  trap 'rm -f "$tmp"' EXIT
  jq -r '.fields[]? | select(.value != null and .value != "") | "\(.name)=\(.value)"' \
    <<<"$item_json" >"$tmp"
  log "pull from bitwarden item '$BW_ITEM':"
  merge_into_env "$tmp" "$1"
}

bw_push() { # $1=dry
  bw_require
  [[ -f "$ENV_FILE" ]] || die "no .env — run \`make render-env\` and fill secrets first"
  local tmp names item_json item_id
  tmp="$(secure_tmp)"
  trap 'rm -f "$tmp"' EXIT
  names="$(export_filled_slots "$tmp")"
  [[ -n "$names" ]] || die "no filled secret slots in .env — nothing to push"
  log "push to bitwarden item '$BW_ITEM': ${names//,/ }"
  if [[ "$1" == "1" ]]; then
    log "DRY-RUN: no vault writes"
    return 0
  fi
  bw sync -q 2>/dev/null || log "warn: bw sync failed (offline?) — pushing to cached state"
  if item_json="$(bw get item "$BW_ITEM" 2>/dev/null)"; then
    item_id="$(jq -r .id <<<"$item_json")"
    # Upsert: replace matching fields, keep foreign ones; type 1 = hidden field.
    jq --rawfile kv "$tmp" '
      ([$kv | split("\n")[] | select(length > 0)
        | capture("(?<k>[^=]+)=(?<v>.*)")]) as $pairs
      | .fields = ((.fields // [])
          | map(select(.name as $n | ($pairs | map(.k) | index($n)) | not))
          + ($pairs | map({name: .k, value: .v, type: 1})))
    ' <<<"$item_json" | bw encode | bw edit item "$item_id" >/dev/null
    log "updated vault item '$BW_ITEM'"
  else
    jq -n --arg name "$BW_ITEM" --rawfile kv "$tmp" '
      {type: 2, secureNote: {type: 0}, name: $name,
       notes: "OGIP secret slots (ADR-0011) — managed by config/.env-secrets-render.sh",
       fields: ([$kv | split("\n")[] | select(length > 0)
                 | capture("(?<k>[^=]+)=(?<v>.*)")]
                | map({name: .k, value: .v, type: 1}))}
    ' | bw encode | bw create item >/dev/null
    log "created vault item '$BW_ITEM'"
  fi
}

# --- git-secret backend ------------------------------------------------------------------
gs_require() {
  command -v git-secret >/dev/null 2>&1 || die "git-secret not installed — brew install git-secret"
  command -v gpg >/dev/null 2>&1 || die "gpg not installed — brew install gnupg"
}

gs_initialized() { [[ -d "$REPO_ROOT/.gitsecret" ]]; }

gs_pull() { # $1=dry
  gs_require
  gs_initialized || die "git-secret not initialized — run \`just secrets-setup-git-secret\`"
  [[ -f "$REPO_ROOT/$GS_PLAINTEXT.secret" ]] ||
    die "no committed blob $GS_PLAINTEXT.secret — run \`just secrets-hide\` on a filled machine and commit it"
  (cd "$REPO_ROOT" && git secret reveal -f)
  log "pull from git-secret plaintext $GS_PLAINTEXT:"
  merge_into_env "$REPO_ROOT/$GS_PLAINTEXT" "$1"
}

gs_hide() { # $1=dry
  gs_require
  gs_initialized || die "git-secret not initialized — run \`just secrets-setup-git-secret\`"
  [[ -f "$ENV_FILE" ]] || die "no .env — run \`make render-env\` and fill secrets first"
  local names plain_abs
  plain_abs="$REPO_ROOT/$GS_PLAINTEXT"
  mkdir -p "$(dirname "$plain_abs")"
  if [[ "$1" == "1" ]]; then
    local tmp
    tmp="$(secure_tmp)"
    trap 'rm -f "$tmp"' EXIT
    names="$(export_filled_slots "$tmp")"
    log "DRY-RUN: would export slots to $GS_PLAINTEXT and encrypt: ${names//,/ }"
    return 0
  fi
  names="$(export_filled_slots "$plain_abs")"
  chmod 600 "$plain_abs"
  [[ -n "$names" ]] || die "no filled secret slots in .env — nothing to hide"
  log "exported slots to $GS_PLAINTEXT: ${names//,/ }"
  (cd "$REPO_ROOT" && git secret hide -m)
  log "encrypted -> $GS_PLAINTEXT.secret — commit the blob: git add '$GS_PLAINTEXT.secret'"
}

gs_reveal() {
  gs_require
  gs_initialized || die "git-secret not initialized — run \`just secrets-setup-git-secret\`"
  (cd "$REPO_ROOT" && git secret reveal -f)
  log "revealed plaintext(s) — they are gitignored; never commit them"
}

gs_setup() { # $1=email(optional)
  gs_require
  local email="$1"
  [[ -n "$email" ]] || email="$(git -C "$REPO_ROOT" config user.email)"
  [[ -n "$email" ]] || die "no email — pass one: setup-git-secret you@example.com"
  gpg --list-secret-keys "$email" >/dev/null 2>&1 || die \
    "no GPG secret key for '$email' — generate one first: gpg --full-generate-key (then re-run)"
  (
    cd "$REPO_ROOT"
    gs_initialized || git secret init
    git secret tell "$email"
    if [[ ! -f "$GS_PLAINTEXT" ]]; then
      mkdir -p "$(dirname "$GS_PLAINTEXT")"
      slot_names | sed 's/$/=/' >"$GS_PLAINTEXT"
      chmod 600 "$GS_PLAINTEXT"
      log "created blank plaintext $GS_PLAINTEXT (gitignored)"
    fi
    git secret list | grep -qx "$GS_PLAINTEXT" || git secret add "$GS_PLAINTEXT"
  )
  log "git-secret ready — fill .env, then \`just secrets-hide\` and commit the .secret blob"
  log "commit the .gitsecret/ metadata directory as well"
}

# --- doctor ------------------------------------------------------------------------------
doctor() {
  log "backend (config/config.yml secrets.backend): $CFG_BACKEND"
  log ".env slot state:"
  slot_state
  log "bitwarden:"
  if command -v bw >/dev/null 2>&1; then
    local status
    status="$(bw status 2>/dev/null | jq -r '.status + " (" + (.userEmail // "-") + ")"')"
    log "  bw $(bw --version 2>/dev/null): $status; item: '$BW_ITEM'"
    [[ "$(bw status 2>/dev/null | jq -r .status)" == "unlocked" ]] ||
      log "  -> unlock: export BW_SESSION=\"\$(bw unlock --raw)\""
  else
    log "  bw not installed (brew install bitwarden-cli)"
  fi
  log "git-secret:"
  if command -v git-secret >/dev/null 2>&1; then
    log "  git-secret $(git secret --version 2>/dev/null): initialized=$(gs_initialized && echo yes || echo NO)"
    if gpg --list-secret-keys 2>/dev/null | grep -q sec; then
      log "  gpg secret key: present"
    else
      log "  gpg secret key: NONE — git-secret backend unusable until: gpg --full-generate-key"
    fi
    log "  plaintext: $GS_PLAINTEXT ($([[ -f "$REPO_ROOT/$GS_PLAINTEXT" ]] && echo present || echo absent))"
    log "  blob: $GS_PLAINTEXT.secret ($([[ -f "$REPO_ROOT/$GS_PLAINTEXT.secret" ]] && echo present || echo absent))"
  else
    log "  git-secret not installed (brew install git-secret)"
  fi
}

# --- args --------------------------------------------------------------------------------
usage() { sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

ACTION="pull"
DRY=0
BACKEND_OVERRIDE=""
EMAIL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    pull | push | hide | reveal | doctor | setup-git-secret)
      ACTION="$1"
      ;;
    --dry-run)
      DRY=1
      ;;
    --backend)
      BACKEND_OVERRIDE="${2:?--backend needs a value}"
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      if [[ "$ACTION" == "setup-git-secret" && -z "$EMAIL" ]]; then
        EMAIL="$1"
      else
        die "unknown argument: $1 (see --help)"
      fi
      ;;
  esac
  shift
done

read_config
BACKEND="${BACKEND_OVERRIDE:-$CFG_BACKEND}"

case "$ACTION" in
  pull)
    [[ -f "$ENV_FILE" ]] || die "no .env — run \`make render-env\` first"
    case "$BACKEND" in
      bitwarden) bw_pull "$DRY" ;;
      git-secret) gs_pull "$DRY" ;;
      *) die "backend is '$BACKEND' — opt-in backends: bitwarden | git-secret (set config.yml secrets.backend or pass --backend)" ;;
    esac
    ;;
  push)
    bw_push "$DRY"
    ;;
  hide)
    gs_hide "$DRY"
    ;;
  reveal)
    gs_reveal
    ;;
  setup-git-secret)
    gs_setup "$EMAIL"
    ;;
  doctor)
    doctor
    ;;
esac
