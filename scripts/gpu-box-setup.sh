#!/usr/bin/env bash
# Bring a rented GPU box to the point where the pydantic reranker arm can resume, and
# refuse to start it if anything about the box would change the measurement.
#
# The laptop does 161 pairs/sec and 16.6M pairs remain, which is 28.6 hours. An L4 or
# A10G does this in 2-3. The whole reason that trade is available is that the banked
# cache is only 276MB, so the expensive thing travels and the cheap things rebuild.
#
# Usage, from the repo root on the box:
#   bash scripts/gpu-box-setup.sh              # set up, verify, probe, then stop
#   bash scripts/gpu-box-setup.sh 256          # set up, verify, and run at batch 256
#
# Run it with no argument first. It ends by printing the measured best batch size, and
# on CUDA that is genuinely not knowable in advance -- on this laptop's MPS the FASTEST
# setting is 64 and every larger one is worse, which is the opposite of the usual
# advice, so the number gets measured on each device rather than carried between them.
#
# WHAT THIS DELIBERATELY DOES NOT DO: run on an account that is not yours. Rent the box
# on a personal account you pay for -- RunPod, Lambda Labs, Vast.ai, or your own AWS. A
# 42-hour GPU job billed to an employer's account is somebody else's money and somebody
# else's audit trail, and this repository has no business putting either at risk.
set -euo pipefail

BATCH="${1:-}"
CACHE=".cache/rerank/pydantic-only-800-100.npz"
LABELS="data/labels-v11.jsonl"
CLONE_ROOT=".cache/clones"

say() { printf '\n=== %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. The two things that had to be copied, because neither can be rebuilt here.
# ---------------------------------------------------------------------------
# The cache is 14 hours of already-spent GPU time and the label file is the corpus.
# Re-mining labels on the box would risk a DIFFERENT corpus, which would make this
# repo's number incomparable with the four already scored -- so it is copied, never
# regenerated. Checked before the dependency install so a missing file costs seconds
# rather than a torch download.
say "checking what had to be copied"
fatal=0
if [ ! -f "$LABELS" ]; then
    echo "MISSING $LABELS -- rsync it from the laptop; do NOT re-mine it here"
    fatal=1
else
    echo "ok   $LABELS ($(wc -l < "$LABELS" | tr -d ' ') labels)"
fi
if [ ! -f "$CACHE" ]; then
    echo "MISSING $CACHE -- without it this run re-pays the 14 hours already spent"
    fatal=1
else
    echo "ok   $CACHE ($(du -h "$CACHE" | cut -f1) of banked pair scores)"
fi
[ "$fatal" -eq 0 ] || { echo; echo "refusing to continue"; exit 1; }

# ---------------------------------------------------------------------------
# 2. The GPU. Reported, not assumed.
# ---------------------------------------------------------------------------
say "device"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
else
    echo "no nvidia-smi found. If this box has no CUDA GPU there is no reason to be on"
    echo "it -- the laptop is faster than a rented CPU. Stopping."
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Dependencies.
# ---------------------------------------------------------------------------
# uv.lock already carries manylinux x86_64 wheels for torch 2.14 + cp312, and PyPI's
# Linux torch bundles CUDA, so the pinned lockfile resolves to a CUDA build with no
# extra index. `--frozen` so the lockfile is obeyed rather than re-resolved: a different
# torch here would be a second uncontrolled variable in a measurement run.
say "installing dependencies from the lockfile"
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --frozen --extra embed

say "torch sees"
uv run python -c "
import torch
print(f'  torch {torch.__version__}, cuda available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  device: {torch.cuda.get_device_name(0)}')
else:
    raise SystemExit('torch cannot see the GPU -- stopping rather than running on CPU')
"

# ---------------------------------------------------------------------------
# 4. The clone, and the check that makes re-cloning safe.
# ---------------------------------------------------------------------------
# Bare, because every read goes through git plumbing against a commit-ish; that is what
# `ensure_clone` builds and what `(dest/HEAD).exists()` tests for.
say "clone"
DEST="$CLONE_ROOT/pydantic__pydantic"
if [ -f "$DEST/HEAD" ]; then
    echo "ok   already present at $DEST"
else
    mkdir -p "$CLONE_ROOT"
    echo "cloning pydantic/pydantic (bare, full history -- a shallow clone cannot serve"
    echo "the 524 historical shas the labels point into)"
    git clone --bare https://github.com/pydantic/pydantic "$DEST"
fi

# This is the step that makes the whole re-clone-instead-of-upload trade safe. A fresh
# clone is not guaranteed to carry what September's clone carried, and a repo whose
# clone cannot serve a sha has its queries recorded as ABSENT rather than failed
# (dataset.py:238) -- so a partial clone yields a quietly smaller corpus and a result
# that looks right. Verified against the full set on the laptop: all 524 present.
say "verifying every labelled sha is present"
uv run python scripts/verify_clone_shas.py "$LABELS" --repos pydantic/pydantic

# ---------------------------------------------------------------------------
# 5. Measure, then run.
# ---------------------------------------------------------------------------
if [ -z "$BATCH" ]; then
    say "throughput probe"
    uv run python scripts/rerank_throughput.py --device cuda --batches 64 128 256 512 1024
    cat <<'EOF'

Setup is done and the clone is verified. Re-run with the best batch size above:

    bash scripts/gpu-box-setup.sh <batch>

It checkpoints every 15 minutes, so an interrupt costs at most that.
EOF
    exit 0
fi

say "running at batch $BATCH"
exec bash scripts/run-pydantic-rerank.sh cuda "$BATCH"
