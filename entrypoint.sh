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
  reviewdog -f=rdjsonl -name="Grammar reviewer" -reporter=github-pr-review -filter-mode=nofilter < suggestions.rdjsonl
else
  echo "No suggestions found, skipping reviewdog."
fi