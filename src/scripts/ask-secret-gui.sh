#!/usr/bin/env bash
# Acquire a credential through a native macOS dialog and store it in the gitignored .env.
#
# Opens the page where the credential is generated, then asks for it in a dialog with hidden
# input. The value is never echoed to stdout, never passed as a command-line argument (argv is
# world-readable via `ps`), and never reaches shell history.
#
# Idempotent: if the key is already in the environment or already filled in .env, it says so
# and exits 0 without prompting — safe to call unconditionally from a deploy script.
#
# Usage: ask-secret-gui.sh <ENV_KEY> <TOKEN_URL> [PROMPT_TEXT]
#   ask-secret-gui.sh HETZNER_API_TOKEN https://console.hetzner.cloud/ "Hetzner Cloud API token"
#
# Exit: 0 secret present (pre-existing or captured) · 1 cancelled/empty · 2 unsupported platform
set -euo pipefail

KEY="${1:?usage: ask-secret-gui.sh <ENV_KEY> <TOKEN_URL> [PROMPT]}"
URL="${2:?token URL required}"
PROMPT="${3:-$KEY}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

# osascript is macOS-only. Fail with the manual instruction rather than pretending to succeed —
# a caller that believes the secret was stored will fail far less legibly further along.
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[ask-secret] not macOS — set ${KEY} manually (get it at ${URL}), then re-run" >&2
  exit 2
fi

# Already available? Environment wins over .env; either means nothing to ask.
if [[ -n "${!KEY:-}" ]]; then
  echo "[ask-secret] ${KEY}: already in environment"
  exit 0
fi
if [[ -f "$ENV_FILE" ]] && grep -qE "^${KEY}=.+" "$ENV_FILE"; then
  echo "[ask-secret] ${KEY}: already set in .env"
  exit 0
fi

echo "[ask-secret] ${KEY}: opening ${URL} — answer the dialog"
open "$URL" 2>/dev/null || true

# The prompt reaches AppleScript as an ARGUMENT (`on run argv`), never by string
# interpolation. Interpolating would let a quote in the prompt break out of the string
# literal and change the script — the same class of bug as SQL injection.
value="$(
  osascript \
    -e 'on run argv' \
    -e 'set d to display dialog (item 1 of argv) & "

A browser tab with the token page just opened. Paste the value here:" default answer "" with hidden answer buttons {"Cancel", "Save"} default button "Save" with title "OGIP: credential needed"' \
    -e 'return text returned of d' \
    -e 'end run' \
    "$PROMPT" 2>/dev/null || true
)"

[[ -n "$value" ]] || {
  echo "[ask-secret] ${KEY}: cancelled or empty — nothing written" >&2
  exit 1
}

# Write via python with the secret passed in the ENVIRONMENT, not argv: command-line
# arguments are visible to every process on the box via `ps`, environment of another
# process is not. Rewrites an existing key in place, otherwise appends.
touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
SECRET_VALUE="$value" SECRET_KEY="$KEY" ENV_PATH="$ENV_FILE" python3 <<'PY'
import os
import pathlib

key, value = os.environ["SECRET_KEY"], os.environ["SECRET_VALUE"]
path = pathlib.Path(os.environ["ENV_PATH"])
lines = path.read_text().splitlines() if path.exists() else []

for i, line in enumerate(lines):
    if line.split("=", 1)[0] == key:
        lines[i] = f"{key}={value}"
        break
else:
    lines.append(f"{key}={value}")

path.write_text("\n".join(lines) + "\n")
PY

echo "[ask-secret] ${KEY}: saved to .env (mode 600)"
