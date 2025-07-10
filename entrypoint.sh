#!/bin/bash
set -e

python grammar_reviewer.py
python generate_rdjsonl.py
reviewdog -f=rdjsonl -name="Grammar reviewer" -reporter=github-pr-review -filter-mode=nofilter < suggestions.rdjsonl