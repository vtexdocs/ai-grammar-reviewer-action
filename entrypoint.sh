#!/bin/bash
set -e

cd /github/workspace
ls -l
python /action/grammar_reviewer.py
if [ -f issues.json ]; then
  python /action/generate_rdjsonl.py
fi
if [ -f suggestions.rdjsonl ]; then
  reviewdog -f=rdjsonl -name="Grammar reviewer" -reporter=github-pr-review -filter-mode=nofilter < suggestions.rdjsonl
fi