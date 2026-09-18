"""The `driftwood judge-cases` and `driftwood judge-eval` subcommands.

Registered from the top-level parser the same way stage 2 is, and for the same
reason: the mining package is the ground truth everything else is graded against, so
it does not import the things grading it.

Two commands rather than one, because the useful thing to do first costs nothing.
`judge-cases` prints what the eval is about to be run on -- the class balance, the
floors, the shape split -- and touches neither a clone nor a model. Reading that
before spending anything is the whole point of having built the floors first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import DEFAULT_JUDGE_MODEL
from .cases import class_balance, format_case_report, load_cases
from .context import ARMS, DEFAULT_K, ContextBuilder, render
from .evaluate import dump_json, format_results, noise_range, to_json
from .judge import AlwaysJudge, AnthropicJudge, LexicalJudge

__all__ = ["add_parser"]

# Every judge that needs no key and no network. The default, so that `judge-eval`
# with no flags produces the half of the result that is free -- and so that a missing
# key is a smaller command rather than an error.
FREE_JUDGES = ("always-not-false", "always-false", "lexical-absence")


def _cmd_cases(args: argparse.Namespace) -> int:
    cases, tally = load_cases(args.review, args.data)
    print(format_case_report(cases, tally))
    return 0


def _build_judges(args: argparse.Namespace) -> dict[str, object]:
    judges: dict[str, object] = {}
    wanted = set(args.judges)
    if "always-not-false" in wanted:
        judges["always-not-false"] = AlwaysJudge(False)
    if "always-false" in wanted:
        judges["always-false"] = AlwaysJudge(True)
    if "lexical-absence" in wanted:
        for threshold in args.lexical_thresholds:
            judge = LexicalJudge(min_missing=threshold)
            # The threshold is in the name because the eval sweeps it. A baseline
            # reported at one arbitrary setting is a baseline chosen to lose.
            judge.name = f"lexical-absence(>={threshold})"
            judges[judge.name] = judge
    if "model" in wanted:
        judges[f"model:{args.model}"] = AnthropicJudge(
            model=args.model, cache_dir=args.cache
        )
    return judges


def _cmd_eval(args: argparse.Namespace) -> int:
    cases, tally = load_cases(args.review, args.data)
    if not cases:
        print("no labelled cases found; nothing to score", file=sys.stderr)
        return 1
    print(format_case_report(cases, tally))
    print()

    if args.repos:
        cases = [c for c in cases if c.repo in set(args.repos)]
    if args.limit:
        # A prefix of the sorted cases, not a sample. A sample would need a seed
        # recorded in the provenance block to mean anything, and --limit exists for
        # smoke-testing the harness rather than for producing a number.
        cases = cases[: args.limit]
        print(f"NOTE: --limit {args.limit} -- this is a smoke test, not a result\n")

    judges = _build_judges(args)
    if not judges:
        print("no judges selected", file=sys.stderr)
        return 1

    builder = ContextBuilder(args.clone_root, k=args.k)
    by_arm: dict[str, dict[str, dict]] = {}
    noise: dict[str, dict] = {}

    for arm in args.arms:
        # The oracle arm covers shape A only. Filtered here rather than raising,
        # because the interesting comparison is oracle-vs-retrieved *on the same 45
        # cases*, and that is what `--arms oracle retrieved` with this filter gives.
        arm_cases = [c for c in cases if c.code_path] if arm == "oracle" else cases
        if not arm_cases:
            print(f"arm {arm}: no cases carry a code_path; skipped\n")
            continue

        contexts = {}
        unusable = []
        for case in arm_cases:
            context = builder.build(case, arm)
            if not context.usable:
                unusable.append(context)
                continue
            contexts[case.example_id] = context
        if unusable:
            # Not dropped silently: a case with no readable doc or no code side is a
            # case the judge was never asked about, and it has to come off the
            # denominator visibly or every rate below is computed against a corpus
            # size that is not the one that was scored.
            print(
                f"arm {arm}: {len(unusable)} case(s) had no readable document or no "
                f"code file at their parent commit and were not judged: "
                + ", ".join(sorted(c.example_id for c in unusable))
            )

        truncated_docs = sum(1 for c in contexts.values() if c.doc_truncated)
        found_oracle = [c.oracle_rank for c in contexts.values() if c.oracle_rank]
        print(
            f"arm {arm}: {len(contexts)} contexts built; "
            f"{truncated_docs} document(s) hit the character budget and were cut; "
            f"median candidate pool {_median([c.pool_size for c in contexts.values()]):.0f}"
        )
        if found_oracle:
            hit_at_k = sum(1 for r in found_oracle if r <= args.k) / len(found_oracle)
            print(
                f"  retrieval check: the commit's own code file is in the top "
                f"{args.k} for {hit_at_k:.0%} of the {len(found_oracle)} shape-A cases "
                f"(median rank {_median(found_oracle):.0f}) -- this is the ceiling the "
                "retrieved arm is working under"
            )
        print()

        if args.dump_prompt:
            first = next(iter(contexts.values()))
            print(f"--- rendered prompt for {first.example_id} ({arm}) ---")
            print(render(first))
            print("--- end ---\n")

        judgements: dict[str, dict] = {}
        for name, judge in judges.items():
            judgements[name] = {
                example_id: judge.judge(context)  # type: ignore[attr-defined]
                for example_id, context in contexts.items()
            }

        scored = [c for c in arm_cases if c.example_id in contexts]
        noise[arm] = noise_range(scored, set(contexts), trials=args.null_trials)
        print(format_results(scored, judgements, arm=arm, noise=noise[arm]))
        print()
        by_arm[arm] = judgements

    if args.out:
        payload = to_json(
            cases, by_arm, tally=tally, noise=noise,
            extra={
                "arms": list(args.arms),
                "k": args.k,
                "judges": sorted(judges),
                "repos": args.repos or "all",
                "limit": args.limit,
            },
        )
        dump_json(args.out, payload)
        print(f"wrote {args.out}")
    return 0


def _median(values) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    middle = len(values) // 2
    if len(values) % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2


def add_parser(subparsers) -> None:
    cases = subparsers.add_parser(
        "judge-cases",
        help="report the hand-labelled cases, the class balance and the floors",
    )
    cases.add_argument("--review", type=Path, default=Path("review"))
    cases.add_argument("--data", type=Path, default=Path("data"))
    cases.set_defaults(func=_cmd_cases)

    ev = subparsers.add_parser(
        "judge-eval", help="score judges against the hand-written verdicts"
    )
    ev.add_argument("--review", type=Path, default=Path("review"))
    ev.add_argument("--data", type=Path, default=Path("data"))
    ev.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    ev.add_argument(
        "--arms", nargs="+", choices=ARMS, default=["retrieved"],
        help="oracle = the commit's own code file, shape A only; retrieved = Lexical "
             "top-k, the only arm that covers shape B",
    )
    ev.add_argument(
        "--judges", nargs="+", default=list(FREE_JUDGES),
        choices=["always-not-false", "always-false", "lexical-absence", "model"],
        help="defaults to the three that need no key",
    )
    ev.add_argument(
        "--lexical-thresholds", nargs="+", type=int, default=[1, 3, 6],
        help="swept rather than fixed, so the free baseline is reported at its best",
    )
    ev.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    ev.add_argument(
        "--cache", type=Path, default=Path(".cache/judgements"),
        help="keyed by a hash of the rendered context, prompt and model",
    )
    ev.add_argument(
        "--k", type=int, default=DEFAULT_K,
        help="code files shown per document; 5 is where the measured hit rate on the "
             "45 known-answer cases reaches 60%%, and it is a dimension to sweep",
    )
    ev.add_argument("--repos", nargs="*", default=None)
    ev.add_argument("--limit", type=int, default=0, help="smoke test only")
    ev.add_argument("--null-trials", type=int, default=200)
    ev.add_argument(
        "--dump-prompt", action="store_true",
        help="print one rendered prompt, to check by eye that no diff leaked into it",
    )
    ev.add_argument("--out", type=Path, default=None, help="also write JSON")
    ev.set_defaults(func=_cmd_eval)
