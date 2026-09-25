#!/usr/bin/env bash
# How far the pydantic reranker arm has got, and what finishing it still costs.
#
#   bash scripts/rerank-progress.sh
#
# Reads the cache rather than the log, because the log reports what the run SAID and the
# cache is what the run BANKED -- and only the second survives a kill. The count comes
# from the file, so this is also the honest answer to "did the checkpoint actually land".
set -euo pipefail

cd "$(dirname "$0")/.."

CACHE=".cache/rerank/pydantic-only-800-100.npz"
OUT="data/scores/retrieval-rerank-top20-pydantic.json"

if pgrep -f "bin/driftwood retrieve-eval" >/dev/null 2>&1; then
    echo "RUNNING:"
    ps -p "$(pgrep -f 'bin/driftwood retrieve-eval' | tr '\n' ',' | sed 's/,$//')" \
        -o pid,etime,time,%cpu,rss 2>/dev/null | sed 's/^/  /'
else
    echo "STOPPED -- nothing is scoring right now."
fi

if [ ! -f "$CACHE" ]; then
    echo "no cache at $CACHE"
    exit 0
fi

echo
echo "last checkpoint: $(date -r "$CACHE" '+%Y-%m-%d %H:%M:%S')  ($(du -h "$CACHE" | cut -f1))"
# Anything since that timestamp is unbanked and dies with the process. Printed because
# it is the whole cost of pausing, and 15 minutes is its ceiling by construction.
echo "  work since then is NOT banked -- capped at 15 minutes by the checkpoint interval"

uv run python -c "
import numpy as np
# Derived, not counted: the arm's priced total less the four cheap repos already cached.
TOTAL = 24_625_841
with np.load('$CACHE', allow_pickle=False) as h:
    n = len(h['keys'])
left = TOTAL - n
print()
print(f'banked    : {n:,} pair scores  ({n/TOTAL:.1%} of pydantic)')
print(f'remaining : {left:,}')
print()
# 161/sec is measured on this laptop at batch 64, which is its FASTEST setting; the GPU
# figures are vendor-class estimates and deliberately labelled as such.
print(f'  laptop  (161/sec, measured) : {left/161/3600:>5.1f}h')
print(f'  L4      (~1500/sec, est)    : {left/1500/3600:>5.1f}h')
print(f'  A10G    (~2500/sec, est)    : {left/2500/3600:>5.1f}h')
"

echo
if [ -f "$OUT" ]; then
    echo "SCORED: $OUT exists -- the arm finished. Read it against the five"
    echo "pre-registered predictions, per repo, never pooled."
else
    echo "$OUT does not exist yet, so there is no result to read."
fi
