"""Do the label and the judge answer the same question? And did the budget cut the answer?

    uv run python scripts/unit_mismatch_audit.py --arm seeded --retry-max-tokens 12000

Two audits, both free: git and `.cache/judgements` only, no API call possible. Written
after the 2026-09-19 cache audit raised two questions it could not settle by reading
prose.

**1a -- the unit question.** The hand label describes what THE COMMIT changed
(`cosmetic` = "wording, formatting or a link -- nothing factual changed"). The judge is
asked about THE PAGE ("at the parent commit, was this documentation false about the
code?"). A page can carry a false statement the commit never touched, and then a correct
`false` answer is scored as a false positive. This locates the model's own quoted claim
in the parent document and reports which it came from:

    in-changed-prose   the claim is in what this commit added or removed
    elsewhere-on-page  the claim is in the parent page, but the commit did not touch it
    not-locatable      the claim does not match the page (paraphrase, or reformatted)

The diagnostic reading is the SPLIT BY SCORE. If false positives skew
`elsewhere-on-page` while true positives skew `in-changed-prose`, the mismatch is
mechanical rather than inferred, and measured precision is partly a taxonomy artefact.

**1b -- the budget question.** 75% of shown code files are cut, but "cut" is not the same
as "the answer was cut". For each identifier the commit DELETED from the prose -- the
false claim's own vocabulary -- this checks whether a *definition* of it exists in the
full text of a shown file but not in the windowed text actually sent. That is the budget
removing the answer, as distinct from the model seeing it and affirming agreement anyway.

Definition, not mention, and deliberately so: `oracle_file_audit.py` already established
that identifier PRESENCE proves nothing, because `requests/__init__.py` scores ~100% by
re-exporting names it does not implement. A regex for `def`/`class`/module-level
assignment is still an approximation -- it will miss a name bound by a decorator, a
metaclass or a conditional import -- so a zero here is weaker evidence than a positive.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from driftwood.judge.cases import load_cases
from driftwood.judge.context import ContextBuilder, context_hash
from driftwood.judge.judge import AnthropicJudge
from driftwood.mining import identifiers
from driftwood.mining.gitio import changed_sides, ensure_clone, file_diff, read_blobs

_WS = re.compile(r"\s+")
# Markup that differs between a doc source and how a model retypes a quote from it.
# Stripped from both sides, so `` `foo` `` and `foo` compare equal rather than counting
# as a paraphrase and landing in `not-locatable`, which would understate both buckets.
_MARKUP = re.compile(r"[`*_\\]|::|^\s*[-+]\s*", re.MULTILINE)


class _NoSpend:
    def __getattr__(self, name: str):
        raise AssertionError(
            "this audit reads the cache and must never call the API -- a reply is "
            "missing for the ceilings requested, so re-check --arm/--max-tokens/"
            "--retry-max-tokens against the run you meant to audit"
        )


def norm(text: str) -> str:
    return _WS.sub(" ", _MARKUP.sub("", text)).strip().lower()


def shingles(text: str, n: int = 4) -> set[str]:
    words = text.split()
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def overlap(claim: str, hay: str) -> float:
    """Fraction of the claim's word 4-grams present in `hay`."""
    cs = shingles(claim)
    if not cs:
        return 0.0
    hs = shingles(hay)
    return len(cs & hs) / len(cs)


def locate(claim: str, touched: str, page: str, *, floor: float = 0.5) -> str:
    c = norm(claim)
    if len(c) < 12:
        return "claim too short to locate"
    t, p = norm(touched), norm(page)
    if c in t:
        return "in-changed-prose"
    if c in p:
        return "elsewhere-on-page"
    ot, op = overlap(c, t), overlap(c, p)
    # Touched wins ties on purpose: the touched text is a subset of the page, so a claim
    # inside it also scores against the page, and reporting that as `elsewhere` would
    # invent the very mismatch this script exists to test for.
    if ot >= floor and ot >= op:
        return "in-changed-prose"
    if op >= floor:
        return "elsewhere-on-page"
    return "not-locatable"


_DEF = "|".join(
    (
        r"^\s*(?:async\s+)?def\s+{n}\b",
        r"^\s*class\s+{n}\b",
        r"^{n}\s*(?::[^=\n]+)?=",
        r"^\s*{n}\s*(?::[^=\n]+)?=",
    )
)


def defines(text: str, name: str) -> bool:
    pattern = _DEF.format(n=re.escape(name))
    return re.search(pattern, text, re.MULTILINE) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("review"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/judgements"))
    parser.add_argument("--arm", default="seeded", choices=("oracle", "seeded"))
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--retry-max-tokens", type=int, default=None)
    args = parser.parse_args()

    cases = [c for c in load_cases(args.review, args.data)[0] if c.code_path]
    builder = ContextBuilder(args.clone_root)
    judge = AnthropicJudge(
        cache_dir=args.cache,
        client=_NoSpend(),
        **{
            k: v
            for k, v in (
                ("max_tokens", args.max_tokens),
                ("retry_max_tokens", args.retry_max_tokens),
            )
            if v is not None
        },
    )

    rows = []
    for case in cases:
        context = builder.build(case, args.arm)
        if not context.usable:
            continue
        key = context_hash(
            context, judge.system, judge.model, request=judge._request()
        )
        if not (args.cache / f"{key}.json").exists():
            continue
        found = judge.judge(context)
        answer = {True: "false", False: "not-false", None: "unclear"}[found.answer]

        clone = ensure_clone(case.repo, args.clone_root)
        diff = file_diff(clone, case.at_sha, case.fix_sha, case.doc_path)
        added, removed = changed_sides(diff)
        page = read_blobs(clone, case.at_sha, [case.doc_path]).get(case.doc_path, "")

        # Scoring, replicating the harness: positive class is `drift`.
        if case.verdict == "drift":
            score = "tp" if answer == "false" else ("fn" if answer == "not-false" else "abstain")
        else:
            score = "fp" if answer == "false" else ("tn" if answer == "not-false" else "abstain")

        where = (
            locate(found.claim, added + "\n" + removed, page)
            if (found.claim or "").strip()
            else "no claim quoted"
        )
        rows.append((case, found, answer, score, where, context, removed))

    print(f"{len(rows)} case(s) read from cache for arm `{args.arm}`\n")

    print("=== 1a. WHERE THE MODEL'S QUOTED CLAIM CAME FROM, BY SCORE ===\n")
    by_score: dict[str, Counter] = {}
    for _c, _f, _a, score, where, _ctx, _rm in rows:
        by_score.setdefault(score, Counter())[where] += 1
    for score in ("tp", "fp", "fn", "tn", "abstain"):
        if score not in by_score:
            continue
        total = sum(by_score[score].values())
        print(f"  {score} (n={total})")
        for where, n in by_score[score].most_common():
            print(f"      {n:>3}  {where}")
        print()

    flagged = [r for r in rows if r[3] in ("tp", "fp")]
    print("  The comparison that matters -- only the cases it answered `false`:\n")
    for score in ("tp", "fp"):
        grp = [r for r in flagged if r[3] == score]
        if not grp:
            continue
        inside = sum(1 for r in grp if r[4] == "in-changed-prose")
        outside = sum(1 for r in grp if r[4] == "elsewhere-on-page")
        other = len(grp) - inside - outside
        print(
            f"      {score}: {inside}/{len(grp)} in-changed-prose, "
            f"{outside}/{len(grp)} elsewhere-on-page, {other} other"
        )
    print()
    print("  The `fp` cases, one line each:\n")
    for case, _f, _a, score, where, _ctx, _rm in rows:
        if score != "fp":
            continue
        print(f"      [{where:<18}] {case.verdict:<9} {case.repo} {case.doc_path}")
    print()

    print("=== 1b. DID THE CODE BUDGET CUT THE ANSWER? ===\n")
    print("Identifiers the commit DELETED from the prose, and whether a definition of")
    print("one survived into the windowed text that was actually sent.\n")
    tally = Counter()
    for case, _f, _a, score, _w, context, removed in rows:
        if score not in ("fn", "abstain") or case.verdict != "drift":
            continue
        wanted = identifiers.extract(removed)
        full = builder._code_texts(case.repo, case.at_sha)
        shown_paths = [f.path for f in context.code_files]
        defined_full = {
            n for n in wanted if any(defines(full.get(p, ""), n) for p in shown_paths)
        }
        defined_shown = {
            n
            for n in wanted
            if any(defines(f.text, n) for f in context.code_files)
        }
        cut = defined_full - defined_shown
        verdict = "BUDGET CUT THE DEFINITION" if cut else (
            "definition was on screen" if defined_shown else "no definition in any shown file"
        )
        tally[f"{score}: {verdict}"] += 1
        # The `example_id` first, because it is the thing `judge-eval --only-cases` takes.
        # Without it the diagnosis has to be re-derived by hand from repo + path to be
        # acted on, and re-typing a sha-shaped id is how one of them becomes another case.
        print(f"  [{score}] {case.example_id}  {case.repo} {case.doc_path}")
        print(f"        deleted-prose identifiers: {len(wanted)}")
        print(f"        defined in a shown file (full text):   {len(defined_full)}")
        print(f"        still defined in the windowed text:    {len(defined_shown)}")
        print(f"        -> {verdict}" + (f" ({sorted(cut)[:6]})" if cut else ""))
        print()
    print("  Summary:")
    for key, n in sorted(tally.items()):
        print(f"      {n:>3}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
