#!/usr/bin/env bash
set -euo pipefail
DEMO="$(cd "$(dirname "$0")/.." && pwd)"
umask 077
export PAPERCLIP_CONFIG_DIR="$DEMO/harness/paperclip/private"
mkdir -p "$PAPERCLIP_CONFIG_DIR"
if [[ -z "${PAPERCLIP_API_KEY:-}" && -f "$PAPERCLIP_CONFIG_DIR/api.key" ]]; then
  export PAPERCLIP_API_KEY="$(cat "$PAPERCLIP_CONFIG_DIR/api.key")"
fi
exec "$DEMO/.venv-paperclip/bin/paperclip" "$@"
