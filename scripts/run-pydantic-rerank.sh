#!/usr/bin/env bash
# The pydantic-only reranker arm, with every flag that changes the result pinned here
# rather than retyped. Two reasons this is a script and not a command in a note:
#
#   1. The invocation is 250 characters, and a wrapped paste is a silent way to run
#      something slightly different from what was measured.
#   2. `--rerank-cache` and `--repos` are what make the run RESUMABLE. Rerun this exact
#      line after an interrupt and it continues from the last checkpoint; drop the cache
#      flag by accident and it starts from zero, having looked identical.
#
# Usage:  bash scripts/run-pydantic-rerank.sh [device] [batch]
#   bash scripts/run-pydantic-rerank.sh mps 64      # the laptop; 64 measured fastest there
#   bash scripts/run-pydantic-rerank.sh cuda 256    # a GPU box; run the throughput probe first
#
# `pydantic/pydantic` is 41.8 of the arm's 55.1 priced hours. The other four repos are
# already scored -- see data/scores/retrieval-rerank-top20-no-pydantic.json -- so this is
# the only split that still costs anything.
set -euo pipefail

DEVICE="${1:-mps}"
BATCH="${2:-64}"
CACHE=".cache/rerank/pydantic-only-800-100.npz"
OUT="data/scores/retrieval-rerank-top20-pydantic.json"

# Refuse to be the second copy. On 2026-09-23 two of these ran for 90 seconds at once --
# one started from a terminal, one launched detached -- and that is worse than it sounds:
# both load the same banked cache, score overlapping pairs, and then each writes the whole
# store back over the other's, so whichever saves last DISCARDS the other's interval. The
# atomic rename means no corrupt file and therefore no symptom; the only trace is a pair
# count that grew more slowly than the GPU time says it should have. It also doubles the
# memory footprint on a laptop that has been killed once for exactly that.
# Matched on the venv path, which appears in the worker's argv but not in the `uv run`
# wrapper's, so this counts real scorers rather than launchers.
if pgrep -f "bin/driftwood retrieve-eval" >/dev/null 2>&1; then
    echo "REFUSING: a reranker run is already going --"
    # `ps -p` rather than `pgrep -a`, which is a GNU extension: on macOS the -a is
    # accepted and ignored, printing bare pids and losing the elapsed time that tells
    # you whether the other run is minutes or hours in.
    ps -p "$(pgrep -f 'bin/driftwood retrieve-eval' | tr '\n' ',' | sed 's/,$//')" \
        -o pid,etime,time,%cpu 2>/dev/null | sed 's/^/    /'
    echo
    echo "Two copies silently overwrite each other's progress. Let that one finish, or"
    echo "stop it first:  pkill -f 'bin/driftwood retrieve-eval'"
    exit 1
fi

if [ -f "$CACHE" ]; then
    echo "resuming from $CACHE ($(du -h "$CACHE" | cut -f1) of banked pair scores)"
else
    echo "no cache at $CACHE -- starting from zero"
fi
echo "device=$DEVICE batch=$BATCH out=$OUT"
echo

exec uv run driftwood retrieve-eval data/labels-v11.jsonl \
    --out "$OUT" \
    --rerank-model \
    --rerank-device "$DEVICE" \
    --rerank-batch "$BATCH" \
    --rerank-cache "$CACHE" \
    --repos pydantic/pydantic
