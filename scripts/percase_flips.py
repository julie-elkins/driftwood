"""Did a budget change flip any case, one case at a time?

    uv run python scripts/percase_flips.py

Free by construction: it computes the same key the judge computes and reads the cache file. No
client is built, so a miss prints MISS rather than quietly costing money.

Per case, never as an F1. The ids in `PREDICTED` were selected because they failed, so every one
of them is a `drift` positive and `always-false` scores F1 1.00 over the set. The only readable
question is which NAMED case changed answer, next to what was predicted for it before the run.

Two things this got wrong on the first pass, both left as comments below because both would
silently produce a wrong comparison rather than an error:

  - taking the first cache hit by ceiling reports a stale 6,000-token truncation for any case the
    earlier run had already retried at 12,000, i.e. compares against a baseline worse than the one
    actually measured
  - a truncated reply is not a verdict. `TRUNCATED` in the `now` column means the prediction for
    that case is UNTESTED, not falsified, and counting it as a non-flip inflates the falsified
    count. Raising the doc budget is itself what truncated two of these, so this is not a rare path
"""
import json
from pathlib import Path

from driftwood.judge import DEFAULT_JUDGE_MODEL
from driftwood.judge.cases import load_cases
from driftwood.judge.context import ContextBuilder, context_hash
from driftwood.judge.judge import DEFAULT_MAX_TOKENS, SYSTEM_PROMPT

PREDICTED = {
    "3b7710af3aaa1c49": ("FLIP to false", "doc-cut, claim newly on screen"),
    "f6ff7af97ac3c31c": ("FLIP to false", "doc-cut, same page"),
    "884f8d4776cb8b02": ("FLIP to false", "doc-cut, claim whole at 18k"),
    "04a332fe0dc498cc": ("no flip", "claim not locatable in the page"),
    "e7df72235ade950f": ("no flip", "LIVE CONTROL: no shown file defines it"),
    "0eea9dc58ea4a754": ("no flip (guaranteed)", "byte-identical prompt"),
    "65463185f227a96c": ("no flip (guaranteed)", "byte-identical prompt"),
    "d0f54d7f2b930191": ("no flip (guaranteed)", "byte-identical prompt"),
    "756ac020b878f26e": ("no flip (guaranteed)", "byte-identical prompt"),
}

cases = {c.example_id: c for c in load_cases(Path("review"), Path("data"))[0]}
old = ContextBuilder(Path(".cache/clones"), doc_budget=12_000, code_budget=6_000)
new = ContextBuilder(Path(".cache/clones"), doc_budget=30_000, code_budget=6_000)


def cached(context, ceiling):
    key = context_hash(
        context, SYSTEM_PROMPT, DEFAULT_JUDGE_MODEL,
        request={"max_tokens": ceiling},
    )
    path = Path(".cache/judgements") / f"{key}.json"
    return json.loads(path.read_text()) if path.exists() else None


def verdict_of(entry):
    if entry is None:
        return "MISS", ""
    if entry.get("stop_reason") == "max_tokens":
        return "TRUNCATED", entry.get("stop_reason", "")
    try:
        payload = json.loads(entry["text"])
    except Exception:
        return "UNPARSED", (entry.get("text") or "")[:80]
    return payload.get("verdict", "?"), (payload.get("reason") or "")[:150]


print(f"{'case':<18}{'was (12k)':<12}{'now (30k)':<12}predicted")
print("-" * 100)
for eid, (pred, why) in PREDICTED.items():
    # Prefer a reply that is not truncated, whatever ceiling produced it. Taking the
    # first hit by ceiling reported the stale 6,000-token truncation for every case the
    # earlier run had already retried successfully at 12,000 -- which would have compared
    # this run against a baseline worse than the one that was actually measured.
    def best(builder):
        context = builder.build(cases[eid], "seeded")
        entries = [e for e in (cached(context, c) for c in (DEFAULT_MAX_TOKENS, 12_000)) if e]
        for entry in entries:
            if entry.get("stop_reason") != "max_tokens":
                return entry
        return entries[0] if entries else None

    before, after = best(old), best(new)
    bv, _ = verdict_of(before)
    av, reason = verdict_of(after)
    # A reply that ran out of tokens is not an answer, so it cannot be a flip. Saying
    # "FLIPPED" here read as evidence for the prediction when it was the absence of it.
    if av in ("TRUNCATED", "UNPARSED", "MISS"):
        flipped = f"UNTESTED ({av.lower()})"
    else:
        flipped = "FLIPPED" if bv != av else "same"
    print(f"{eid:<18}{bv:<12}{av:<12}{pred:<22}{flipped}")
    print(f"{'':18}{why}")
    if reason:
        print(f"{'':18}model: {reason}")
    print()
