#!/bin/sh
# Starts It (page host + local database) and the OwlPilot worker, publishes the page on first run,
# and stops both with Ctrl-C. Run from the repository root:  ./scripts/start.sh
set -eu
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
IT_HOME="$ROOT/.tools/it"
export IT_HOME
IT="$IT_HOME/bin/it"

[ -x "$IT" ] || { echo "It is not installed yet. Run ./scripts/setup.sh first."; exit 1; }
[ -x .venv/bin/python ] || { echo "Python environment missing. Run ./scripts/setup.sh first."; exit 1; }
mkdir -p data

IT_PID=""
WORKER_PID=""
cleanup() {
  [ -n "$WORKER_PID" ] && kill "$WORKER_PID" 2>/dev/null || true
  [ -n "$IT_PID" ] && kill "$IT_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

if "$IT" status >/dev/null 2>&1; then
  echo "It is already running."
else
  echo "Starting It…"
  "$IT" serve --log "$ROOT/data/it.log" &
  IT_PID=$!
  i=0
  until "$IT" status >/dev/null 2>&1; do
    i=$((i + 1)); [ $i -gt 60 ] && { echo "It did not start; see data/it.log"; exit 1; }
    sleep 1
  done
fi

if ! "$IT" read owlpilot >/dev/null 2>&1; then
  echo "Publishing the OwlPilot page for the first time…"
  STATE="$(mktemp)"; rm -f "$STATE"
  .venv/bin/python -m owlpilot initial --out "$STATE" >/dev/null
  "$IT" create "OwlPilot · Academic co-pilot" --id owlpilot --dir app --state-file "$STATE" --agent "OwlPilot" >/dev/null
  rm -f "$STATE"
else
  "$IT" update owlpilot --dir app >/dev/null
fi

if pgrep -f "owlpilot.worker" >/dev/null 2>&1; then
  echo "The OwlPilot worker is already running elsewhere; not starting a second one."
else
  .venv/bin/python -m owlpilot.worker &
  WORKER_PID=$!
fi

cat <<EOF

OwlPilot is running:  http://localhost:4700/p/owlpilot
First time in a browser? Pair it:  IT_HOME="\$PWD/.tools/it" .tools/it/bin/it site
Press Ctrl-C to stop.

EOF
wait
