#!/usr/bin/env bash

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/anthropics/skills.git}"
REPO_REF="${REPO_REF:-main}"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="${TARGET_DIR:-$CODEX_HOME_DIR/skills}"
usage() {
  cat <<'EOF'
Usage: update_anthropic_skills.sh

Sync Anthropic skills from GitHub into ~/.codex/skills.

Environment overrides:
  REPO_URL   Git repo to sync from. Default: https://github.com/anthropics/skills.git
  REPO_REF   Git ref to sync. Default: main
  CODEX_HOME Codex home directory. Default: ~/.codex
  TARGET_DIR Destination skills directory. Default: $CODEX_HOME/skills
EOF
}

while (($#)); do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

for cmd in git rsync mktemp; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/anthropic-skills.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

REPO_DIR="$TMP_DIR/repo"
UPSTREAM_DIR="$REPO_DIR/skills"

echo "Cloning $REPO_URL ($REPO_REF)..."
git clone --depth 1 --branch "$REPO_REF" --filter=blob:none --sparse "$REPO_URL" "$REPO_DIR" >/dev/null
git -C "$REPO_DIR" sparse-checkout set skills

mkdir -p "$TARGET_DIR"

echo "Syncing skills into $TARGET_DIR..."
while IFS= read -r upstream_skill; do
  skill_name="$(basename "$upstream_skill")"
  target_skill="$TARGET_DIR/$skill_name"

  rm -rf "$target_skill"
  rsync -a "$upstream_skill/" "$target_skill/"
  echo "Updated: $skill_name"
done < <(find "$UPSTREAM_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

echo "Cleaning local skills not present upstream..."
while IFS= read -r local_skill; do
  skill_name="$(basename "$local_skill")"

  [[ "$skill_name" == ".system" ]] && continue
  [[ "$skill_name" == custom_* ]] && continue

  if [[ ! -d "$UPSTREAM_DIR/$skill_name" ]]; then
    rm -rf "$local_skill"
    echo "Removed: $skill_name"
  fi
done < <(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

echo "Done."
echo "Restart Codex to pick up skill changes."
