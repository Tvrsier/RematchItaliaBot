#!/usr/bin/env bash
set -euo pipefail

# Uso: ./start_bot.sh <path/to/bot.pex> [args...]
# Esempio: ./start_bot.sh build/0.2.1/rematch_bot-0.2.1.pex --debug

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path/to/bot.pex> [args...]"
  exit 1
fi

PEX_FILE="$1"
shift || true

if [[ ! -f "$PEX_FILE" ]]; then
  echo "PEX not found: $PEX_FILE" >&2
  exit 1
fi

mkdir -p logs run

# Avvio in background con python3 (funziona sempre)
nohup python3 "$PEX_FILE" "$@" >> logs/rematch_bot.out 2>&1 &
echo $! > run/rematch_bot.pid

echo "Started. PID=$(cat run/rematch_bot.pid)  |  Log: logs/rematch_bot.out"
