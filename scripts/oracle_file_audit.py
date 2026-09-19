"""Is the "oracle" code file the file the drifted sentence is about?

    uv run python scripts/oracle_file_audit.py

Costs nothing and answers the question that the first paid run left open. The model
arm abstained on 69% of the 45 shape-A cases, and the diagnosis written up at the time
was that the oracle arm shows the wrong file -- median 16% of the document's
backticked identifiers appear in the code on screen.

**That reasoning does not hold, and this script exists because it does not.** The
denominator there is every identifier the *whole document* marks up. A reference page
marks up dozens, spread over many topics, and one code file will never contain most of
them even when it is exactly the right file. 16% is therefore consistent with two
incompatible worlds: the oracle file is irrelevant, or the oracle file is correct and
the page is simply long. A metric that cannot separate those two cannot justify a
redesign, and it was being used to justify one.

What separates them is a narrower denominator: the identifiers in the *drifted
sentence* rather than in the document. `shared_identifiers` is exactly that -- the doc
diff's removed-only side, the identifiers the fixing commit deleted from the prose. If
those appear in the oracle file, the oracle file is the file the claim is about and the
whole-document number was measuring page length.

**`shared_identifiers` is a leaking field, and using it here is not a leak.** It must
never reach a model -- `context.LEAKING_FIELDS` names it and a test asserts it is
absent from every rendered prompt, because it points straight at the answer. This is
the evaluation harness looking at its own corpus to decide what to build next, which
is the one place the miner's evidence is legitimately readable. Nothing this script
computes is shown to a judge or feeds a scored run.

Four questions, in the order that decides the next build step:

1. **Claim coverage.** Share of the drifted sentence's identifiers present in the
   oracle file. High means the arm is sound and the abstentions have another cause.
2. **Would the proposed fix change anything?** Where the oracle file ranks in the pool
   by claim coverage. If it is already at the top, "select code files by the
   document's identifiers" picks the same file and is a no-op.
3. **What did truncation cost?** The same coverage computed on the 6,000-character cut
   the judge actually saw, against the whole file. A gap here is a budget bug, which is
   a much cheaper fix than a selection redesign.
4. **Does it differ on the positives?** Split by verdict. The arm only has to be right
   where the label is `drift`; being wrong on `unrelated` cases costs nothing.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from driftwood.judge.cases import load_cases
from driftwood.judge.context import (
    CODE_BUDGET,
    DOC_BUDGET,
    _truncate,
    select_relevant,
)
from driftwood.mining.gitio import list_files, local_name_for, read_blobs
from driftwood.mining.identifiers import extract, literal_spans
from driftwood.mining.paths import Kind, classify


def _median(values) -> float:
    # None means "no opinion on this case" (see `_share`) and is dropped rather than
    # counted as zero, so a page with nothing marked up does not pull the median down
    # alongside a file that genuinely covers nothing.
    values = sorted(v for v in values if v is not None)
    if not values:
        return 0.0
    middle = len(values) // 2
    if len(values) % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2


def _share(wanted: set[str], present: set[str]) -> float | None:
    """None rather than 0.0 when there is nothing to cover.

    A case whose drifted sentence marked up no identifiers is a case this measurement
    has no opinion about, and scoring it zero would drag the median down with cases
    that are not evidence of anything. 28 of the 125 records have an empty
    `shared_identifiers`, so this is not a corner.
    """
    if not wanted:
        return None
    return len(wanted & present) / len(wanted)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    cases, _ = load_cases(args.review, args.data)
    cases = [c for c in cases if c.code_path]
    print(f"{len(cases)} shape-A case(s) with a code_path\n")

    rows = []
    pools: dict[tuple[str, str], list[str]] = {}
    texts: dict[tuple[str, str], dict[str, str]] = {}

    for case in cases:
        clone = args.clone_root / local_name_for(case.repo)
        key = (case.repo, case.at_sha)
        if key not in pools:
            present = list_files(clone, case.at_sha)
            pools[key] = sorted(p for p in present if classify(p) is Kind.CODE)
            texts[key] = read_blobs(clone, case.at_sha, pools[key])
        pool, bodies = pools[key], texts[key]

        doc = read_blobs(clone, case.at_sha, [case.doc_path]).get(case.doc_path)
        if doc is None:
            continue
        oracle_body = bodies.get(case.code_path)
        if oracle_body is None:
            continue

        claim = set(case.shared_identifiers)
        doc_marked = extract(literal_spans(doc), versions=False)
        oracle_tokens = extract(oracle_body, versions=False)
        cut_body, was_cut = _truncate(oracle_body, CODE_BUDGET)
        cut_tokens = extract(cut_body, versions=False)

        # The same budget spent by windowing instead of by head-truncation. Guided by
        # `doc_marked` -- the identifiers the document marks up -- and NOT by `claim`,
        # which is `shared_identifiers` and is the answer. Selecting windows with the
        # answer would measure a retrieval step that cannot exist at inference time, and
        # would report a recovery this code could never reproduce on an unseen page.
        win_body, _win_cut = select_relevant(oracle_body, CODE_BUDGET, doc_marked)
        win_tokens = extract(win_body, versions=False)

        # Rank every candidate in the pool by how much of the drifted sentence it
        # contains, and see where the oracle file lands. This is question 2: if the
        # oracle file is already rank 1, selecting by identifiers picks it anyway.
        claim_rank = None
        better = 0
        if claim:
            oracle_hit = len(claim & oracle_tokens)
            for path in pool:
                if path == case.code_path:
                    continue
                if len(claim & extract(bodies[path], versions=False)) > oracle_hit:
                    better += 1
            claim_rank = better + 1

        rows.append(
            {
                "example_id": case.example_id,
                "code_path": case.code_path,
                "chars": len(oracle_body),
                "repo": case.repo,
                "verdict": case.verdict,
                "doc_marked": len(doc_marked),
                "claim_n": len(claim),
                "doc_cov": _share(doc_marked, oracle_tokens),
                "claim_cov": _share(claim, oracle_tokens),
                "claim_cov_cut": _share(claim, cut_tokens),
                "claim_cov_win": _share(claim, win_tokens),
                "win_chars": len(win_body),
                "was_cut": was_cut,
                "doc_cut": len(doc) > DOC_BUDGET,
                "claim_rank": claim_rank,
                "files_better": better,
                "pool": len(pool),
            }
        )

    _report(rows, args.k)
    return 0


def _report(rows: list[dict], k: int) -> None:
    scored = [r for r in rows if r["claim_cov"] is not None]
    print(f"{len(scored)} of {len(rows)} case(s) have a non-empty drifted-sentence")
    print("identifier set and can be measured at all.\n")

    print("=== 1. IS THE ORACLE FILE THE RIGHT FILE? ===\n")
    print("Two denominators over the same code file. `doc` is every identifier the")
    print("whole page marks up; `claim` is only the ones the fix deleted from the prose.")
    print()
    print(f"{'':<22}{'median doc cov':>16}{'median claim cov':>19}{'claim=100%':>12}"
          f"{'claim=0%':>10}")
    for label, subset in (("all shape-A", scored),
                          ("verdict=drift", [r for r in scored if r["verdict"] == "drift"]),
                          ("verdict!=drift", [r for r in scored if r["verdict"] != "drift"])):
        if not subset:
            continue
        full = sum(1 for r in subset if r["claim_cov"] == 1.0)
        none = sum(1 for r in subset if r["claim_cov"] == 0.0)
        print(f"{label:<22}"
              f"{_median([r['doc_cov'] for r in subset]):>15.0%}"
              f"{_median([r['claim_cov'] for r in subset]):>19.0%}"
              f"{full:>9}/{len(subset):<3}{none:>7}/{len(subset)}")
    print()
    print(f"median identifiers marked up per page: {_median([r['doc_marked'] for r in rows]):.0f}")
    print(f"median identifiers in the drifted sentence: {_median([r['claim_n'] for r in scored]):.0f}")

    print("\n=== 2. WOULD SELECTING BY IDENTIFIERS PICK A DIFFERENT FILE? ===\n")
    ranked = [r for r in scored if r["claim_rank"]]
    top1 = sum(1 for r in ranked if r["claim_rank"] == 1)
    topk = sum(1 for r in ranked if r["claim_rank"] <= k)
    print(f"oracle file is the single best-covering file in its pool: {top1}/{len(ranked)}")
    print(f"oracle file is within the top {k} by claim coverage:        {topk}/{len(ranked)}")
    print(f"median number of files that cover the claim better:      "
          f"{_median([r['files_better'] for r in ranked]):.0f}")
    print(f"median pool size:                                        "
          f"{_median([r['pool'] for r in rows]):.0f}")

    print("\n=== 3. WHAT DID TRUNCATION COST? ===\n")
    cut = [r for r in scored if r["was_cut"]]
    print(f"{len(cut)} of {len(scored)} oracle file(s) were cut at {CODE_BUDGET:,} chars")
    if cut:
        lost = [r for r in cut if r["claim_cov_cut"] < r["claim_cov"]]
        print(f"  of those, {len(lost)} lost claim coverage to the cut")
        print(f"  median claim coverage whole file: {_median([r['claim_cov'] for r in cut]):.0%}")
        print(f"  median claim coverage as shown:   {_median([r['claim_cov_cut'] for r in cut]):.0%}")
        # The two medians above move further apart than the count suggests, so the
        # per-case losses are listed rather than summarised: 19 of the 29 lost nothing,
        # and reporting only the median shift would read as every cut file losing 42
        # points. What the budget is actually costing is a few total losses.
        print(f"\n  the {len(lost)} that lost coverage, whole file -> as shown:")
        for r in sorted(lost, key=lambda r: r["claim_cov_cut"] - r["claim_cov"]):
            print(f"    {r['verdict']:<10}{r['claim_cov']:>5.0%} -> {r['claim_cov_cut']:>4.0%}"
                  f"   {r['chars']:>7,} chars  {r['code_path']}")
        drift_lost = [r for r in lost if r["verdict"] == "drift"]
        print(f"  of the {len(lost)}, {len(drift_lost)} are verdict=drift -- the only "
              f"ones where the loss can cost a true positive")
    print(f"{sum(1 for r in rows if r['doc_cut'])} of {len(rows)} document(s) were cut "
          f"at {DOC_BUDGET:,} chars")

    print("\n=== 3b. DOES WINDOWING GET IT BACK, AT THE SAME BUDGET? ===\n")
    print("Same 6,000 characters, spent on the neighbourhoods of the identifiers the")
    print("DOCUMENT marks up instead of on the first 6,000 characters of the file. The")
    print("selector never sees the drifted sentence, so this is a recovery the judge")
    print("could actually get on a page whose answer nobody knows.\n")
    if cut:
        print(f"{'':<12}{'whole file':>12}{'head-cut':>11}{'windowed':>11}")
        print(f"{'median':<12}"
              f"{_median([r['claim_cov'] for r in cut]):>11.0%}"
              f"{_median([r['claim_cov_cut'] for r in cut]):>11.0%}"
              f"{_median([r['claim_cov_win'] for r in cut]):>11.0%}")
        recovered = [r for r in lost if r["claim_cov_win"] > r["claim_cov_cut"]]
        whole = [r for r in lost if r["claim_cov_win"] >= r["claim_cov"]]
        print(f"\nof the {len(lost)} file(s) that lost coverage to the head cut:")
        print(f"  {len(recovered)} recover some of it by windowing")
        print(f"  {len(whole)} are back to their whole-file coverage")
        print(f"\n  per case, head-cut -> windowed (whole file in brackets):")
        for r in sorted(lost, key=lambda r: r["claim_cov_win"] - r["claim_cov_cut"]):
            mark = "  " if r["claim_cov_win"] <= r["claim_cov_cut"] else "->"
            print(f"  {mark} {r['verdict']:<10}{r['claim_cov_cut']:>4.0%} -> "
                  f"{r['claim_cov_win']:>4.0%}  [{r['claim_cov']:>4.0%}]"
                  f"  {r['chars']:>7,} chars  {r['code_path']}")
        # Windowing can also LOSE coverage a head cut happened to keep: a definition in
        # the first 6,000 characters that no marked identifier points at gets dropped to
        # pay for a window further down. Counted rather than assumed away.
        worse = [r for r in scored
                 if r["was_cut"] and r["claim_cov_win"] < r["claim_cov_cut"]]
        print(f"\n{len(worse)} cut file(s) are WORSE windowed than head-cut -- a window "
              f"paid for\nby dropping a definition the head happened to include:")
        for r in worse:
            print(f"     {r['verdict']:<10}{r['claim_cov_cut']:>4.0%} -> "
                  f"{r['claim_cov_win']:>4.0%}  {r['code_path']}")

    print("\n=== 4. PER REPO ===\n")
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        by_repo[r["repo"]].append(r)
    print(f"{'repo':<22}{'n':>4}{'median claim cov':>19}{'oracle is rank 1':>19}")
    for repo in sorted(by_repo):
        subset = by_repo[repo]
        top = sum(1 for r in subset if r["claim_rank"] == 1)
        print(f"{repo:<22}{len(subset):>4}"
              f"{_median([r['claim_cov'] for r in subset]):>18.0%}"
              f"{top:>13}/{len(subset)}")
    print("\n=== 5. REPO x VERDICT, BECAUSE ONE REPO IS HALF THE ARM ===\n")
    # psf/requests is 22 of the 45 and its median claim coverage is 0%, which would be
    # alarming if those cases were positives: it would mean the drifted sentence's
    # identifiers appear in no file in the repo. Whether it is alarming depends entirely
    # on the verdict split, so the split is printed rather than assumed either way.
    verdicts = sorted({r["verdict"] for r in scored})
    print(f"{'repo':<22}" + "".join(f"{v:>11}" for v in verdicts))
    for repo in sorted(by_repo):
        cells = []
        for verdict in verdicts:
            subset = [r for r in by_repo[repo] if r["verdict"] == verdict]
            cells.append(f"{len(subset)}@{_median([r['claim_cov'] for r in subset]):.0%}"
                         if subset else "-")
        print(f"{repo:<22}" + "".join(f"{c:>11}" for c in cells))
    print("\ncell = case count @ median claim coverage")

    print("\nNo pooled row for the headline. Per repo, as everywhere else in this harness.")


if __name__ == "__main__":
    raise SystemExit(main())
