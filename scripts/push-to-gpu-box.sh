#!/usr/bin/env bash
# Copy the two things a rented GPU box cannot rebuild, after checking it can be reached.
#
# This asks for the host rather than taking it as an argument, and that is deliberate.
# The earlier version of this was a block with `PASTE_HOST_HERE` in it, pasted whole
# twice -- a command block that needs a hand-edit before it is safe to run is a broken
# deliverable, because the whole block gets copied. Nothing here needs editing.
#
# Usage:
#   bash scripts/push-to-gpu-box.sh
#
# What gets copied, and why only these two:
#   - the working tree (~30MB) -- NOT a git clone, because the 15-minute checkpoint fix
#     in rerank.py is uncommitted, and `origin/main` equals local HEAD. A box that
#     cloned from GitHub would run the version that loses everything on a crash.
#   - .cache/rerank/pydantic-only-800-100.npz (276MB) -- 14 hours of spent GPU time.
# Everything else rebuilds there: .venv via `uv sync`, the clone via `git clone --bare`.
set -euo pipefail

cd "$(dirname "$0")/.."

CACHE=".cache/rerank/pydantic-only-800-100.npz"
LABELS="data/labels-v11.jsonl"

# Set explicitly rather than inherited. A stale RSYNC_RSH in the calling shell -- which
# a previous attempt at this may well have left behind -- would silently send the
# transfer at the wrong port.
unset RSYNC_RSH

printf '\n'
printf 'Rent the box first if you have not: a RunPod / Lambda Labs / Vast.ai L4 or\n'
printf 'A10G, PyTorch template, 60GB+ disk. Use a personal account you pay for, not\n'
printf 'an employer-provided one. The Connect panel gives the host and port.\n'
printf '\n'

# `read -r -p` and not zsh's `read "VAR?prompt"`, which in bash would create a variable
# whose NAME contains the prompt text and never ask anything.
read -r -p "SSH host (user@address, blank to cancel): " HOSTPART
if [ -z "${HOSTPART:-}" ]; then
    printf '\ncancelled -- nothing copied.\n'
    exit 0
fi
read -r -p "SSH port [22]: " PORTPART
PORTPART="${PORTPART:-22}"

case "$HOSTPART" in
    *PASTE*|*HOST*|*paste*|*your-host*)
        printf '\n"%s" still looks like a placeholder. Stopping rather than\n' "$HOSTPART"
        printf 'failing six commands deep. Re-run with the real host.\n'
        exit 1
        ;;
esac

SSHCMD="ssh -p $PORTPART -o ConnectTimeout=15 -o BatchMode=yes"

printf '\n=== the two things that must travel\n'
fatal=0
for f in "$LABELS" "$CACHE"; do
    if [ -f "$f" ]; then
        printf 'ok   %-46s %s\n' "$f" "$(du -h "$f" | cut -f1)"
    else
        printf 'MISSING %s\n' "$f"
        fatal=1
    fi
done
[ "$fatal" -eq 0 ] || { printf '\nrefusing to continue\n'; exit 1; }

# Reachability before payload. A 276MB transfer that dies on authentication after two
# minutes is the same wasted time as the placeholder was, just quieter about it.
printf '\n=== can the box be reached\n'
if ! $SSHCMD "$HOSTPART" true 2>/dev/null; then
    printf 'cannot open an SSH session to %s on port %s.\n\n' "$HOSTPART" "$PORTPART"
    printf 'Most likely: the pod is not running yet, the port is not 22 (RunPod\n'
    printf 'usually assigns a high one), or your key is not on the box. BatchMode is\n'
    printf 'on, so a password prompt counts as a failure here -- add your key to the\n'
    printf 'provider first. Nothing was copied.\n'
    exit 1
fi
printf 'ok   %s reachable, and it reports:\n' "$HOSTPART"
$SSHCMD "$HOSTPART" 'nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "  (no nvidia-smi -- if this box has no GPU there is no reason to use it)"' | sed 's/^/     /'

printf '\n=== copying\n'
$SSHCMD "$HOSTPART" "mkdir -p driftwood/.cache/rerank"
rsync -avh --partial --info=progress2 -e "$SSHCMD" \
    --exclude .venv --exclude .cache --exclude .git \
    ./ "$HOSTPART:driftwood/"
# --partial so an interrupted 276MB transfer resumes instead of restarting, for the same
# reason the pair cache checkpoints at all.
rsync -avh --partial --info=progress2 -e "$SSHCMD" \
    "$CACHE" "$HOSTPART:driftwood/.cache/rerank/"

# The cache is checked and the source tree is not, because the consequences differ. A
# corrupt .py fails immediately and loudly; a truncated cache fails the stamp check on
# the box AFTER the pod is running and being charged for -- or worse, loads a short file
# and silently re-scores pairs that were already paid for.
printf '\n=== verifying the cache arrived intact\n'
LOCAL_SUM="$(shasum -a 256 "$CACHE" | awk '{print $1}')"
# `sha256sum` on Linux, `shasum -a 256` on macOS; the box could be either, so try the
# Linux name first and fall back. `awk '{print $1}'` isolates the hash, because both
# tools print "<hash>  <filename>" and the filenames differ between the two machines.
REMOTE_SUM="$(
    $SSHCMD "$HOSTPART" \
        'f=driftwood/.cache/rerank/pydantic-only-800-100.npz
         if command -v sha256sum >/dev/null 2>&1; then sha256sum "$f"
         else shasum -a 256 "$f"; fi' 2>/dev/null | awk '{print $1}'
)"

printf '  local : %s\n' "$LOCAL_SUM"
printf '  remote: %s\n' "${REMOTE_SUM:-<no answer from the box>}"
if [ -z "$REMOTE_SUM" ]; then
    printf '\nCould not hash the file on the box. Do not start the run until this is\n'
    printf 'resolved -- an unverified cache is the one artefact worth 14 hours.\n'
    exit 1
fi
if [ "$LOCAL_SUM" != "$REMOTE_SUM" ]; then
    printf '\nMISMATCH. The copy on the box is not the file that left here. Re-run this\n'
    printf 'script -- rsync --partial will resume rather than restart. Do NOT run the\n'
    printf 'scoring against it: a short cache re-scores pairs already paid for.\n'
    exit 1
fi
printf 'ok   identical -- 8,034,228 banked pair scores made it across\n'

printf '\n=== done. On the box:\n\n'
printf '    ssh -p %s %s\n' "$PORTPART" "$HOSTPART"
printf '    cd driftwood\n'
printf '    bash scripts/gpu-box-setup.sh\n\n'
printf 'That installs from the lockfile, verifies all 524 labelled shas are in the\n'
printf 'fresh clone, then probes batch sizes and stops with a recommendation.\n'
