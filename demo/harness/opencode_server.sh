#!/usr/bin/env bash
# Isolated demo OpenCode; optional arguments are passed to the pinned binary.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
DEMO="$(dirname "$H")"
OC="$H/opencode"
BIN="$OC/v1.19.5/opencode"
umask 077
export XDG_CONFIG_HOME="$OC/xdg/config" XDG_DATA_HOME="$OC/xdg/data" XDG_CACHE_HOME="$OC/xdg/cache" XDG_STATE_HOME="$OC/xdg/state"
export OPENCODE_CONFIG_DIR="$DEMO/.opencode"
export OPENCODE_DISABLE_PROJECT_CONFIG=true OPENCODE_DISABLE_CLAUDE_CODE=true
export OPENCODE_CONFIG="$OC/private/runtime.json"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME" "$OC/private"
unset NEBIUS_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY OPENAI_BASE_URL
python3 "$H/configure_agent.py"
PW="$OC/private/server_password"
[ -s "$PW" ] || python3 -c 'import secrets; print(secrets.token_urlsafe(18))' > "$PW"
export OPENCODE_SERVER_USERNAME=opencode OPENCODE_SERVER_PASSWORD="$(cat "$PW")"
cd "$DEMO"
if [ ! -x "$BIN" ]; then echo 'Run python3 demo/install.py first' >&2; exit 1; fi
if [ $# -eq 0 ]; then
  exec "$BIN" serve --hostname 127.0.0.1 --port "${OPENCODE_PORT:-4096}"
else
  exec "$BIN" "$@"
fi
