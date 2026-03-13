#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: push_with_comment.sh [commit message]

Safely syncs the current branch with its upstream, stages local changes,
creates a commit with your message, and pushes. If no commit message is
provided, the script will prompt for one.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

cd "$REPO_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository: $REPO_DIR" >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
if [[ -z "$current_branch" ]]; then
  echo "Detached HEAD is not supported by this script." >&2
  exit 1
fi

echo "Repository: $REPO_DIR"
echo "Branch: $current_branch"

upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [[ -z "$upstream_ref" ]]; then
  echo "No upstream is configured for $current_branch." >&2
  echo "Set one with: git branch --set-upstream-to origin/$current_branch" >&2
  exit 1
fi

echo "Fetching latest upstream..."
git fetch

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Syncing upstream with rebase before commit..."
  git pull --rebase --autostash
else
  local_head="$(git rev-parse HEAD)"
  upstream_head="$(git rev-parse "$upstream_ref")"
  if [[ "$local_head" != "$upstream_head" ]]; then
    echo "Branch is behind upstream. Rebasing before commit..."
    git pull --rebase
  fi
fi

echo "Staging changes..."
git add -A

if git diff --cached --quiet; then
  echo "No local changes to commit."
  echo "Pushing current branch state..."
  git push
  echo "Done."
  exit 0
fi

commit_message="${1:-}"
if [[ -z "$commit_message" ]]; then
  printf "Commit message: "
  IFS= read -r commit_message
fi

if [[ -z "$commit_message" ]]; then
  echo "Commit message cannot be empty." >&2
  exit 1
fi

echo "Staged summary:"
git diff --cached --stat

echo "Creating commit..."
git commit -m "$commit_message"

echo "Pushing to upstream..."
git push

echo "Done."
