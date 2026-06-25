#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PARENT_DIR="$(dirname "$PROJECT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOG_DIR/bot.pid"
LOG_FILE="$LOG_DIR/bot.log"

mkdir -p "$LOG_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 not found. Please install Python 3 first."
  exit 1
fi

if [ ! -d "$PROJECT_DIR/.venv" ]; then
  python3 -m venv "$PROJECT_DIR/.venv"
fi

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"

python -m pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

echo "Installing Xray..."
wget -qO- https://raw.githubusercontent.com/ServerTechnologies/simple-xray-core/refs/heads/main/xray-install | bash

cd "$PARENT_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Bot is already running."
  exit 0
fi

nohup python -m Noodles.main >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Bot started successfully."
echo "Logs: $LOG_FILE"
echo "PID: $(cat "$PID_FILE")"
