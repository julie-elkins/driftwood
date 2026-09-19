"""Why did the judge abstain on 31 of 45 cases? Read the replies, per case.

    uv run python scripts/abstention_audit.py

Free: every reply is already on disk under `.cache/judgements`, so this reads the
cache and never calls the API. No key needed.

`oracle_file_audit.py` established that the oracle arm is not showing a *wrong* file: the
commit's own file is the single best-covering file in its pool in 37 of 45 cases and
top-5 in 44 of 45, so "select by the document's identifiers instead" would pick the same
file and is a near-no-op.

**One thing that audit says must not be over-read, because it was.** On the `drift` cases
the oracle file contains a median 100% of the identifiers the fix deleted from the prose,
and that was briefly taken to mean the file definitely contains the answer. It does not:
identifier presence is not definition presence. `requests/__init__.py` scores ~100% by
re-exporting `Session`, `Request` and `Response` while containing no implementation at
all, and the model said exactly that in its own words -- it "merely imports these names".
A token-presence metric cannot tell "defines" from "mentions", which is why the causes
below are read off the replies rather than inferred from coverage numbers.

So the candidate is the number of files rather than the choice of file, and the system
prompt is what turns that into an abstention:

    A statement about code that is not among the files shown. If the relevant code
    is not here, you cannot tell.

In the oracle arm exactly ONE file is shown, against a page that marks up a median of
52 identifiers. Almost every claim on the page is therefore about code that is not
present, and the prompt instructs abstention in that situation. If that is what
happened, the model followed its instructions exactly and the run measured the prompt.

This prints the verdict and the model's own stated reason next to the context facts, so
that reading is confirmed against observation instead of inferred from the prose of the
prompt -- which is a mistake this project has already made once, when a test matching
prose against prose passed while the instruction inside it was false.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from driftwood.judge.cases import load_cases
from driftwood.judge.context import ContextBuilder
from driftwood.judge.judge import AnthropicJudge

# Truncation, checked FIRST and reported as its own cause. The first version of this
# script folded it into "absent code", which is how the reply "the Response class methods
# are truncated and not visible" got counted as evidence for a prompt problem when it is
# evidence for a 6,000-character budget. The two want opposite fixes, so they cannot
# share a bucket: one is a prompt edit, the other is head-truncating a 47,000-character
# module and hoping the relevant function is in the first eighth of it.
_TRUNCATED = re.compile(r"truncat", re.IGNORECASE)

# Phrases that say "I abstained because the code I needed was not shown", as opposed to
# "I read the code and could not decide". Matched on the model's own reason text, and
# deliberately crude: the point is a count of one distinguishable cause, not a taxonomy.
_NOT_SHOWN = re.compile(
    r"not (?:among|in) the (?:files|code) (?:shown|provided)"
    r"|not (?:shown|provided|present|included|available)"
    r"|only code file"
    r"|no(?:t any)? code file"
    r"|cannot verify without"
    r"|is not defined in"
    r"|does not (?:appear|contain|include|define)"
    r"|would need",
    re.IGNORECASE,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/judgements"))
    parser.add_argument("--only", default=None, help="restrict to one verdict")
    parser.add_argument(
        "--arm", default="oracle", choices=("oracle", "seeded"),
        help="which arm's cached replies to read. The two are separate caches -- the key "
             "is a hash of the RENDERED context, so the same case under a different arm "
             "is a different reply and the arms cannot be compared by accident",
    )
    # The ceilings have to match the run being audited, because they are IN the cache key.
    # Reading the seeded arm at the default single ceiling finds the 6,000-token reply for
    # all 45 -- including the 4 that died there and were re-asked at 12,000 -- so the audit
    # would report 4 truncations that the graded run does not have, and attribute the
    # model's answers on those cases to a budget rather than to its reasoning. Defaults
    # reproduce the pre-retry run; `--retry-max-tokens 12000` reproduces the graded one.
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--retry-max-tokens", type=int, default=None)
    args = parser.parse_args()

    cases = [c for c in load_cases(args.review, args.data)[0] if c.code_path]
    builder = ContextBuilder(args.clone_root)
    # No client is constructed unless a reply is missing from the cache, so this stays
    # free. A miss is reported rather than fetched: silently paying for a call inside a
    # script whose docstring promises it is free is the kind of surprise that ends up on
    # a bill.
    # `client` is normally built on the first cache miss, which would turn a miss in this
    # script into a silent purchase. A client that raises makes the docstring's promise
    # structural instead of a convention: a miss is now an error with the key in it.
    class _NoSpend:
        def __getattr__(self, name: str):
            raise AssertionError(
                "this audit reads the cache and must never call the API -- a reply is "
                "missing for the ceilings requested, so re-check --arm/--max-tokens/"
                "--retry-max-tokens against the run you meant to audit"
            )

    judge = AnthropicJudge(
        cache_dir=args.cache,
        client=_NoSpend(),
        **{k: v for k, v in (
            ("max_tokens", args.max_tokens),
            ("retry_max_tokens", args.retry_max_tokens),
        ) if v is not None},
    )

    tally: Counter = Counter()
    rows = []
    for case in cases:
        if args.only and case.verdict != args.only:
            continue
        context = builder.build(case, args.arm)
        if not context.usable:
            continue
        path = args.cache / f"{_key(judge, context)}.json"
        if not path.exists():
            tally["no cached reply"] += 1
            continue
        found = judge.judge(context)
        answer = {True: "false", False: "not-false", None: "unclear"}[found.answer]
        # Truncation wins the tie on purpose. A reply that says both "truncated" and "not
        # shown" is describing one thing: the definition was in the file and the harness
        # cut it out. Attributing that to the prompt would send the fix to the wrong place.
        if _TRUNCATED.search(found.reason):
            cause = "cut by the code budget"
        elif _NOT_SHOWN.search(found.reason):
            cause = "code genuinely not in the context"
        else:
            cause = "read the code and still could not decide"
        tally[f"{case.verdict} -> {answer}"] += 1
        if found.abstained:
            tally["abstained"] += 1
            tally[f"abstained: {cause}"] += 1
            tally[f"abstained on `{case.verdict}`: {cause}"] += 1
        rows.append((case, found, answer, cause))

    print(f"{len(rows)} case(s) read from cache for arm `{args.arm}`\n")
    print("=== COUNTS ===\n")
    for key, count in sorted(tally.items()):
        print(f"  {count:>3}  {key}")

    drift_abstained = [r for r in rows if r[1].abstained and r[0].verdict == "drift"]
    print(f"\n=== THE {len(drift_abstained)} ABSTENTIONS ON `drift`, WITH THE MODEL'S "
          "OWN REASON ===\n")
    print("These are the ones that cost recall. Everything else abstained on a case")
    print("whose right answer was `not-false` anyway, where abstaining is cheap.\n")
    for case, found, _answer, cause in rows:
        if not found.abstained or case.verdict != "drift":
            continue
        print(f"[{cause}]")
        print(f"  {case.repo:<18} {case.code_path}")
        print(f"  {found.reason.strip()[:300]}")
        print()

    answered_drift = [r for r in rows if not r[1].abstained and r[0].verdict == "drift"]
    print(f"=== THE {len(answered_drift)} CASE(S) IT DID ANSWER ON A `drift` LABEL ===\n")
    for case, found, answer, _blames in rows:
        if case.verdict != "drift" or found.abstained:
            continue
        print(f"  answered {answer:<10} {case.repo} {case.doc_path}")
        print(f"    claim:  {(found.claim or '')[:180]}")
        print(f"    reason: {found.reason.strip()[:220]}")
        print()

    # The two error classes, printed in full and separately, because they want opposite
    # fixes and the seeded arm's headline is now driven by the first one: fn 7 against
    # tp 4. A rubric edit that chases the false positives would make the false negatives
    # worse, so the question this section exists to answer is whether the model's stated
    # reason for a false negative actually cites the "these are NOT false" list.
    fns = [r for r in rows if not r[1].abstained and r[0].verdict == "drift"
           and r[2] == "not-false"]
    fps = [r for r in rows if not r[1].abstained and r[0].verdict != "drift"
           and r[2] == "false"]
    for title, group in (
        (f"THE {len(fns)} FALSE NEGATIVE(S) -- labelled `drift`, answered `not-false`", fns),
        (f"THE {len(fps)} FALSE POSITIVE(S) -- labelled not-drift, answered `false`", fps),
    ):
        print(f"=== {title} ===\n")
        for case, found, _answer, _cause in group:
            print(f"  {case.repo:<18} {case.doc_path}")
            print(f"    hand label: {case.verdict}")
            print(f"    code shown: {case.code_path}")
            print(f"    claim:      {(found.claim or '').strip()[:300]}")
            print(f"    reason:     {found.reason.strip()[:600]}")
            print()
    return 0


def _key(judge: AnthropicJudge, context) -> str:
    from driftwood.judge.context import context_hash

    return context_hash(
        context, judge.system, judge.model, request=judge._request()
    )


if __name__ == "__main__":
    raise SystemExit(main())
