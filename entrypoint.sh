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
  if [ -n "$PR_NUMBER" ] && [ -n "$GITHUB_REPOSITORY" ]; then
    export CI_PULL_REQUEST="https://github.com/$GITHUB_REPOSITORY/pull/$PR_NUMBER"
  fi
  reviewdog -f=rdjsonl -name="Grammar reviewer" -reporter=github-pr-review -filter-mode=nofilter < suggestions.rdjsonl
else
  echo "No suggestions found, skipping reviewdog."
fi