#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if ! command -v grok >/dev/null 2>&1; then
  echo "Grok CLI is not installed."
  echo "Install it with: curl -fsSL https://x.ai/cli/install.sh | bash"
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

export QIRA_WORKSPACE_ROOT="${QIRA_WORKSPACE_ROOT:-$HOME/Documents/GitHub}"
export GROK_CONTROL_HOST="${GROK_CONTROL_HOST:-127.0.0.1}"
export GROK_CONTROL_PORT="${GROK_CONTROL_PORT:-8787}"

python -m uvicorn server:app --host "$GROK_CONTROL_HOST" --port "$GROK_CONTROL_PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT INT TERM

sleep 1
if command -v open >/dev/null 2>&1; then
  open "http://${GROK_CONTROL_HOST}:${GROK_CONTROL_PORT}"
fi

wait "$SERVER_PID"
