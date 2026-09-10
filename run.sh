#!/usr/bin/env bash
# Stuart Saves the Pomodoro Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH}"
exec python3 -m sstp.app "$@"
