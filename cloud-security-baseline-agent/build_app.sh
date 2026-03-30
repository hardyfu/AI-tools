#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/ryan/Desktop/pythoncode/.venv/bin/python3}"
APP_PATH="$PROJECT_ROOT/dist/Cloud Security Baseline Agent.app"
BUILD_PATH="$PROJECT_ROOT/build"

cd "$PROJECT_ROOT"

"$PYTHON_BIN" -m pip install py2app

rm -rf "$APP_PATH" "$BUILD_PATH"
"$PYTHON_BIN" setup.py py2app

echo "Built app:"
echo "$PROJECT_ROOT/dist/Cloud Security Baseline Agent.app"
