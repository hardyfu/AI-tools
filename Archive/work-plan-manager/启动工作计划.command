#!/bin/zsh

PROJECT_DIR="/Users/ryan/Desktop/pythoncode/work-plan-manager"
PID_FILE="$PROJECT_DIR/.server.pid"
LOG_FILE="$PROJECT_DIR/.server.log"
URL="http://127.0.0.1:8000"

cd "$PROJECT_DIR" || exit 1

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    open "$URL"
    exit 0
  else
    rm -f "$PID_FILE"
  fi
fi

nohup python3 server.py 8000 > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

for i in {1..30}; do
  if curl -s "$URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

open "$URL"
