#!/usr/bin/env bash
# start/status/stop only the checkout-owned tmux session.
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"
DEMO="$(dirname "$H")"
ROOT="$(dirname "$DEMO")"
S="wwtn-demo-$(printf '%s' "$DEMO" | sha256sum | cut -c1-10)"
PORT="${STAGE_PORT:-7100}"
OCP="${OPENCODE_PORT:-4096}"
case "${1:-}" in
 start)
  if tmux has-session -t "$S" 2>/dev/null; then echo "Already running: $S"; exit 0; fi
  for port in "$PORT" "$OCP"; do
    if ss -ltn | grep -q ":$port\b"; then echo "Port $port is busy; choose different ports" >&2; exit 1; fi
  done
  printf -v command 'OPENCODE_PORT=%q %q' "$OCP" "$H/opencode_server.sh"
  tmux new-session -d -s "$S" -n opencode -c "$DEMO" "$command"
  ready=false
  for i in $(seq 1 30); do
    if curl -fsS -o /dev/null -m 1 "http://127.0.0.1:$OCP/global/health" 2>/dev/null; then ready=true; break; fi
    sleep 1
  done
  if [ "$ready" != true ]; then tmux kill-session -t "$S" 2>/dev/null || true; echo 'OpenCode did not become ready; run its launcher in foreground' >&2; exit 1; fi
  printf -v command 'OPENCODE_PORT=%q STAGE_PORT=%q %q -m demo.harness.stage.server' "$OCP" "$PORT" "$DEMO/.venv/bin/python"
  tmux new-window -t "$S" -n stage -c "$ROOT" "$command"
  echo "Planner: http://127.0.0.1:$PORT/ ; logs: tmux attach -t $S"
  ;;
 status) tmux has-session -t "$S" 2>/dev/null && echo "Running: $S" || echo 'Not running';;
 stop) tmux kill-session -t "$S" 2>/dev/null && echo "Stopped: $S" || echo 'Not running';;
 *) echo 'Usage: demo/harness/stage.sh start|status|stop'; exit 1;;
esac
