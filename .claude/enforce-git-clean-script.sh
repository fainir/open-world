#!/usr/bin/env bash
# Stop hook: prevent stopping with uncommitted/unpushed work in tracked files.
#
# Why: the user previously lost work because Claude made changes and didn't
# commit/push them. Local-only changes are not durable. This hook treats
# uncommitted modifications and unpushed commits as a hard block.
#
# What it blocks on:
#   - Modified TRACKED files (Claude edited a file in the repo, didn't commit)
#   - Unpushed commits (committed locally but not pushed to remote)
#
# What it does NOT block on:
#   - Untracked files (user's responsibility — could be junk or intentional)
#   - .gitignored files
#   - Repos with no remote (can't push; warns instead)
#
# Exit 2 = block with instruction. Exit 0 = allow stop.

set -euo pipefail

# Find project root (nearest .git dir walking up)
find_git_root() {
  local dir="${PWD}"
  while [ "$dir" != "/" ]; do
    [ -d "$dir/.git" ] && echo "$dir" && return 0
    dir="$(dirname "$dir")"
  done
  return 1
}

ROOT="$(find_git_root 2>/dev/null || true)"
[ -z "$ROOT" ] && exit 0  # not in a git repo, nothing to enforce

cd "$ROOT" || exit 0

# Skip very short sessions (single Q&A)
if [ "${CLAUDE_TRANSCRIPT_LENGTH:-0}" -lt 500 ] 2>/dev/null; then
  exit 0
fi

# Check 1: modified tracked files (staged or unstaged, but excluding untracked)
MODIFIED=$(git diff --name-only HEAD 2>/dev/null | head -20)
MODIFIED_COUNT=$(echo "$MODIFIED" | grep -c . 2>/dev/null || echo 0)
MODIFIED_COUNT="${MODIFIED_COUNT//[^0-9]/}"; MODIFIED_COUNT="${MODIFIED_COUNT:-0}"

# Check 2: unpushed commits (only if a tracking branch exists)
UNPUSHED=0
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  UNPUSHED=$(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0)
  UNPUSHED="${UNPUSHED//[^0-9]/}"; UNPUSHED="${UNPUSHED:-0}"
fi

# Decide
if [ "$MODIFIED_COUNT" -gt 0 ] || [ "$UNPUSHED" -gt 0 ]; then
  REASON="UNCOMMITTED/UNPUSHED WORK in $ROOT - user has lost work before from this."
  ACTION=""
  if [ "$MODIFIED_COUNT" -gt 0 ]; then
    SAMPLE=$(echo "$MODIFIED" | head -3 | tr '\n' ',' | sed 's/,$//')
    REASON="$REASON Modified tracked files: $MODIFIED_COUNT (e.g. $SAMPLE)."
    ACTION="git add the modified files, commit with a meaningful message, then push. "
  fi
  if [ "$UNPUSHED" -gt 0 ]; then
    REASON="$REASON Unpushed commits: $UNPUSHED."
    ACTION="${ACTION}git push to the remote. "
  fi

  # Check if remote exists; if not, give clear guidance
  if ! git remote get-url origin >/dev/null 2>&1; then
    REASON="$REASON NO REMOTE CONFIGURED — ask the user if they want one created (gh repo create) so work can be pushed."
    ACTION="Create or wire up a remote, then push. Until then, do NOT stop."
  fi

  cat << BLOCK
{
  "decision": "block",
  "reason": "$REASON Your next action: ${ACTION}Do NOT output text without a tool call - commit and push first."
}
BLOCK
  exit 2
fi

exit 0
