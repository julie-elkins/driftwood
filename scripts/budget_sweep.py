"""At what budget does the answer survive into the context? And what does it cost?

    uv run python scripts/budget_sweep.py

Free: git and the two truncation functions only, no API call and no cache read. Written
to choose the budgets for the targeted re-run by measurement instead of picking round
numbers, because both budgets are inside the judge cache key -- every value tried costs
the full price of every case it is tried on, so they want to be chosen once.

**Two sides, and the doc side turned out to be the bigger one.** `unit_mismatch_audit.py`
looked only at code: 5 of the 9 recall-costing cases have a *definition* of a
deleted-prose identifier in the full text of a shown file and not in the windowed text
that was sent. Sweeping the code budget qualifies that count downwards, and then the doc
side reframes it entirely:

    section 1  of those 5, how many get the definition on screen, at what budget
    section 2  whether the CLAIM -- the prose the fixing commit deleted -- was on
               screen at all, which is the question nobody asked
    section 3  input tokens at each (doc, code) pair, which is what gets billed

Section 2 is the one that matters. Doc truncation was counted from the first paid run;
whether the cut removed the sentence under test was never checked, and on 3 of the 9 it
did. A case whose false claim is not in the prompt is unanswerable, not answered wrongly,
and no code budget can rescue it. A fourth case fails section 2 for an unrelated reason --
none of its deleted prose is findable in the parent page at all -- and is reported apart
from the budget finding rather than folded into it.

A budget that recovers everything is not automatically the right one: `select_relevant`
spends a bigger budget on more windows, so the marginal character buys less each time,
and doubling the context roughly doubles the input bill for that case. Read the smallest
budget that recovers the cases, not the largest that fits.

Deliberately NOT swept here: `k`. More files re-divides the same per-file budget and
changes which windows win, so moving both at once makes a recovered case unattributable
-- and the 3 "no definition in any shown file" cases are the control group that says
whether the diagnosis was right, which only holds if selection is held still.
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from driftwood.judge import context as context_module
from driftwood.judge.cases import load_cases
from driftwood.judge.context import (
    CODE_BUDGET,
    DOC_BUDGET,
    ContextBuilder,
    render,
    select_relevant,
)
from driftwood.judge.evaluate import estimate_spend
from driftwood.judge.judge import DEFAULT_MAX_TOKENS, SYSTEM_PROMPT
from driftwood.mining import identifiers
from driftwood.mining.gitio import changed_sides, ensure_clone, file_diff, read_blobs
from driftwood.mining.identifiers import literal_spans

from unit_mismatch_audit import defines, norm, shingles

# The nine cases `unit_mismatch_audit.py --arm seeded --retry-max-tokens 12000` names as
# recall-costing, with the bucket it put each in. Pasted rather than re-derived because
# re-deriving reads the paid cache, and this script must run without it -- but they are
# re-checked below against the same mechanical test, so a stale id shows up as a
# mismatch rather than as a wrong number.
BUCKETS = {
    "04a332fe0dc498cc": "budget-cut",
    "0eea9dc58ea4a754": "budget-cut",
    "3b7710af3aaa1c49": "budget-cut",
    "884f8d4776cb8b02": "budget-cut",
    "f6ff7af97ac3c31c": "budget-cut",
    "65463185f227a96c": "no-definition-shown",
    "d0f54d7f2b930191": "no-definition-shown",
    "e7df72235ade950f": "no-definition-shown",
    "756ac020b878f26e": "judge-miss",
}

CANDIDATES = (6_000, 9_000, 12_000, 18_000, 24_000, 36_000, 48_000)

# Doc candidates run higher than the code ones because the doc side is head-truncated
# rather than windowed: reaching a sentence at character 22,461 costs all 22,461 of them.
DOC_CANDIDATES = (12_000, 18_000, 24_000, 30_000, 42_000, 60_000)


def claim_offset(page: str, removed: str) -> int | None:
    """Where in the NORMALISED page the fixing commit's deleted prose first appears.

    `None` means the deleted text does not match the parent page at all -- reformatting,
    or a diff whose removed side is not literal prose. That is not the same as "beyond the
    budget" and must not be counted as a recovery either way, so it is reported separately.

    Reported for scale only, and it is a LOWER BOUND on the raw offset the budget is
    measured in: `norm` strips markup and collapses whitespace, so the character the
    truncation actually counts to sits at or beyond this number. Which budget reaches the
    claim is decided by `claim_survives` against the real truncation, not by comparing
    this against a candidate.
    """
    haystack = norm(page)
    hits = [haystack.find(s) for s in shingles(norm(removed)) if s in haystack]
    return min(hits) if hits else None


def locatable_shingles(page: str, removed: str) -> tuple[set[str], int]:
    """The deleted passage's word 4-grams that are findable in the full parent page.

    The denominator is every shingle of the removed side; the numerator drops the ones the
    page does not contain. Those are not a budget finding and must not be counted as one:
    `changed_sides` concatenates ALL removed hunks, so a 4-gram straddling the junction
    between two hunks is absent from the page no matter how much of it is shown, and
    markup normalisation loses a few more. Requiring every shingle instead made a
    7,067-character page -- one the 12,000 budget never truncates -- report as cut.
    """
    haystack = norm(page)
    every = shingles(norm(removed))
    return {s for s in every if s in haystack}, len(every)


def claim_survives(page: str, removed: str, doc_budget: int) -> bool:
    """Does head-truncating the page at `doc_budget` still show the whole deleted passage?

    Asked against `_truncate` itself rather than against an offset, because the budget
    counts raw characters and the only offset available is in normalised space. The test is
    containment of the locatable shingles, which isolates truncation from non-locatability
    and gives a free sanity property: a page shorter than the budget is returned whole, so
    it survives by construction.

    Every locatable shingle, not one of them: a claim whose last clause was cut is a claim
    the judge cannot check, and scoring it as shown is the optimism this script removes.
    """
    findable, _ = locatable_shingles(page, removed)
    if not findable:
        return False
    kept, _ = context_module._truncate(page, doc_budget)
    haystack = norm(kept)
    return all(s in haystack for s in findable)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--arm", default="seeded", choices=("oracle", "seeded"))
    parser.add_argument("--k", type=int, default=None)
    args = parser.parse_args()

    cases = {c.example_id: c for c in load_cases(args.review, args.data)[0]}
    missing_ids = sorted(set(BUCKETS) - set(cases))
    if missing_ids:
        print(f"these ids are not in the corpus any more: {missing_ids}")
        return 1

    builder = ContextBuilder(
        args.clone_root, **({"k": args.k} if args.k is not None else {})
    )

    # Per case: the identifiers whose definitions are the thing at stake, plus which
    # files were shown at the default budget. Files are held fixed across the sweep --
    # `select_relevant` cannot change WHICH file is chosen, only what survives inside it.
    plan = []
    for example_id, bucket in BUCKETS.items():
        case = cases[example_id]
        context = builder.build(case, args.arm)
        clone = ensure_clone(case.repo, args.clone_root)
        _added, removed = changed_sides(
            file_diff(clone, case.at_sha, case.fix_sha, case.doc_path)
        )
        raw_doc = read_blobs(clone, case.at_sha, [case.doc_path]).get(case.doc_path, "")
        wanted = identifiers.extract(literal_spans(raw_doc), versions=False)
        deleted = identifiers.extract(removed)
        full = builder._code_texts(case.repo, case.at_sha)
        shown = [f.path for f in context.code_files]
        at_stake = {
            name
            for name in deleted
            if any(defines(full.get(p, ""), name) for p in shown)
        }
        plan.append((case, bucket, context, full, wanted, at_stake, raw_doc, removed))

    print(f"arm `{args.arm}`, k={builder.k}, default CODE_BUDGET={CODE_BUDGET:,}\n")
    print("=== PER CASE: THE SMALLEST BUDGET AT WHICH THE DEFINITION IS ON SCREEN ===\n")

    first_ok: dict[str, int | None] = {}
    # Rendered prompts, not raw code characters: the doc side and the per-file headers
    # do not grow with the budget, so counting code alone overstates the cost increase.
    prompts_at: dict[int, list[str]] = {b: [] for b in CANDIDATES}
    for case, bucket, context, full, wanted, at_stake, _doc, _rm in plan:
        row = []
        found = None
        for budget in CANDIDATES:
            windowed = tuple(
                dataclasses.replace(
                    f,
                    **dict(
                        zip(
                            ("text", "truncated"),
                            select_relevant(full.get(f.path, ""), budget, wanted),
                        )
                    ),
                )
                for f in context.code_files
            )
            prompts_at[budget].append(
                render(dataclasses.replace(context, code_files=windowed))
            )
            on_screen = {
                name
                for name in at_stake
                if any(defines(f.text, name) for f in windowed)
            }
            ok = bool(at_stake) and on_screen == at_stake
            row.append(f"{budget // 1000}k:{len(on_screen)}/{len(at_stake)}")
            if ok and found is None:
                found = budget
        first_ok[case.example_id] = found
        mark = (
            f"all on screen at {found:,}"
            if found
            else ("nothing at stake -- no shown file defines a deleted identifier"
                  if not at_stake else "NOT RECOVERED at any candidate")
        )
        print(f"  [{bucket:<19}] {case.example_id}  {case.repo} {case.doc_path}")
        print(f"        at stake: {sorted(at_stake) or '--'}")
        print(f"        {'  '.join(row)}")
        print(f"        -> {mark}\n")

    print("=== PER CASE: WAS THE CLAIM UNDER TEST EVEN IN THE PROMPT? ===\n")
    print(f"  default DOC_BUDGET={DOC_BUDGET:,}, head-truncated (the tail is what goes)\n")

    doc_first_ok: dict[str, int | None] = {}
    unlocatable: list[str] = []
    for case, bucket, _ctx, _full, _wanted, _at_stake, raw_doc, removed in plan:
        offset = claim_offset(raw_doc, removed)
        findable, every = locatable_shingles(raw_doc, removed)
        row = [
            f"{b // 1000}k:{'y' if claim_survives(raw_doc, removed, b) else 'n'}"
            for b in DOC_CANDIDATES
        ]
        found = next(
            (b for b in DOC_CANDIDATES if claim_survives(raw_doc, removed, b)), None
        )
        doc_first_ok[case.example_id] = found
        if offset is None:
            unlocatable.append(case.example_id)
            verdict = (
                "deleted prose NOT LOCATABLE in the parent page -- reformatted, or the "
                "removed side is not literal prose. Not a budget finding either way"
            )
        elif found == DOC_CANDIDATES[0]:
            verdict = f"whole claim on screen already at {DOC_CANDIDATES[0]:,}"
        elif found:
            verdict = (
                f"CUT AT THE DEFAULT {DOC_BUDGET:,} -- whole claim needs {found:,}"
            )
        else:
            verdict = (
                f"CUT AT THE DEFAULT {DOC_BUDGET:,} and not whole at any candidate "
                f"(up to {DOC_CANDIDATES[-1]:,})"
            )
        print(f"  [{bucket:<19}] {case.example_id}  {case.repo} {case.doc_path}")
        print(
            f"        page {len(raw_doc):,} chars, deleted prose first at "
            f"{'--' if offset is None else f'~{offset:,}'} (normalised, lower bound), "
            f"{len(findable)}/{every} of it locatable in the page"
        )
        print(f"        {'  '.join(row)}")
        print(f"        -> {verdict}\n")

    unanswerable = [
        example_id
        for example_id, found in doc_first_ok.items()
        if found is None or found > DOC_BUDGET
    ]
    print(f"  UNANSWERABLE AT THE DEFAULT DOC BUDGET: {len(unanswerable)}/{len(plan)}")
    for example_id in unanswerable:
        print(f"    {example_id}  ({BUCKETS[example_id]})")
    print()
    print("  These were scored as wrong answers. They are not: the sentence the fixing")
    print("  commit deleted was not in the text the judge was shown, so no code budget")
    print("  and no better model could have reached them. A recall number computed over")
    print("  them measures the harness, and the first paid run did exactly that.")
    print()

    print("=== WHAT EACH PAIR RECOVERS, AND WHAT IT COSTS ===\n")
    budget_cut = [c.example_id for c, b, *_ in plan if b == "budget-cut"]
    # One row per (doc, code) pair worth considering, rather than the full cross product:
    # the code sweep's own plateaus make most of the grid redundant, and a table nobody
    # reads to the end is how a middle row gets chosen by accident.
    pairs = [
        (DOC_BUDGET, CODE_BUDGET),  # what the paid run actually used
        (DOC_BUDGET, 9_000),
        (DOC_BUDGET, 36_000),
        (30_000, CODE_BUDGET),
        (30_000, 9_000),
        (30_000, 36_000),
    ]
    print(
        f"  {'doc':>8}  {'code':>8}  {'defn':>6}  {'claim':>6}  "
        f"{'input tokens, 9':>16}  vs paid run"
    )
    baseline = None
    for doc_budget, code_budget in pairs:
        prompts = []
        for case, _b, context, full, wanted, _at_stake, raw_doc, _rm in plan:
            doc_text, doc_cut = context_module._truncate(raw_doc, doc_budget)
            windowed = tuple(
                dataclasses.replace(
                    f,
                    **dict(
                        zip(
                            ("text", "truncated"),
                            select_relevant(full.get(f.path, ""), code_budget, wanted),
                        )
                    ),
                )
                for f in context.code_files
            )
            prompts.append(
                render(
                    dataclasses.replace(
                        context,
                        doc_text=doc_text,
                        doc_truncated=doc_cut,
                        code_files=windowed,
                    )
                )
            )
        tokens = estimate_spend(
            prompts, system=SYSTEM_PROMPT, max_tokens=DEFAULT_MAX_TOKENS
        )["input_tokens_approx"]
        if baseline is None:
            baseline = tokens
        defn = sum(
            1
            for example_id in budget_cut
            if first_ok[example_id] is not None and first_ok[example_id] <= code_budget
        )
        claim = sum(
            1
            for found in doc_first_ok.values()
            if found is not None and found <= doc_budget
        )
        print(
            f"  {doc_budget:>8,}  {code_budget:>8,}  {defn:>3}/{len(budget_cut):<2}  "
            f"{claim:>3}/{len(plan):<2}  {tokens:>16,}  {tokens / baseline:>10.2f}x"
        )
    print()
    print("  Tokens, never dollars -- a price table in this repo would be exactly the")
    print("  kind of claim that goes stale silently, which is what driftwood looks for.")
    print("  `defn` counts only the budget-cut bucket; `claim` counts all nine. The")
    print("  three `no-definition-shown` cases cannot be recovered by either budget and")
    print("  are the control: if raising one flips them, the diagnosis was wrong.")
    if unlocatable:
        print(f"  `claim` can never reach {len(plan)}/{len(plan)}: {len(unlocatable)} case(s)")
        print("  have deleted prose that does not match the parent page at all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
