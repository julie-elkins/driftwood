"""Every sha a label references is present in the clone, or this exits nonzero.

Written for the case that motivated it: moving a run to a rented GPU box means
re-cloning the repo there rather than uploading 447MB, and a fresh clone is not
guaranteed to carry what the mined clone carried. A force-push, a deleted branch or
a repo that rewrote history drops commits that were reachable in September and are
not reachable now.

The reason that needs a guard rather than a glance is in `dataset.py:238`: a repo the
clone cannot serve has its queries recorded as **"absent, not failed"**. So a clone
missing 30 of 524 shas does not crash and does not warn loudly -- it produces a
smaller query set, macro-averages over it, and prints a result that looks exactly
like the one it should have printed. Comparing that number to the four repos scored
against the full clone would be comparing two different corpora.

    uv run python scripts/verify_clone_shas.py data/labels-v11.jsonl --repos pydantic/pydantic

Exit 0 means every referenced sha resolves to a commit. Exit 1 names what is missing
and how many, which is the only useful thing to know before spending GPU hours.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Mirrors the miner's own reader rather than guessing: a label record names its sha in
# `at_sha`, and the older ones used `sha`. Both are checked so an older label file does
# not silently verify zero shas and report success.
SHA_FIELDS = ("at_sha", "sha", "commit")


def local_name_for(slug: str) -> str:
    """The same directory name `gitio.local_name_for` produces, by the same rule."""
    from driftwood.mining.gitio import local_name_for as upstream

    return upstream(slug)


def shas_by_repo(labels: Path, repos: set[str] | None) -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for line in labels.open():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        repo = record.get("repo")
        if not repo or (repos and repo not in repos):
            continue
        for field in SHA_FIELDS:
            value = record.get(field)
            if value:
                found[repo].add(value)
    return dict(found)


def missing_shas(clone: Path, shas: set[str]) -> list[str]:
    """Which of `shas` the clone cannot resolve to a commit.

    One `git cat-file --batch-check` for the whole set rather than a process per sha:
    524 shas is 524 forks otherwise, and this runs before a GPU meter starts.
    `^{commit}` is appended so a sha that resolves to a tree or a tag -- which would
    pass a bare existence check and then fail the actual read -- is reported missing
    here instead of an hour in.
    """
    if not shas:
        return []
    ordered = sorted(shas)
    probe = "\n".join(f"{sha}^{{commit}}" for sha in ordered) + "\n"
    result = subprocess.run(
        ["git", "--git-dir", str(clone), "cat-file", "--batch-check"],
        input=probe,
        capture_output=True,
        text=True,
    )
    # Lines come back in the order sent, so they zip against `ordered`. A present
    # object prints "<sha> commit <size>"; a missing one prints "<what was asked>
    # missing" -- which for our input is "<sha>^{commit} missing".
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if len(lines) != len(ordered):
        # Rather than mis-zip and report the wrong shas as missing, refuse. A
        # mismatch here means git answered in a shape this parser does not know.
        raise RuntimeError(
            f"git returned {len(lines)} lines for {len(ordered)} shas; "
            f"stderr={result.stderr.strip()[:400]!r}"
        )
    return [
        sha for sha, line in zip(ordered, lines, strict=True) if "missing" in line.split()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument(
        "--repos",
        nargs="+",
        default=[],
        help="restrict to these slugs; default is every repo the label file names",
    )
    args = parser.parse_args()

    wanted = shas_by_repo(args.labels, set(args.repos) or None)
    if not wanted:
        print(
            f"no labels matched in {args.labels}"
            + (f" for {args.repos}" if args.repos else ""),
            file=sys.stderr,
        )
        return 2

    failed = False
    for repo in sorted(wanted):
        shas = wanted[repo]
        clone = args.clone_root / local_name_for(repo)
        if not (clone / "HEAD").exists():
            print(f"FAIL {repo}: no clone at {clone}")
            failed = True
            continue
        gone = missing_shas(clone, shas)
        if gone:
            print(f"FAIL {repo}: {len(gone)} of {len(shas)} shas missing from {clone}")
            for sha in gone[:10]:
                print(f"       {sha}")
            if len(gone) > 10:
                print(f"       ... and {len(gone) - 10} more")
            failed = True
        else:
            print(f"ok   {repo}: all {len(shas)} shas present")

    if failed:
        print(
            "\nDo not start the run. A missing sha does not error -- dataset.py records "
            "its queries as absent, so the result would be measured on a smaller corpus "
            "than the repos it gets compared against.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
