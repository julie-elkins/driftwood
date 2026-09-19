"""How many claims are on a page, and what does asking about them one at a time cost?

    PYTHONPATH=scripts uv run python scripts/claim_units.py

Free: git, the renderer, and the usage already recorded in `.cache/judgements`. No API
call and nothing sent -- it reads bills that have been paid, which is the only honest
source for the output half of section 3. Written because the
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
    section 3  what the prompt's current section ORDER costs, and what decides the
               design once order turns out not to

`render` puts the document first and the code after it, so under per-claim prompting the
varying part sits at the FRONT of the prompt and no shared prefix exists to cache.
Reordering it -- code first, claim last -- is what makes the cached design affordable.

An earlier version of this docstring added that the reordering orphans every judgement
already bought, and drew the design decision from that. It does not: a per-claim arm
needs a new rendering whatever order it picks, so both designs start from an empty cache
and order is free. What separates them is the CALL COUNT -- output tokens, and whether
the advertised price depends on cache hits the harness cannot verify in advance. Section
3 prints both. The wrong version is in this file's own commit message, which is pushed
and is left alone; corrections belong in the file, not in rewritten history.

WHAT A "CLAIM UNIT" IS HERE, and it is a proxy rather than a definition: a sentence from
the page's prose that marks up at least one identifier, using the same `literal_spans`
signal `select_relevant` already selects code with. It deliberately does not use the
miner's `shared_identifiers`, so the count is one a judge could compute at inference time
on a page nobody has labelled. It will be wrong at the edges -- a claim spanning two
sentences counts twice, a directive block counts as none -- so read it as a cost estimate
to within about 20% and not as a taxonomy. The decision it informs does not turn on the
third significant figure.

The definition lives in `driftwood.judge.claims` and is IMPORTED here. It was copied here
first, and the copy went stale the moment the package version learned to skip the body of
a fenced block: this script reported 1,240 units where the judge would have asked about
1,195, disagreeing on 8 of the 45 cases about what the arm does. The numbers below are the
ones the built judge produces. Two implementations of one rule with no test between them is the
thing this repository exists to find, and it was in the file doing the finding.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
from pathlib import Path

from driftwood.judge.cases import load_cases
# THE SAME enumeration the judge uses, imported rather than reimplemented. This script had
# its own copy for exactly as long as it took the package version to gain a fix the copy
# did not have -- a fence body came through as prose here and not there -- so the pricing
# table described a design nobody was going to build. Two implementations of one rule, one
# of them quietly stale, is this repository's entire subject; it is not going to be the
# shape of the script that prices the work.
from driftwood.judge.claims import DEFAULT_BATCH as BATCH, claim_units
from driftwood.judge.context import CODE_BUDGET, DOC_BUDGET, ContextBuilder, render
from driftwood.judge.evaluate import estimate_spend
from driftwood.judge.judge import DEFAULT_MAX_TOKENS, SYSTEM_PROMPT
from driftwood.mining.gitio import ensure_clone, read_blobs


def tokens(prompt: str) -> int:
    """Input tokens for one prompt, by the constant the tool measured off its own bill."""
    spend = estimate_spend([prompt], system=SYSTEM_PROMPT, max_tokens=DEFAULT_MAX_TOKENS)
    return int(spend["input_tokens_approx"])


def billed_output(cache: Path) -> dict[str, float] | None:
    """Output tokens a call, READ OFF the replies already paid for, or None if none are.

    The first version of section 3 asserted "the last paid run averaged ~3,900 output
    tokens a call" and hardcoded it. The cache disagrees: over the replies with usage
    recorded, the mean is nearer 1,700 and the median nearer 700, so ~3,900 is about the
    90th percentile of a long-tailed distribution being quoted as its centre. It
    overstated the output half of the design by roughly 2.3x, in the EXPENSIVE-looking
    direction -- the safe direction for a go/no-go, and still a made-up number in the
    file whose whole job is to not print one. Sixth false claim about this code found
    inside this project, after the fence body two paragraphs up in the module docstring.

    So it is measured now rather than asserted, and the skew is printed rather than
    averaged away, because a mean over these is not a typical call.
    """
    tokens_out = []
    for path in sorted(cache.glob("*.json")):
        try:
            reply = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if reply.get("output_tokens") is not None:
            tokens_out.append(int(reply["output_tokens"]))
    if not tokens_out:
        return None
    return {
        "n": len(tokens_out),
        "mean": statistics.mean(tokens_out),
        "median": statistics.median(tokens_out),
        "p90": sorted(tokens_out)[int(len(tokens_out) * 0.9)],
        "max": max(tokens_out),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/judgements"))
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
        f"\n  CALL count rather than the token count: {calls_batch:,} calls is {calls_batch / calls_page:.1f}x the reply"
        f"\n  volume of {calls_page}. That lands the multiplier for the total near the input"
        "\n  multiplier rather than below it, so read these as the whole design's shape"
        "\n  and not as a bill."
    )

    print("\nSECTION 3 -- the prompt's section order, and why it is NOT the tiebreak")
    print(
        "  `render` emits the DOCUMENT first and the code after it. Under per-claim\n"
        "  prompting the claim is the part that varies, so it sits at the front and\n"
        "  there is no shared prefix to cache: the unchanged-prompt row above is what\n"
        f"  today's order costs, {naive / page_total:.0f}x one pass. Code first and the\n"
        "  claim last is the same information in the other order, and it is the\n"
        "  difference between an arm that can be run and one that cannot.\n"
        "\n"
        "  CORRECTION, and the first version of this section got it backwards. It said\n"
        "  the reordering orphans every judgement already bought, because it is inside\n"
        "  the cache key. The premise is true of `render` and the conclusion does not\n"
        "  follow: a per-claim arm needs a NEW rendering either way -- the claim has to\n"
        "  reach the prompt somehow -- so both designs produce new keys and neither can\n"
        "  reuse one existing reply. Order is free to choose here. A false claim about\n"
        "  this code, in this repository, is the fourth of its kind and is left visible\n"
        "  rather than quietly rewritten."
    )
    # The two reasons that DO separate the designs, and both are about the call count
    # rather than the token count, which is why the input table above cannot see them.
    billed = billed_output(args.cache)
    if billed is None:
        anchor = (
            "     There is NO anchor for output on this machine: no cached reply carries\n"
            "     usage, so the output half of this argument is unmeasured. It rests on\n"
            "     the call ratio alone, which is enough for the direction and not for a\n"
            "     figure."
        )
    else:
        anchor = (
            f"     Output per call, off the {billed['n']} replies already paid for: median\n"
            f"     {billed['median']:,.0f}, mean {billed['mean']:,.0f}, p90 {billed['p90']:,.0f}, max {billed['max']:,} -- long-tailed, so read the\n"
            f"     median and not the mean. Those are PER-PAGE replies and neither design\n"
            "     sends that prompt: a single-claim reply is shorter and a batch of\n"
            f"     {BATCH} is longer, so this does NOT multiply out to a total for either.\n"
            "     What it does bound is the FIXED part -- the preamble and the reasoning\n"
            f"     every reply pays before its first verdict. {calls_claim:,} replies pay that\n"
            f"     {calls_claim / calls_batch:.1f}x as often as {calls_batch:,} do, on the same {sum(counts):,} verdicts."
        )
    print(
        f"""
  WHAT ACTUALLY DECIDES IT, now that order does not:

  1. OUTPUT. The cached design needs {calls_claim:,} replies to batching's {calls_batch:,}, a
     {calls_claim / calls_batch:.1f}x ratio in CALL count, and output is billed above input.
{anchor}
     Input parity ({cached_priced / page_total:.1f}x against {batched / page_total:.1f}x) is therefore not cost parity, and
     the input table above is the thing that cannot see it.

  2. WHAT EACH ONE NEEDS TO BE TRUE. Batching needs nothing. The {cached_priced / page_total:.1f}x needs
     every one of a page's calls to land inside the prompt cache's TTL, in order,
     with the prefix byte-identical. If that does not hold, the design does not
     cost {cached_priced / page_total:.1f}x -- it costs the {naive / page_total:.0f}x row, because the reads are simply
     fresh input. A price that can move {naive / cached_priced:.0f}-fold on a behaviour the harness
     cannot check beforehand is the worse bet at equal advertised cost."""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
