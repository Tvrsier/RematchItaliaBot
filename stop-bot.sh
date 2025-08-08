#!/usr/bin/env bash
set -euo pipefail

# Uso: ./stop_bot.sh
# Usa il PID salvato in run/rematch_bot.pid

PIDFILE="run/rematch_bot.pid"

if [[ ! -f "$PIDFILE" ]]; then
  echo "PID file not found: $PIDFILE"
  exit 0
fi

PID="$(cat "$PIDFILE" || true)"
if [[ -z "${PID}" ]]; then
  echo "Empty PID file: $PIDFILE"
  rm -f "$PIDFILE"
  exit 0
fi

if ! ps -p "$PID" >/dev/null 2>&1; then
  echo "Process $PID not running."
  rm -f "$PIDFILE"
  exit 0
fi

echo "Stopping PID $PID..."
kill "$PID" || true

# attende un attimo, poi forza se serve
for i in {1..10}; do
  if ! ps -p "$PID" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ps -p "$PID" >/dev/null 2>&1; then
  echo "Forcing stop (SIGKILL) for $PID"
  kill -KILL "$PID" || true
fi

rm -f "$PIDFILE"
echo "Stopped."