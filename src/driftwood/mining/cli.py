"""Command line entry point for the label miner.

Stdlib argparse and no dependencies at all, on purpose: this stage of the project
contains no AI, and keeping its dependency count at zero means the label set can
be regenerated on any machine, in CI, years from now, without resolving an
inference stack. The dependency budget gets spent later, where it buys something.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .gitio import ensure_clone, file_diff, head_sha
from .labels import LABEL_DRIFT, MineConfig, mine_repo
from .scoring import format_report, format_retention, parse_sheet, retention, score

DEFAULT_REPOS = ["psf/requests", "pallets/flask", "encode/httpx"]
DEFAULT_CLONES = Path(".cache/clones")
DEFAULT_LABELS = Path("data/labels.jsonl")

# What the reviewer is asked to choose from. The point of a taxonomy rather than
# a yes/no is that the error *modes* tell you what to fix; a bare accuracy number
# does not.
VERDICTS = {
    "drift": "the doc said something untrue about the code, and this commit corrected it",
    "new": "the doc was documenting something that did not exist yet (feature + its docs)",
    "cosmetic": "wording, formatting or a link -- nothing factual changed",
    "unrelated": "the doc change and the code change are not about the same thing",
    "unclear": "cannot tell from these diffs alone",
}


def _manifest_path(out: Path) -> Path:
    return out.with_suffix(".manifest.json")


def _miner_revision() -> dict[str, str]:
    """The miner's own code state, for the manifest.

    Added 2026-09-18 after a bug fix silently invalidated an existing manifest's
    replay claim. The manifest pinned every repo sha and the whole rule config, which
    made it feel complete -- but the *rules* live in code, and `_VERSION_RE` was
    corrected in a way that changes which tokens are extracted. Every manifest written
    before that fix promises a byte-identical regeneration that the current code
    cannot deliver, and nothing in the file said so.

    A config dict is not a version. This is the input that was missing.
    """
    import subprocess

    root = Path(__file__).resolve().parents[3]
    try:
        rev = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", "src"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        # Running from a tarball or without git. Say so rather than omitting the key,
        # because a missing field reads as "not checked" and an absent one reads as
        # "clean" -- the same asymmetry this project keeps running into.
        return {"commit": "unknown", "src_dirty": "unknown"}
    return {"commit": rev, "src_dirty": "yes" if dirty else "no"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _cmd_mine(args: argparse.Namespace) -> int:
    cfg = MineConfig(
        max_files_in_commit=args.max_files,
        min_shared_identifiers=args.min_shared,
        min_doc_lines_changed=args.min_doc_lines,
        require_removed_identifier=args.require_removed,
        doc_literals_only=args.doc_literals_only,
        require_withdrawn_claim=args.require_withdrawn,
        drop_docs_build_paths=args.drop_docs_build_paths,
        require_symbol_beyond_version=args.require_symbol_beyond_version,
        easy_negatives_per_repo=args.easy_negatives,
    )

    # Checked before the clones, so a refusal costs nothing rather than arriving at
    # the end of a seven-minute walk. `mine` writes derived data and overwriting it is
    # normally harmless -- but `--out` defaults to the one label set in this repo that
    # predates manifests and therefore cannot be regenerated, and the usage example in
    # the README pointed straight at it. It was silently clobbered exactly that way.
    # A guard is cheaper than remembering.
    if args.out.exists() and not args.force:
        print(
            f"refusing to overwrite existing {args.out}\n"
            "  mine output is derived data, but this file may not be regenerable.\n"
            "  choose a new --out (e.g. data/labels-v10.jsonl), or pass --force.",
            file=sys.stderr,
        )
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)

    # `owner/name=sha` pins from a previous manifest. Replaying a run without these
    # mines a different commit window, because --limit counts back from HEAD.
    #
    # `--pin` was `nargs="*"` until 2026-09-18, which meant argparse kept only the LAST
    # occurrence of a repeated flag -- and the `replay` line built below emits exactly
    # the repeated form. So every manifest in this repo advertised a replay command that
    # silently un-pinned four of its five repos and mined them at a moving HEAD. No
    # error, a plausible-looking corpus, and a different one. `action="extend"` accepts
    # both spellings; the check below is the other half, because a mistyped slug was
    # equally silent -- `pins.get(slug, "HEAD")` treats a typo as "no pin requested".
    pins = dict(pin.split("=", 1) for pin in args.pin)
    unknown = sorted(set(pins) - set(args.repos))
    if unknown:
        print(
            "pinned repo(s) not in --repos: " + ", ".join(unknown) + "\n"
            "  a pin that matches no repo is silently ignored, and the run would mine\n"
            "  a moving HEAD while looking pinned. Fix the slug or add it to --repos.",
            file=sys.stderr,
        )
        return 2

    counts: Counter[str] = Counter()
    revs: dict[str, str] = {}
    written = 0
    with args.out.open("w", encoding="utf-8") as handle:
        for slug in args.repos:
            print(f"[clone] {slug}", file=sys.stderr)
            repo_dir = ensure_clone(slug, args.clones)
            rev = pins.get(slug, "HEAD")
            revs[slug] = head_sha(repo_dir, rev)
            print(f"[mine]  {slug} @ {revs[slug][:12]}", file=sys.stderr)
            for example in mine_repo(
                repo_dir, slug, cfg, limit=args.limit, since=args.since, rev=rev
            ):
                handle.write(json.dumps(example.to_dict(), ensure_ascii=False) + "\n")
                written += 1
                counts[f"{example.repo} {example.label} shape={example.shape}"] += 1

    # The manifest is what lets the label file itself stay out of git. It records
    # every input that determines the output -- the rules, the repo shas, the
    # windowing -- plus a digest of the result, so a regeneration can be *proved*
    # byte-identical rather than assumed to be. Without this a label set is an
    # unattributable blob and the only way to preserve an experiment is to commit
    # 16MB of derived rows per iteration.
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output": {
            "path": str(args.out),
            "examples": written,
            "sha256": _sha256(args.out),
        },
        "repos": revs,
        "miner": _miner_revision(),
        "window": {"limit": args.limit, "since": args.since},
        "config": asdict(cfg),
        "counts": dict(sorted(counts.items())),
        "replay": (
            "driftwood mine --out <path> "
            + (f"--limit {args.limit} " if args.limit else "")
            + " ".join(f"--pin {slug}={sha}" for slug, sha in revs.items())
        ),
    }
    _manifest_path(args.out).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {written} examples to {args.out}", file=sys.stderr)
    print(f"wrote manifest to {_manifest_path(args.out)}\n", file=sys.stderr)
    for key in sorted(counts):
        print(f"  {counts[key]:6d}  {key}", file=sys.stderr)
    return 0


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _cmd_stats(args: argparse.Namespace) -> int:
    rows = _load(args.labels)
    print(f"{len(rows)} examples in {args.labels}\n")
    for dimension in ("repo", "label", "shape", "label_basis"):
        print(f"by {dimension}:")
        for value, count in Counter(row[dimension] for row in rows).most_common():
            print(f"  {count:6d}  {value}")
        print()
    return 0


def _cmd_sample(args: argparse.Namespace) -> int:
    """Write a hand-review sheet for a random sample of positives."""
    rows = [row for row in _load(args.labels) if row["label"] == LABEL_DRIFT]
    if args.shape:
        rows = [row for row in rows if row["shape"] == args.shape]
    if args.repo:
        # Needed to sample *away* from a repo. The first review drew all 40 cases
        # from psf/requests, which turned out to be an outlier -- 13x more shape B
        # than shape A, where every other repo in the set is balanced or the other
        # way round. A per-repo draw is how that stops being invisible.
        wanted = set(args.repo)
        rows = [row for row in rows if row["repo"] in wanted]

    # Never ask for a verdict already given. The labelled set should grow
    # monotonically across sessions rather than re-litigating settled cases, and
    # re-asking would also let a reviewer's second answer silently disagree with
    # their first.
    if args.exclude:
        seen = {
            verdict.example_id
            for sheet in args.exclude
            for verdict in parse_sheet(sheet)
        }
        before = len(rows)
        rows = [row for row in rows if row["example_id"] not in seen]
        print(f"excluded {before - len(rows)} already-judged case(s)", file=sys.stderr)

    if not rows:
        print("no positive examples matched", file=sys.stderr)
        return 1

    random.Random(args.seed).shuffle(rows)
    chosen = rows[: args.n]
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open("w", encoding="utf-8") as sheet:
        sheet.write(f"# Drift label review — {len(chosen)} cases (seed {args.seed})\n\n")
        sheet.write(
            "For each case, replace `VERDICT: ?` with one of:\n\n"
            + "".join(f"- `{key}` — {why}\n" for key, why in VERDICTS.items())
            + "\nThe question is always: **at the parent commit, was this "
            "documentation false about the code?** Not whether the commit "
            "improved the docs — whether what it replaced was wrong.\n\n---\n\n"
        )
        for index, row in enumerate(chosen, start=1):
            repo_dir = args.clones / row["repo"].replace("/", "__")
            sheet.write(f"## Case {index} — `{row['example_id']}`\n\n")
            sheet.write(f"- **repo** `{row['repo']}` · **shape** {row['shape']}\n")
            sheet.write(f"- **basis** `{row['label_basis']}`\n")
            sheet.write(f"- **subject** {row['subject']}\n")
            sheet.write(
                f"- **commit** https://github.com/{row['repo']}/commit/{row['fix_sha']}\n"
            )
            sheet.write(f"- **doc** `{row['doc_path']}`\n")
            if row["code_path"]:
                sheet.write(f"- **code** `{row['code_path']}`\n")
            if row["shared_identifiers"]:
                tokens = ", ".join(f"`{token}`" for token in row["shared_identifiers"])
                # Same field, different meaning per shape, so it has to be
                # labelled per shape. Shape A: tokens the doc and code diffs have
                # in common. Shape B: tokens the doc stopped asserting. Printing
                # both as "shared identifiers" would tell the reviewer something
                # false about the evidence they are judging.
                caption = (
                    "no longer asserted after this commit"
                    if row["shape"] == "B"
                    else "shared identifiers"
                )
                sheet.write(f"- **{caption}** {tokens}\n")
            sheet.write("\n**VERDICT: ?**\n\n")

            sheet.write("<details><summary>doc diff</summary>\n\n```diff\n")
            try:
                sheet.write(
                    file_diff(
                        repo_dir, row["parent_sha"], row["fix_sha"], row["doc_path"], context=3
                    )[: args.max_diff_chars]
                )
            except Exception as exc:  # a clone may be missing or the path renamed
                sheet.write(f"(could not render: {exc})")
            sheet.write("\n```\n\n</details>\n\n")

            if row["code_path"]:
                sheet.write("<details><summary>code diff</summary>\n\n```diff\n")
                try:
                    sheet.write(
                        file_diff(
                            repo_dir,
                            row["parent_sha"],
                            row["fix_sha"],
                            row["code_path"],
                            context=3,
                        )[: args.max_diff_chars]
                    )
                except Exception as exc:
                    sheet.write(f"(could not render: {exc})")
                sheet.write("\n```\n\n</details>\n\n")
            sheet.write("---\n\n")

    print(f"wrote {len(chosen)} cases to {args.out}", file=sys.stderr)
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    result = score(args.labels, args.sheets)
    print(format_report(result))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


def _cmd_retention(args: argparse.Namespace) -> int:
    result = retention(args.old, args.new, args.sheets)
    print(format_retention(result))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="driftwood", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    mine = subparsers.add_parser("mine", help="mine drift labels out of git history")
    mine.add_argument("--repos", nargs="+", default=DEFAULT_REPOS)
    mine.add_argument("--clones", type=Path, default=DEFAULT_CLONES)
    mine.add_argument("--out", type=Path, default=DEFAULT_LABELS)
    mine.add_argument("--limit", type=int, default=None, help="max commits per repo")
    mine.add_argument(
        "--force",
        action="store_true",
        help="overwrite --out if it already exists (refused by default)",
    )
    mine.add_argument("--since", default=None, help='e.g. "2022-01-01"')
    mine.add_argument(
        "--pin",
        action="extend",
        nargs="+",
        default=[],
        metavar="owner/name=SHA",
        help="mine each repo at a fixed sha, as printed in a manifest's `replay` "
        "field; without this, --limit counts back from a moving HEAD",
    )
    mine.add_argument("--max-files", type=int, default=MineConfig.max_files_in_commit)
    mine.add_argument("--min-shared", type=int, default=MineConfig.min_shared_identifiers)
    mine.add_argument("--min-doc-lines", type=int, default=MineConfig.min_doc_lines_changed)
    mine.add_argument(
        "--no-require-removed-identifier",
        dest="require_removed",
        action="store_false",
        default=True,
        help="shape B: keep doc-only commits that changed no identifier "
        "(off by default; turn on to measure what that filter is worth)",
    )
    mine.add_argument(
        "--no-doc-literals-only",
        dest="doc_literals_only",
        action="store_false",
        default=True,
        help="shape B: judge the doc side on all prose rather than only on "
        "marked-up code spans and version literals",
    )
    mine.add_argument(
        "--easy-negatives",
        type=int,
        default=0,
        metavar="N",
        help="also emit N negatives per repo from doc/code pairs that never "
        "co-changed. These are the only negatives that permit a false-positive "
        "rate: a matched negative's doc really is about its code, so a detector "
        "that fires on everything still scores well on them. Split evenly between "
        "uniformly random pairs and pairs whose paths look related, reported "
        "separately by label_basis -- a random pair is trivially unrelated, so a "
        "specificity number built only from those prices the problem too cheaply",
    )
    mine.add_argument(
        "--require-withdrawn-claim",
        dest="require_withdrawn",
        action="store_true",
        default=False,
        help="shape A: require an identifier to be removed from both the doc and "
        "the code, not merely shared. Targets `new` (feature plus its docs), the "
        "largest shape-A error class in the second review. Off by default: it "
        "costs 2 of 7 true positives, and its precision gain is not yet measured "
        "out of sample",
    )
    mine.add_argument(
        "--no-drop-docs-build-paths",
        dest="drop_docs_build_paths",
        action="store_false",
        default=True,
        help="shape B: keep doc changes that are example-include renumbering "
        "(tutorial001, docs_src). On by default -- measured at 3 of 20 cases, all "
        "cosmetic, costing no true positive",
    )
    mine.add_argument(
        "--require-symbol-beyond-version",
        dest="require_symbol_beyond_version",
        action="store_true",
        default=False,
        help="shape B: reject cases whose withdrawn evidence is only version "
        "literals. Those scored 0/10 against 37 hand labels where the rest of the "
        "arm scored 44%%, because a doc-only commit withdraws a version literal by "
        "rewriting its own example output. Off by default: subtractive, so "
        "`retention` prices it against the existing sheets first",
    )
    mine.set_defaults(func=_cmd_mine)

    stats = subparsers.add_parser("stats", help="summarise a label file")
    stats.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    stats.set_defaults(func=_cmd_stats)

    sample = subparsers.add_parser("sample", help="write a hand-review sheet")
    sample.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    sample.add_argument("--clones", type=Path, default=DEFAULT_CLONES)
    sample.add_argument("--out", type=Path, default=Path("review/batch-01.md"))
    sample.add_argument("-n", type=int, default=50)
    sample.add_argument("--shape", choices=["A", "B"], default=None)
    sample.add_argument("--repo", nargs="*", default=[], help="restrict to these repos")
    sample.add_argument("--seed", type=int, default=7)
    sample.add_argument(
        "--exclude",
        nargs="*",
        type=Path,
        default=[],
        help="already-completed review sheets; their cases will not be sampled again",
    )
    sample.add_argument("--max-diff-chars", type=int, default=4000)
    sample.set_defaults(func=_cmd_sample)

    scorer = subparsers.add_parser("score", help="score hand-labelled review sheets")
    scorer.add_argument("sheets", nargs="+", type=Path)
    scorer.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    scorer.add_argument(
        "--out",
        type=Path,
        default=None,
        help="also write the result as JSON, so eval results are data rather than "
        "console output and a later run is diffable against this one",
    )
    scorer.set_defaults(func=_cmd_score)

    keep = subparsers.add_parser(
        "retention",
        help="check how a rebuilt label set treats already-judged cases "
        "(valid for subtractive rule changes only)",
    )
    keep.add_argument("sheets", nargs="+", type=Path)
    keep.add_argument("--old", type=Path, required=True)
    keep.add_argument("--new", type=Path, required=True)
    keep.add_argument("--out", type=Path, default=None)
    keep.set_defaults(func=_cmd_retention)

    # Stage 2 registers its own subcommand rather than being implemented here: the
    # mining package is the project's ground truth and everything downstream is
    # measured against it, so it should not grow a dependency on the thing it
    # grades. Imported lazily for the same reason `mine` does not import a model.
    from ..retrieval.cli import add_parser as add_retrieval_parser

    add_retrieval_parser(subparsers)

    # Stage 3, likewise. Imported lazily so that `mine` and `score` still run on a
    # machine with no `anthropic` installed -- the judge package's model arm is an
    # optional extra and its floors are not.
    from ..judge.cli import add_parser as add_judge_parser

    add_judge_parser(subparsers)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
