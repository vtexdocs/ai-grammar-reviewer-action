#!/bin/bash
set -e

cd /github/workspace
python /action/grammar_reviewer.py
if [ -f issues.json ]; then
  python /action/generate_rdjsonl.py
else
  echo "No issues found, skipping RDJSONL generation."
fi
if [ -f suggestions.rdjsonl ]; then
  if [ -n "$PR_NUMBER" ] && [ -n "$PR_HEAD_REF" ] && [ -n "$GITHUB_REPOSITORY" ]; then
    HEAD_REF="${PR_HEAD_REF#refs/heads/}"
    BASE_REF="${PR_BASE_REF:-main}"
    HEAD_SHA="${PR_HEAD_SHA:-$GITHUB_SHA}"
    EVENT_FILE="/tmp/pull_request_event.json"
    REPO_OWNER="${GITHUB_REPOSITORY%%/*}"
    REPO_NAME="${GITHUB_REPOSITORY#*/}"
    cat > "$EVENT_FILE" << EOF
{
"pull_request": {
  "number": $PR_NUMBER,
  "head": {"ref": "$HEAD_REF", "sha": "$HEAD_SHA"},
  "base": {"ref": "$BASE_REF"}
},
"repository": {
  "name": "$REPO_NAME",
  "full_name": "$GITHUB_REPOSITORY",
  "owner": {
    "login": "$REPO_OWNER"
  }
}
}
EOF
    export GITHUB_EVENT_PATH="$EVENT_FILE"
    export GITHUB_EVENT_NAME="pull_request"
  fi
  reviewdog -f=rdjsonl -name="Grammar reviewer" -reporter=github-pr-review -filter-mode=nofilter < suggestions.rdjsonl
else
  echo "No suggestions found, skipping reviewdog."
fi