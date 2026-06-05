#!/bin/bash
# 🤖 SWMAS Auto-Push Script
# Usage: ./auto_push.sh [message]

REPO_DIR="/root/.openclaw/workspace"
cd "$REPO_DIR" || exit 1

# Check if there are changes
if git diff --quiet && git diff --cached --quiet; then
    echo "📭 No changes to push"
    exit 0
fi

# Default message
MESSAGE="${1:-🤖 Auto-update: $(date +%Y-%m-%d_%H:%M)}"

# Add, commit, push
git add -A
git commit -m "$MESSAGE" --quiet
git push origin master --quiet

echo "✅ Pushed: $MESSAGE"
