"""How many claims are on a page, and what does asking about them one at a time cost?

    PYTHONPATH=scripts uv run python scripts/claim_units.py

Free: git and the renderer only, no API call and no cache read. Written because the
doc-budget probe settled that the judge does not audit a whole page -- it answered
`not-false` with an empty claim field on a 38,830-character page, reasoning only about
the opening and never reaching the sentence under test at character 22,461. The lever
that failed was context. The lever it points at is asking one claim at a time.

That design has to be priced before it is built, and the price is not the obvious one.
`--doc-budget 30000` cost $0.60 because it changed one number. Per-claim prompting
multiplies the number of CALLS by the claims on a page, and the code side rides along on
every one of them -- k=5 files at 6,000 characters is 30,000 characters of code against
at most 12,000 of document, so the expensive half of the prompt is the half that does not
vary. Naive per-claim prompting therefore does not cost N times the document, it costs N
times the whole context.

    section 1  claim units per page, and the distribution, because a median hides the
               38,830-character pages that motivated this
    section 2  input tokens under four designs, as multiples of what is already paid
    section 3  what the prompt's current section ORDER costs, which is the finding

Section 3 is the one that changes a decision. `render` puts the document first and the
code after it, so under per-claim prompting the varying part sits at the FRONT of the
prompt and no shared prefix exists to cache. Reordering it -- code first, claim last --
is what makes the design affordable, and reordering is inside the cache key, so it
orphans every judgement already bought. That is a thing to get right once rather than
discover after a run.

WHAT A "CLAIM UNIT" IS HERE, and it is a proxy rather than a definition: a sentence from
the page's prose that marks up at least one identifier, using the same `literal_spans`
signal `select_relevant` already selects code with. It deliberately does not use the
miner's `shared_identifiers`, so the count is one a judge could compute at inference time
on a page nobody has labelled. It will be wrong at the edges -- a claim spanning two
sentences counts twice, a directive block counts as none -- so read it as a cost estimate
to within about 20% and not as a taxonomy. The decision it informs does not turn on the
third significant figure.
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import statistics
from pathlib import Path

from driftwood.judge.cases import load_cases
from driftwood.judge.context import CODE_BUDGET, DOC_BUDGET, ContextBuilder, render
from driftwood.judge.evaluate import estimate_spend
from driftwood.judge.judge import DEFAULT_MAX_TOKENS, SYSTEM_PROMPT
from driftwood.mining.gitio import ensure_clone, read_blobs
from driftwood.mining.identifiers import extract, literal_spans

# Claims are batched at this many per call in the fourth design. 8 is not tuned -- it is
# the value that makes the arithmetic legible, and section 2 prints the whole curve so a
# different one can be read off rather than argued for.
BATCH = 8

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# Lines that are not prose: rst directives, fenced code, indented blocks, table rules,
# underlines. Counted as part of no unit, which undercounts pages that make claims
# entirely inside a table. Named so the undercount is a known direction, not a surprise.
_NOT_PROSE = re.compile(
    r"^\s*(?:\.\.\s|```|~~~|\||[-=~^\"'+*#]{3,}\s*$|>>>|\$\s)|^\s{4,}\S"
)


def claim_units(text: str) -> list[str]:
    """The page's prose sentences that mark up at least one identifier."""
    units: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.splitlines() if not _NOT_PROSE.match(ln)]
        if not lines:
            continue
        prose = " ".join(ln.strip() for ln in lines).strip()
        if not prose:
            continue
        for sentence in _SENTENCE_END.split(prose):
            sentence = sentence.strip()
            if not sentence:
                continue
            if extract(literal_spans(sentence), versions=False):
                units.append(sentence)
    return units


def tokens(prompt: str) -> int:
    """Input tokens for one prompt, by the constant the tool measured off its own bill."""
    spend = estimate_spend([prompt], system=SYSTEM_PROMPT, max_tokens=DEFAULT_MAX_TOKENS)
    return int(spend["input_tokens_approx"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--arm", default="seeded", choices=("oracle", "seeded"))
    args = parser.parse_args()

    cases = [c for c in load_cases(args.review, args.data)[0] if c.code_path]
    builder = ContextBuilder(args.clone_root)
    print(
        f"arm `{args.arm}`, k={builder.k}, DOC_BUDGET={DOC_BUDGET:,}, "
        f"CODE_BUDGET={CODE_BUDGET:,}, {len(cases)} shape-A cases\n"
    )

    rows = []
    for case in sorted(cases, key=lambda c: c.example_id):
        clone = ensure_clone(case.repo, args.clone_root)
        raw_doc = read_blobs(clone, case.at_sha, [case.doc_path]).get(case.doc_path, "")
        context = builder.build(case, args.arm)

        # Units are counted on the WHOLE page, not the truncated one. The point of the
        # design is to stop losing the tail of a long page, so pricing it off the cut
        # version would price the problem away.
        units = claim_units(raw_doc)

        page = tokens(render(context))
        # The context with no document in it at all: the part every per-claim call would
        # repeat. Measured rather than subtracted, so the section headers and the code
        # markers are counted where they actually fall.
        shared = tokens(render(dataclasses.replace(context, doc_text="", doc_truncated=False)))
        per_unit = [
            tokens(render(dataclasses.replace(context, doc_text=u, doc_truncated=False)))
            - shared
            for u in units
        ]
        rows.append(
            {
                "id": case.example_id,
                "repo": case.repo,
                "doc": case.doc_path,
                "chars": len(raw_doc),
                "units": len(units),
                "page": page,
                "shared": shared,
                "unit_tokens": sum(per_unit),
            }
        )

    counts = [r["units"] for r in rows]
    print("SECTION 1 -- claim units per page")
    print(f"  total units across {len(rows)} pages: {sum(counts):,}")
    print(
        f"  per page: median {statistics.median(counts):.0f}, "
        f"mean {statistics.mean(counts):.1f}, min {min(counts)}, max {max(counts)}"
    )
    empty = [r for r in rows if r["units"] == 0]
    if empty:
        # A page with no marked-up prose sentence has nothing for a per-claim judge to
        # ask about, so the design abstains on it by construction rather than by
        # judgement. Reported because it is a cost of the design and not a bug: the
        # per-page judge at least sees such a page and can answer about it.
        print(f"  {len(empty)} page(s) have NO claim unit at all, so a per-claim judge")
        print("  has nothing to ask and abstains by construction:")
        for r in empty:
            print(f"    {r['chars']:>7,} chars  {r['repo']:<18} {r['doc']}")
    print("  the ten largest, which are the pages the probe failed on:")
    for r in sorted(rows, key=lambda r: -r["units"])[:10]:
        print(
            f"    {r['units']:>4} units  {r['chars']:>7,} chars  "
            f"{r['repo']:<18} {r['doc']}"
        )

    page_total = sum(r["page"] for r in rows)
    naive = sum(r["units"] * r["shared"] + r["unit_tokens"] for r in rows)
    reordered = sum(r["shared"] + r["unit_tokens"] for r in rows)
    batched = sum(
        -(-r["units"] // BATCH) * r["shared"] + r["unit_tokens"] for r in rows
    )
    # The cached design at its published prices rather than at zero. A cache WRITE is
    # billed above fresh input and a READ below it, so a prefix reused N times is not
    # free N-1 times -- and with a 7,000-token prefix and 28 claims a page, the reads
    # are the largest single item in the whole design. Charging them at zero produced a
    # row cheaper than the run already paid for, which is the shape of a number that
    # flatters. Token-equivalents, not currency, for the same reason everything else
    # here is: a price table in this file would be stale within a quarter.
    CACHE_WRITE, CACHE_READ = 1.25, 0.10
    cached_priced = sum(
        round(CACHE_WRITE * r["shared"] + CACHE_READ * r["shared"] * max(r["units"] - 1, 0))
        + r["unit_tokens"]
        for r in rows
    )
    calls_page = len(rows)
    calls_claim = sum(counts)
    calls_batch = sum(-(-c // BATCH) for c in counts)

    print("\nSECTION 2 -- input tokens for one pass over the arm")
    print(f"  {'design':<44} {'calls':>7} {'input tokens':>14} {'vs now':>8}")
    for label, calls, total in (
        ("per page, as measured today", calls_page, page_total),
        ("per claim, prompt unchanged", calls_claim, naive),
        (f"per claim, batched {BATCH} to a call", calls_batch, batched),
        ("per claim, code first, cache reads priced", calls_claim, cached_priced),
        ("per claim, code first, reads free (a FLOOR)", calls_claim, reordered),
    ):
        print(f"  {label:<44} {calls:>7,} {total:>14,} {total / page_total:>7.1f}x")
    print(
        "\n  Read the priced row and not the floor below it. The floor charges cache"
        "\n  reads at zero and comes out CHEAPER than the pass already paid for, which"
        "\n  is what a flattering number looks like from the inside; at published"
        f"\n  multipliers ({CACHE_WRITE} to write, {CACHE_READ} to read) the same design is"
        f"\n  {cached_priced / page_total:.1f}x, because a {statistics.median([r['shared'] for r in rows]):,.0f}-token"
        "\n  prefix re-read 28 times a page is the largest item in the design rather"
        "\n  than a rounding error. Batching is the version that needs no cache"
        "\n  behaviour to be true, and it is within a factor of the priced row."
    )
    print(
        "\n  INPUT ONLY. Output is billed too, at a higher rate, and it scales with the"
        "\n  CALL count rather than the token count -- the last paid run averaged ~3,900"
        "\n  output tokens a call, so 173 calls is roughly four times the reply volume of"
        "\n  45. That lands the multiplier for the total near the input multiplier rather"
        "\n  than below it, so read these as the whole design's shape and not as a bill."
    )

    print("\nSECTION 3 -- the prompt's section order is what decides this")
    print(
        "  `render` emits the DOCUMENT first and the code after it. Under per-claim\n"
        "  prompting the claim is the part that varies, so it sits at the front and\n"
        "  there is no shared prefix to cache: the unchanged-prompt row above is what\n"
        f"  today's order costs, {naive / page_total:.0f}x one pass. Code first and the\n"
        "  claim last is the same information in the other order, and it is the\n"
        "  difference between an arm that can be run and one that cannot.\n"
        "\n"
        "  That reordering is INSIDE the cache key -- it changes the rendered context --\n"
        "  so it orphans every judgement already paid for on every arm. It is therefore\n"
        "  a decision to take once, before the first per-claim call, and not a tweak."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
