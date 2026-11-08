#!/bin/sh
# near / far / legacy の 3 プロファイルを同じ地形でレンダし、ポリゴン数・インスタンス数・時間を out/terra/closeup/stats_*.jsonl に記録する
D=${1:-out/terra/closeup/v2k}
O=${2:-out/terra/closeup}
rm -f $O/stats_near.jsonl $O/stats_far.jsonl $O/stats_legacy.jsonl
uv run python scripts/terra_render.py $D --view near --detail near -o $O/after --name after --samples 32 --stats $O/stats_near.jsonl
uv run python scripts/terra_render.py $D --view oblique ground --detail far --hi-dist 90 -o $O/far --name far --samples 32 --stats $O/stats_far.jsonl
uv run python scripts/terra_render.py $D --view oblique ground --detail legacy -o $O/legacy --name legacy --samples 32 --stats $O/stats_legacy.jsonl
echo ALLDONE
