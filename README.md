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

## The part worth reading: three rounds, wrong three different ways

Drift labels are mined from git history. When a human commit corrects documentation, the
tree immediately *before* that commit contained documentation that was false, and a human
confirmed it by fixing it. That is a label nobody had to hand-write.

Two candidate shapes were mined, because guessing which was cleaner seemed worse than
measuring:

- **Shape A — co-change.** One commit modifies a doc and some code, and the two diffs share
  an identifier.
- **Shape B — doc-only fix.** A commit modifies documentation and touches no code at all.
  The code did not move, so whatever was corrected was already false.

Shape B looked obviously cleaner on paper. Predictions were written down first, every time,
then hand-labelled — 40 cases from one repo, 45 from five, then 20 drawn to settle a
specific question:

| | predicted | round 1 (n=40) | round 2 (n=45) | round 3 (n=20) |
|---|---|---|---|---|
| shape A precision | ~35% | 6/20 = 30% [15%, 52%] | 7/25 = 28% [14%, 48%] | — |
| shape B precision | **~80%** | **0/20 = 0%**, ub 14% | **7/20 = 35% [18%, 57%]** | 5/20 = 25% [11%, 47%] |
| dominant shape-A error | `new` — feature plus its docs | **zero `new`** | **`new`, 8 of 25** | — |

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

**Round 3 was designed to answer one question**, because round 2 had left rules and corpus
confounded — both changed at once, so neither before/after was attributable to the rules
alone. Twenty fresh shape-B cases from `psf/requests`, the repo that had scored 0/20, under
the current rules. Round 2's shape-B sample happened to contain no `requests` cases at all,
so the two comparisons each vary exactly one thing:

| contrast | holds fixed | varies | result | Fisher p |
|---|---|---|---|---|
| round 3 vs round 1 | repo | rules | 0/20 → 5/20 | **0.047** |
| round 3 vs round 2 | rules | repo | 25% vs 41% | 0.48 |

**The rules get the credit.** Shape B improved on the very repo where it had measured zero,
out of sample, and there is no detectable repo effect left. That confound is retired.

And then the interesting part. Four predictions were recorded before labelling; the point
estimate was called *exactly* — 5 of 20 — and the mechanism behind it was still wrong:

> **The dominant error class is now `unclear`, not `cosmetic`. Round 1 was 12/20 cosmetic and
> the new filters drop all 12.**

Cosmetic went 12/20 → 10/20 (p = 0.75). It is still the largest class; the gain came out of
`unclear` instead. The filters select on *evidence shape* — was a marked-up literal withdrawn,
is this a tutorial renumber — and "cosmetic" is not an evidence shape. It arrives in all of
them. So the filters removed round 1's particular cosmetic cases without reducing the rate at
which the arm admits cosmetic ones, exactly as the fitted retention number had implied and
exactly as the fresh sample denied.

**Being right about the number is not being right about the cause**, and only the error
breakdown could tell the two apart. A harness that reported precision alone would have
scored this round as a clean confirmation.

This is the argument for building the eval harness before the model. Every wrong belief above
was held confidently, was reasonable given the evidence at the time, and was corrected only
by a measurement that did not care what had been predicted.

## One bug, four times — the fourth inside the fix for the first three

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

**Then round 3 found a fourth instance, in the code written to fix the first three.** The
version pattern was `\b\d+(?:\.\d+)+…`, and `\b` does not fire between `v` and `0`. So a
leading `v` did not prevent a match — it *truncated* it, silently, from the second component:

| documentation change | registered as | why |
|---|---|---|
| `v0.5.0` mentioned | `ver:5.0` | the `v` shifted the match start |
| `v1.0.0` → `v2.0.0` | **no change** | both collapse to `ver:0.0` — same token |

That last row is the disease itself, one more time: a version bump written the way projects
actually write it produced two identical tokens, so the correction withdrew nothing and added
nothing. The same pattern also matched `127.0.0.1`, `179.13.100.4` and a MIME boundary
`127.0.0.1.502.21746.1321131593.786.1` — a dotted numeric run is not a version. It is now
capped at three components and absorbs the `v`; genuine four-component versions are the
knowing price of rejecting IP addresses.

Worth being precise about how this was found, because it was not found by reading the regex.
It came out of a single anomalous label — one `new` verdict on a doc-only commit, which the
arm's design says is impossible — and pulling that thread led to the regex four steps later.

## What is honest about the current numbers, and what is not

The unbiased estimates are the ones from rounds 2 and 3, because both were labelled after the
rules were frozen and drawn from cases the rules had not been tuned against:

```
shape A                      7/25 = 28%   95% CI [14%, 48%]
shape B, five repos pooled  12/37 = 32%   95% CI [20%, 49%]
```

Shape B nominally leads, but those intervals overlap almost completely — the ordering of the
two arms is **not** established by this data, and any claim that one is better needs a larger
sample than 85 cases.

One rule change is priced against round 2 and projects shape A to 38%. **That figure is a
hypothesis, not a result**, for the same reason the round-1 retention number was: it was
designed against the cases it is scored on. It gets believed or discarded by a shape-A round 3.

A second change — dropping shape-B cases whose only evidence is a version literal — removes a
class measured at zero and costs no true positive on the sample available:

```
shape B, evidence is only a version literal    0/10 =  0%   [0%, 28%]
shape B, evidence includes a real symbol      12/27 = 44%   [28%, 63%]
true positives lost                           0 of 12
```

**That 44% is a hypothesis too, for exactly the reason the last one was.** Nine of the ten
dropped cases were labelled before the rule existed, which is better than round 1 — but the rule
was designed by reading all ten, so it is still scored on its own design set. Structurally this
is the same shape as the 6/6-kept-14/14-dropped retention that looked decisive and preceded a
30% → 28% no-op. Recognising the pattern is not the same as escaping it.

What is *not* fitted here is the mechanism, which is argued from the arm's structure rather than
from the sample: shape B has no code diff, so a withdrawn version literal has nothing it can be
checked against. That argument would hold even if the ten cases had never been labelled. It is
also why the filter ships **off by default**, with a fresh batch drawn to test it.

The distinction this section keeps making — a measured number versus a number fitted to the
cases that motivated it — is the single thing the eval harness exists to preserve. Every figure
above is marked one way or the other, because the project's own history is that the fitted ones
felt the most convincing at the time.

The recall side is unmeasured throughout. Precision is cheap to estimate from a sample of
what a rule fires on; recall needs to know what it missed, which needs labelled cases the
rule rejected. That work is not done, so **no claim is made here about how much drift this
finds** — only about how much of what it flags is real.

Other limits, stated rather than buried:

- **A doc nobody fixed is not a doc that was correct.** It may be drift nobody noticed.
  Positives here are strong evidence; negatives are weak, and no published false-positive
  rate is meaningful without that caveat.
- **The false-positive denominator exists but has not been used yet.** Until now the only
  negatives were *matched* ones — the same doc/code pair one commit after the fix — and those
  cannot measure a false-positive rate at all, because in a matched negative the doc genuinely
  *is* about that code. A detector that fires on every pair scores well on them. The corpus now
  also carries pairs that never co-changed, in two tiers reported separately: random pairs
  whose paths suggest nothing (a floor), and pairs whose paths look related but have no shared
  history (much closer to what retrieval will hand the detector). No detector exists yet, so
  there is no number here — only a denominator that will support one.
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
  known live example: a reworded sentence still leaks the token `well`. A general scan for
  non-ASCII characters also turned up a corrupted entry — `from` had a stray CJK character
  glued to it, so the stoplist held the nonsense token `from给` and not `from`. Inert, as it
  happens: `from` is a Python keyword and the keyword stoplist caught it anyway, and the
  tokeniser's `[A-Za-z_][A-Za-z0-9_]*` could never emit a token containing that character. But
  it was invisible to reading and to 43 tests, and only a scan found it. Measured at 0
  occurrences across 2134 shape-A positives before being fixed; the stoplists are now
  ASCII-clean.

## Reproducibility

Every mine writes a manifest next to its output recording each repo's pinned sha, the commit
window, the full rule config, the miner's own commit, and a sha256 of the result. Its `replay`
field regenerates the label set byte-identically:

```
$ driftwood mine --out labels.jsonl --limit 4000 --pin psf/requests=dae7ef6...
$ # sha256 in the new manifest matches the old one
```

**Two of those fields are there because the mechanism was broken and said nothing.** Both are
worth reading as findings rather than features, since a provenance system that fails silently
is worse than none:

- `--pin` was declared `nargs="*"`, so argparse kept only the **last** occurrence of a repeated
  flag — and the `replay` line the tool emits is `--pin a=sha --pin b=sha …`. Following the
  documented replay command therefore pinned one repo out of five and mined the other four at a
  moving HEAD. No error, a plausible-looking corpus, a different one. A mistyped slug was
  equally quiet, because `pins.get(slug, "HEAD")` cannot distinguish a typo from "no pin asked
  for". Both now refuse loudly; `tests/test_pinning.py` asserts *both* spellings keep every pin,
  and asserts the count, because the old behaviour returned a non-empty list and would have
  passed any weaker check.
- The manifest pinned every repo sha and the entire rule config, which felt complete. But the
  rules live in code, and correcting the version pattern above changed which tokens get
  extracted. **Every manifest written before that fix promises a regeneration the current code
  cannot deliver, and nothing in the file said so.** A config dict is not a version; the
  manifest now records the miner's commit and whether `src/` was dirty.

For a project about documentation that has quietly stopped being true, having it happen to the
reproducibility documentation is the most on-the-nose thing in the repo. It is the second
instance: the `mine` usage example below destroyed the one irreplaceable label file first.

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
- **The same signal can be evidence in one arm and noise in the other.** Version literals were
  added because three false negatives traced to them, and on shape A they earn their keep: there
  the literal must appear in the *code* diff too, which is how a `python_requires` change gets
  caught. On shape B there is no code diff, so a withdrawn version literal cannot be checked
  against anything — and what actually withdraws one is a doc rewriting its own example output
  (a `User-Agent` header, a console transcript), or listing other projects' versions. Even the
  genuine cases (`supports Python 3.3–3.5`) came back `unclear` every time, because a doc-only
  commit dropping a support line does not show whether support ended. Same token, opposite
  value, and the arm is what decides which. A filter that reads "drop version-only evidence"
  would be wrong applied globally; scoping it per arm is the whole content of the rule.
- **Never-co-changed negatives come in two tiers, not one**, because a uniformly random
  doc/code pair is trivially unrelated and a specificity number built only from those would
  price the problem far below reality — in production the detector sees pairs *retrieval*
  thought were plausible. Retrieval is stage 2, so the real distribution cannot be sampled
  yet; the harder tier samples pairs whose paths look related but share no history, as a
  stand-in. Two things surfaced from printing fourteen sampled pairs and reading them, neither
  of which any test written from the design would have caught: `docs/api.rst` against
  `src/requests/api.py` was being filed as a *random* pair (`api` is stoplisted, so both paths
  reduced to no tokens), which inverts the meaning of the arm cited to show the detector does
  not fire on nonsense; and `tests/certs/README.md` was being sampled as documentation, 74 of
  739 negatives, including every single hard negative for one repo. The harder tier is also
  **scarce exactly where a repo is small and well maintained** — asking 100 per repo yields 100
  from fastapi and pydantic but 1 from `requests`, because in a mature small repo nearly every
  plausible-looking pair *has* co-changed. So it is reported per repo and never pooled; pooling
  would rebuild round 1's single-repo confound in a new place.

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
uv run driftwood mine --repos psf/requests pallets/flask --limit 4000 --out data/mine.jsonl
uv run driftwood stats --labels data/mine.jsonl
uv run driftwood sample --labels data/mine.jsonl --shape A -n 25 --out review/batch.md
uv run driftwood score review/batch.md --labels data/mine.jsonl
uv run pytest
```

Note the explicit `--out`. `mine` refuses to overwrite an existing file without `--force`,
because the flag's default points at `data/labels.jsonl` — the one label set here that
predates manifests and cannot be regenerated. An earlier version of the example above
omitted `--out`, and duly destroyed it. Recovered from git; the guard is the actual fix.

`sample` writes a review sheet a human fills in; `score` reads the verdicts back and reports
precision per shape and per basis with intervals. `retention` checks how a rebuilt label set
treats already-judged cases, which is valid for subtractive rule changes only.

## Licence

MIT.
