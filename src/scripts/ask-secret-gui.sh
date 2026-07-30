#!/usr/bin/env bash
# ask-secret-gui.sh — capture ONE credential and store it in an env file. Dual-mode:
#
#   • AGENTIC (no controlling tty — an agent launched the command): a native macOS GUI dialog
#     pops on the human's screen (hidden input). This is why an agent can still get a secret
#     from the human without a terminal.
#   • INTERACTIVE (a human at a tty): a hidden terminal prompt (`read -s`), any OS.
#
# `--mode auto` (default) picks by whether stdin is a tty. Both modes OPEN THE TOKEN URL in the
# browser first, so the human is already on the page where the value is generated.
#
# The minimal, dependency-free secret primitive — no GitLab/CI coupling, no validation. For the
# batteries-included version (validation + CI variable sync) use /add-secret.
#
# Safety: the value is never echoed to stdout, never passed as a command-line argument (argv is
# world-readable via `ps`), never written to shell history. The GUI prompt reaches AppleScript
# as an argument (`on run argv`), so a quote in it cannot break out and alter the script.
#
# Idempotent: if the key is already in the environment or the env file, it says so and exits 0.
#
# Usage: ask-secret-gui.sh <ENV_KEY> <TOKEN_URL> [--env-file PATH] [--prompt TEXT] [--mode auto|gui|terminal]
#   ask-secret-gui.sh HETZNER_API_TOKEN https://console.hetzner.cloud/ --env-file ./.env
#
# Exit: 0 present (captured or pre-existing) · 1 cancelled/empty · 2 cannot prompt in this mode · 4 bad args
set -uo pipefail

KEY="${1:-}"
URL="${2:-}"
[[ -n "$KEY" && -n "$URL" ]] || {
  echo "usage: ask-secret-gui.sh <ENV_KEY> <TOKEN_URL> [--env-file PATH] [--prompt TEXT] [--mode auto|gui|terminal]" >&2
  exit 4
}
shift 2

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.env"
PROMPT="$KEY"
MODE="auto"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --prompt)
      PROMPT="${2:?}"
      shift 2
      ;;
    --mode)
      MODE="${2:?}"
      shift 2
      ;;
    *)
      echo "ask-secret-gui: unknown arg: $1" >&2
      exit 4
      ;;
  esac
done
case "$MODE" in auto | gui | terminal) ;; *)
  echo "ask-secret-gui: --mode must be auto|gui|terminal" >&2
  exit 4
  ;;
esac

# ── idempotency ──────────────────────────────────────────────────────────────────────────────
if [[ -n "${!KEY:-}" ]]; then
  echo "[ask-secret] ${KEY}: already in environment"
  exit 0
fi
if [[ -f "$ENV_FILE" ]] && grep -qE "^${KEY}=.+" "$ENV_FILE"; then
  echo "[ask-secret] ${KEY}: already set in ${ENV_FILE}"
  exit 0
fi

# ── resolve mode: agent (no tty) → gui; human (tty) → terminal ─────────────────────────────────
resolve_mode() {
  case "$MODE" in
    gui | terminal)
      echo "$MODE"
      return
      ;;
  esac
  if [[ -t 0 ]]; then
    echo terminal
    return
  fi # a human is at the terminal
  [[ "$(uname -s)" == "Darwin" ]] && {
    echo gui
    return
  }         # agent on macOS → GUI
  echo none # agent on a headless/Linux box → cannot prompt
}
RESOLVED="$(resolve_mode)"

open_url() { # open the credential page cross-platform (best-effort)
  if command -v open >/dev/null 2>&1; then
    open "$1" 2>/dev/null || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1" 2>/dev/null || true
  else
    echo "[ask-secret] open this URL to get the credential: $1" >&2
  fi
}

capture_gui() { # macOS dialog, hidden input; prompt passed as an argv item (injection-safe)
  osascript \
    -e 'on run argv' \
    -e 'set d to display dialog (item 1 of argv) & "

A browser tab with the token page just opened. Paste the value here:" default answer "" with hidden answer buttons {"Cancel", "Save"} default button "Save" with title "OGIP: credential needed"' \
    -e 'return text returned of d' \
    -e 'end run' \
    "$PROMPT" 2>/dev/null || true
}

capture_terminal() { # hidden read from the controlling terminal; prompt to stderr, value to stdout
  local v=""
  printf '%s\n  paste %s (input hidden): ' "$PROMPT" "$KEY" >&2
  IFS= read -rs v </dev/tty || true
  printf '\n' >&2
  printf '%s' "$v"
}

if [[ "$RESOLVED" == "none" ]]; then
  echo "[ask-secret] ${KEY}: no way to prompt here (agent, no macOS GUI, no tty)." >&2
  echo "  Get it at ${URL} and set it manually:  export ${KEY}=…   (or add to ${ENV_FILE})" >&2
  exit 2
fi

echo "[ask-secret] ${KEY}: opening ${URL} — ${RESOLVED} prompt" >&2
open_url "$URL"

if [[ "$RESOLVED" == "gui" ]]; then
  value="$(capture_gui)"
else
  value="$(capture_terminal)"
fi

[[ -n "$value" ]] || {
  echo "[ask-secret] ${KEY}: cancelled or empty — nothing written" >&2
  exit 1
}

# ── persist (0600; secret via env to python, never argv) ───────────────────────────────────────
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

echo "[ask-secret] ${KEY}: saved to ${ENV_FILE} (mode 600)"
