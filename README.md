# Driftwood

Finds documentation that has quietly stopped being true about the code, and measures how
well it did.

Not a linter and not a spell-checker. The target is the class of defect no tool currently
catches: a README that promises a flag the code renamed, a tutorial whose import moved, a
compatibility claim that a `setup.py` change silently falsified two years ago. Docs do not
fail loudly. They just become wrong.

**Status: stage 1 of 5.** The ground-truth layer is built and measured. The retrieval and
agent layers are not. Everything below is a measurement, not a projection — where a number
is unreliable, this README says so.

---

## The part worth reading: two predictions, both wrong

Drift labels are mined from git history. When a human commit corrects documentation, the
tree immediately *before* that commit contained documentation that was false, and a human
confirmed it by fixing it. That is a label nobody had to hand-write.

Two candidate shapes were mined, because guessing which was cleaner seemed worse than
measuring:

- **Shape A — co-change.** One commit modifies a doc and some code, and the two diffs share
  an identifier.
- **Shape B — doc-only fix.** A commit modifies documentation and touches no code at all.
  The code did not move, so whatever was corrected was already false.

Shape B looked obviously cleaner on paper. Predictions were written down first, then two
rounds of hand labelling — 40 cases from one repo, then 45 from five:

| | predicted | round 1 (n=40) | round 2 (n=45) |
|---|---|---|---|
| shape A precision | ~35% | 6/20 = 30% [15%, 52%] | 7/25 = 28% [14%, 48%] |
| shape B precision | **~80%** | **0/20 = 0%**, ub 14% | **7/20 = 35% [18%, 57%]** |
| dominant shape-A error | `new` — feature plus its docs | **zero `new`** | **`new`, 8 of 25** |

Read down that table rather than across it, because almost every cell overturned something.

**Round 1.** The shape predicted to carry the project produced nothing at all, and `new` —
the failure mode the "only *modified* docs count" filter existed to defeat — did not occur
once. The obvious conclusion was that shape B was dead and `new` was a phantom risk.

**Round 2 falsified both of those conclusions.** Shape B went from provably nothing to the
better-scoring arm, with non-overlapping intervals. And `new` came back as the single largest
shape-A error class. Round 1 had drawn all 40 cases from one repo, and that repo was an
outlier in both respects — so the "lesson" learned from it was an artifact of the sample, and
believing it would have meant deleting the arm that now scores highest.

Note also what round 2 says about round 1's *fix*. Four filters were added between the rounds
and a retention test showed them keeping 6/6 true positives while dropping 14/14 false ones.
That looked decisive. On cases they had not been designed against, shape-A precision went
30% → 28%: **no measurable improvement.** The retention number was fitted to its own test
set, and this is what that costs.

This is the argument for building the eval harness before the model. Every wrong belief above
was held confidently, was reasonable given the evidence at the time, and was corrected only
by a measurement that did not care what had been predicted.

One limit stated plainly: rules *and* corpus changed between rounds, so neither before/after
is attributable to the rules alone. Separating them needs another labelling round drawn from
the held-out repo.

## One bug, three times

Tracing two true positives that a new filter discarded turned up a root cause that had
nothing to do with the filter. `_TOKEN_RE` requires a leading letter and token
normalisation dropped anything `isdigit()`, so **the identifier system was blind to version
numbers.** Two Python-version corrections survived only as the bare noun `python`, which a
platform stoplist then removed. They looked like stoplist casualties; the claim itself had
never been tokenisable.

The same bug appeared twice more:

| documentation change | registered as | why |
|---|---|---|
| `Python 3.7` → `3.8` | no change | version literals unextractable |
| `verify=True` → `verify=False` | no change | `True`/`False` stoplisted as prose |
| `timeout=None` → `timeout=30` | no change | bare integers dropped as digits |

Three instances of one disease: *the token carrying the factual claim was the one the
tokeniser threw away.* The fix is principled rather than a patch — inside a marked-up code
span the stoplist and the digit filter are switched **off**, because there `True` and `30`
are code, not English. All nine cases are regression tests in `tests/test_identifiers.py`.

## What is honest about the current numbers, and what is not

The only numbers here that are unbiased estimates are the round-2 ones, because round 2 was
labelled after the rules were frozen and drawn from repos the rules had not been tuned
against:

```
shape A   7/25 = 28%   95% CI [14%, 48%]
shape B   7/20 = 35%   95% CI [18%, 57%]
```

Shape B nominally leads, but those intervals overlap almost completely — the ordering of the
two arms is **not** established by this data, and any claim that one is better needs a larger
sample than 45 cases.

Two further rule changes are priced against round 2 and project shape A to 38% and shape B to
41%. **Those two figures are hypotheses, not results**, for the same reason the round-1
retention number was: they were designed against the cases they are scored on. They get
believed or discarded by a round 3.

The recall side is unmeasured throughout. Precision is cheap to estimate from a sample of
what a rule fires on; recall needs to know what it missed, which needs labelled cases the
rule rejected. That work is not done, so **no claim is made here about how much drift this
finds** — only about how much of what it flags is real.

Other limits, stated rather than buried:

- **A doc nobody fixed is not a doc that was correct.** It may be drift nobody noticed.
  Positives here are strong evidence; negatives are weak, and no published false-positive
  rate is meaningful without that caveat.
- **The first 40 cases all came from one repo**, `psf/requests`, which turned out to be an
  outlier. Measured on the pre-filter corpus it yielded 61 shape-A positives against 785
  shape-B — 12.9:1 — where every other repo was balanced or the reverse (pydantic 809:348, a
  ratio of 0.4). Shape A was being judged from the one repo that barely produces it. The
  corpus is now five repos and the sampler takes a `--repo` filter so a draw cannot silently
  come from one again. (Those ratios are from the corpus as it stood when the confound was
  found; the shape-B filters below have since cut that arm by about 4x, so the current
  manifests show different absolute counts.)
- **`doc_literals_only` trades recall for precision knowingly.** A doc naming a symbol in
  bare prose without backticks is invisible to shape B. The two shape-B filters together cut
  that arm from 2788 candidates to 523 — 5.3x — and the decision was taken when shape B had
  zero demonstrated positives, so precision was the only measurable quantity. Round 2 then
  found 7 positives in the surviving set, which means the cut can no longer be assumed free:
  a 5.3x reduction on an arm that does contain real drift is now a recall risk nobody has
  measured.
- **The English and platform stoplists are hand-built and will miss whole families.** A
  known live example: a reworded sentence still leaks the token `well`.

## Reproducibility

Every mine writes a manifest next to its output recording each repo's pinned sha, the commit
window, the full rule config, and a sha256 of the result. Its `replay` field regenerates the
label set byte-identically — verified, not assumed:

```
$ driftwood mine --out labels.jsonl --limit 4000 --pin psf/requests=dae7ef6...
$ # sha256 in the new manifest matches the old one
```

The manifest has already earned its keep as more than a replay mechanism. It records how many
examples were written; the scorer keys by `example_id` and reported two fewer. That
two-example gap was a duplicate-id bug — the same doc state corrected by two sibling commits,
counted twice, and silently collapsed by every dict-keyed consumer. No error, no warning, just
two numbers that disagreed. Nothing else in the system would have surfaced it, and it is
fixed with a regression test that reproduces the cherry-pick shape in a scratch repo.

This is why the mined `.jsonl` files are gitignored while the manifests are committed. The
label sets are derived data — one day of iteration produced seven of them, 16 MB — and
provenance is the thing worth versioning. Two exceptions are tracked deliberately:
`review/*.md`, the hand labels, which are irreplaceable; and `data/labels.jsonl`, the one
label set that predates manifests and therefore cannot be regenerated.

## Design notes

- **Zero dependencies in the mining stage** (pytest aside). The ground-truth layer should be
  regenerable in CI years from now without resolving an inference stack. The dependency
  budget gets spent later, where it buys something.
- **`label_basis` on every record, not just `label`.** A blended precision number can be
  reported but not improved; per-basis precision tells you what to fix.
- **Stable `example_id`** — sha256 of repo/sha/paths/label. Makes label sets diffable across
  runs, and makes it possible to score a subtractive rule change against existing hand
  labels without relabelling anything. It omits the *fixing* commit deliberately, because it
  identifies the tree state being labelled rather than the commit that corrected it — so two
  cherry-picked fixes off one base collide, and collapsing them is right. The miner
  deduplicates; matched negatives key on the fix instead and stay distinct, because those
  really are two different trees.
- **Every proportion carries a 95% Wilson interval.** 6/20 reads as "30%" but spans 15% to
  52%; a twenty-case sample cannot distinguish 30% from 45%. Reporting the point estimate
  alone is how you come to believe a threshold change helped when it did nothing.
- **`unclear` counts as a miss, not as excluded.** A case a competent reviewer cannot
  adjudicate from the evidence the miner surfaced is a case the miner should not have
  surfaced.
- **Matched negatives**: the same doc/code pair at the fixing commit itself. Same file, same
  repo, seconds apart in project time, differing only in whether the correction landed. A
  detector that fires equally on both is not detecting drift.

## Roadmap

| stage | state |
|---|---|
| 1 · Ground-truth miner + eval harness | **built, measured** |
| 2 · Retrieval — embeddings, then a cross-encoder reranker, each against a measured baseline | next |
| 3 · Claim typing and verification agents | designed |
| 4 · Null-run harness — same input twice, to establish the noise floor | designed |
| 5 · GitHub App + CI eval gate | designed |

Stage 3 is not architecture on faith. Version-support claims turned out to be a class that
identifier overlap provably cannot handle: `docs/index.rst` asserting "supports Python 3.7"
against `setup.py`'s `python_requires` needs a matcher that compares version numbers to
packaging metadata, not one that looks for shared symbols. The `ver:` tokens above are a
workaround that makes such claims *visible* to a generic matcher rather than matching them
correctly. A measurement demanded that stage; it was not drawn on a diagram first.

## Usage

```
uv sync
uv run driftwood mine --repos psf/requests pallets/flask --limit 4000 --out data/labels.jsonl
uv run driftwood stats --labels data/labels.jsonl
uv run driftwood sample --labels data/labels.jsonl --shape A -n 25 --out review/batch.md
uv run driftwood score review/batch.md --labels data/labels.jsonl
uv run pytest
```

`sample` writes a review sheet a human fills in; `score` reads the verdicts back and reports
precision per shape and per basis with intervals. `retention` checks how a rebuilt label set
treats already-judged cases, which is valid for subtractive rule changes only.

## Licence

MIT.
