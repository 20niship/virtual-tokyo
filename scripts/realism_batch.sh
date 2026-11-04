#!/bin/zsh
round=$1
for job in ${=2}; do
  spot=${job%%:*}; tm=${job##*:}
  echo "== $spot $tm"
  uv run python scripts/build_realism.py $spot --round $round --time $tm 2>&1 | grep -E "^total|Error|Trace"
done
echo ALLDONE
