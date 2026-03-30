#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="/Users/ryan/Desktop/pythoncode/.venv/bin/python3"
AGENT_SCRIPT="$SCRIPT_DIR/baseline_agent.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python interpreter: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -f "$AGENT_SCRIPT" ]]; then
  echo "Missing agent script: $AGENT_SCRIPT" >&2
  exit 1
fi

cd "$SCRIPT_DIR"

print_help() {
  cat <<'EOF'
Usage:
  ./baseline_cli.sh
  ./baseline_cli.sh gui
  ./baseline_cli.sh bootstrap --case <case_name>
  ./baseline_cli.sh stage-input --case <case_name> --target global_policy --file /abs/path/to/file.pdf
  ./baseline_cli.sh stage-input --case <case_name> --target third_party_standard --file /abs/path/to/file.pdf
  ./baseline_cli.sh run --case <case_name>
  ./baseline_cli.sh validate-case --case <case_name>
  ./baseline_cli.sh validate-all-cases

Notes:
  - Run without arguments to use interactive menu mode.
  - Use "gui" to open the desktop window explicitly.
  - Any explicit arguments are passed through to baseline_agent.py.
EOF
}

run_agent() {
  "$PYTHON_BIN" "$AGENT_SCRIPT" "$@"
}

prompt_required() {
  local label="$1"
  local value=""
  while [[ -z "$value" ]]; do
    printf "%s: " "$label"
    IFS= read -r value
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
  done
  printf "%s" "$value"
}

interactive_menu() {
  local choice=""
  echo "Cloud Security Baseline Agent CLI"
  echo "1. Open GUI"
  echo "2. Bootstrap case"
  echo "3. Stage global policy"
  echo "4. Stage third-party standard"
  echo "5. Run case pipeline"
  echo "6. Validate single case"
  echo "7. Validate all cases"
  echo "8. Exit"
  printf "Select an option [1-8]: "
  IFS= read -r choice

  case "$choice" in
    1)
      run_agent
      ;;
    2)
      local case_name
      case_name="$(prompt_required "Case name")"
      run_agent bootstrap --case "$case_name"
      ;;
    3)
      local case_name file_path
      case_name="$(prompt_required "Case name")"
      file_path="$(prompt_required "Global policy file path")"
      run_agent stage-input --case "$case_name" --target global_policy --file "$file_path"
      ;;
    4)
      local case_name file_path
      case_name="$(prompt_required "Case name")"
      file_path="$(prompt_required "Third-party standard file path")"
      run_agent stage-input --case "$case_name" --target third_party_standard --file "$file_path"
      ;;
    5)
      local case_name
      case_name="$(prompt_required "Case name")"
      run_agent run --case "$case_name"
      ;;
    6)
      local case_name
      case_name="$(prompt_required "Case name")"
      run_agent validate-case --case "$case_name"
      ;;
    7)
      run_agent validate-all-cases
      ;;
    8)
      exit 0
      ;;
    *)
      echo "Invalid option: $choice" >&2
      exit 1
      ;;
  esac
}

if [[ $# -eq 0 ]]; then
  interactive_menu
  exit 0
fi

if [[ "$1" == "help" || "$1" == "--help" || "$1" == "-h" ]]; then
  print_help
  exit 0
fi

if [[ "$1" == "gui" ]]; then
  exec "$PYTHON_BIN" "$AGENT_SCRIPT"
fi

exec "$PYTHON_BIN" "$AGENT_SCRIPT" "$@"
