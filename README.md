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

## Stage 2: retrieval, and what a shuffled ranking is for

The mined pairs are relevance judgements: a doc and a code file that co-changed while sharing an
identifier is a human-confirmed statement that the doc makes a claim about that code. So the
question "given a documentation file, can we find the code it is about?" has 1025 judged queries
without anybody labelling anything new. That is the retrieval step the pipeline needs — an agent
holding a doc claim has to fetch the code to check it against.

Three arms, none of them a model. `path` matches filename tokens. `lexical` ranks by IDF-weighted
identifier overlap. `shuffle` ranks at random, forty times, and is the reason the other two are
readable at all:

```
repo                ranker            pool~    n    R@1    R@5   R@10    MRR
encode/httpx        shuffle (floor)      24  148   0.04   0.20   0.41   0.25
encode/httpx        path                 24  148   0.03   0.34   0.58   0.27
encode/httpx        lexical-ablated      24  148   0.26   0.59   0.82   0.67
pallets/flask       shuffle (floor)      35  396   0.04   0.20   0.36   0.19
pallets/flask       path                 35  396   0.09   0.14   0.34   0.19
pallets/flask       lexical-ablated      35  396   0.36   0.66   0.82   0.66
pydantic/pydantic   shuffle (floor)     101  346   0.01   0.05   0.11   0.10
pydantic/pydantic   path                101  346   0.13   0.18   0.25   0.31
pydantic/pydantic   lexical-ablated     101  346   0.18   0.40   0.57   0.47
fastapi/fastapi     shuffle (floor)     685   82   0.00   0.01   0.01   0.02
fastapi/fastapi     path                685   82   0.09   0.25   0.28   0.21
fastapi/fastapi     lexical-ablated     685   82   0.28   0.49   0.61   0.45
```

**A shuffled ranking scores recall@10 = 0.41 on `encode/httpx`.** Its candidate pool is 24 files
and a query has several right answers, so drawing ten at random finds one about half the time.
The first version of the lexical ranker scored 0.25 there — *below chance* — and without the
shuffle arm that would have been written down as "25% recall@10", a number with a percent sign
on it and nothing wrong with it on its face. The floor is per repo and computed on each query's
own pool, because a 24-file haystack and a 685-file haystack are not the same measurement and a
mean across them describes the corpus rather than the ranker.

The trial spread does the second job. Forty shuffles on flask give recall@10 between 0.32 and
0.40; that range is the noise floor of the metric on this data, so a gain smaller than it has
not been shown to be a gain. It is the same discipline as putting a Wilson interval on a
precision figure instead of quoting the point estimate.

**`path` is not shown to work on two of five repos.** On flask it lands at 0.34 against a 0.36
floor and its MRR exactly equals the floor's; on `psf/requests` it sits inside the noise range.
It earns its keep on fastapi and pydantic, whose docs mirror their module layout. One baseline,
two opposite verdicts, and only the per-repo breakdown shows it.

### The number that was too good, and the ablation that priced it

`lexical` reaching recall@10 = 0.85 should not be believed on sight, because the ground truth
was **mined using identifier overlap** and this ranker scores by identifier overlap. The labels
were selected for the signal being tested. That is structurally the same error as quoting a
retention figure computed on the cases its filter was designed against, which this project has
now done three times.

It is also, unusually, testable: every record names the identifiers the miner accepted as its
reason, so the eval runs a fourth arm with exactly those tokens struck out of the query — the
same ranker, the same tree, the same IDF, a strictly harder task.

```
                    lexical   ablated
encode/httpx  R@10     0.86      0.82
pallets/flask R@10     0.85      0.82
psf/requests  R@10     0.81      0.76
fastapi       R@10     0.63      0.61
```

Two to five points. The circularity is real and small, and **this is the first time in the
project that a suspected fitted number came back mostly clean once it was actually priced.**
Every figure quoted above is the ablated one.

What the ablation does *not* cover, stated plainly: it removes the specific tokens the miner
matched on, not the selection effect. Shape A picks doc/code pairs that were lexically related
enough to share a changed identifier, so the whole *population* of queries may be easier than a
random doc/code relation is. Settling that needs relevance judgements produced without lexical
overlap — hand-labelled doc→code pairs — and that has not been done, so no claim is made here
about performance on docs the miner would never have paired.

The strongest evidence is fastapi's, and for a reason worth noticing: its floor is 0.01, so
recall@10 = 0.61 on a 685-file pool is a 60x lift, where httpx's headline 0.82 is a 2x lift over
a floor of 0.41. The largest haystack produces the least impressive number and the most
convincing one.

### Two design decisions that cost more than they look

**Each query is scored on the tree its judgement was made at**, not on one recent sha per repo.
The recent-sha version was written first and was cheaper. It cost 64% of flask's judged pairs and
30 of requests' 36, because both projects moved to a `src/` layout inside the mining window and
`requests/adapters.py` is not a path that exists any more. That loss is not attrition — it
deletes exactly the core library modules and keeps `setup.py` and `docs/conf.py`, leaving a
sample biased toward the odd pairs while still reporting a confident number. Scoring at the
judged sha loses nothing: `lost = 0` for all five repos, and the corpus went from 127 queries
to 1025.

Following the renames instead was tried and rejected, and the reason is a good one. `git diff -M`
between the two trees returns three renames for `psf/requests`, of which two are wrong:

```
R100  requests/packages/urllib3/contrib/__init__.py  ->  tests/testserver/__init__.py
R100  docs/dev/internals.rst                         ->  src/requests/py.typed
```

Both pairs are near-empty files, so git's similarity scoring rates them identical. It never found
the real module moves. A remap built from that would have scored a documentation file against
`py.typed`, at 100% confidence, silently, forever.

**`path`'s first version was confidently wrong rather than weak**, and the difference matters.
It matched any shared path token, directory names included. Every flask doc lives under `docs/`,
most flask doc paths reduce to that one token once pieces under four characters are dropped
(`docs/api.rst` → `{docs}`), and `docs/conf.py` is the shortest pool path sharing it — so the
length normaliser gave `docs/conf.py` rank 1 for **388 of 396 flask queries**. A shared token now
has to involve at least one of the two filenames, on the general ground that a directory both
files merely sit in says nothing about *which* file. Fixing it moved fastapi's MRR from 0.15 to
0.21 and left flask at the floor — so flask's verdict survived the correction, but a broken
baseline understates the bar every later model has to clear, which is the entire reason for
measuring a baseline.

## Stage 2b: the embedding arm lost to the free baseline, five repos out of five

The result first, because it is the interesting part. `dense-ablated` against
`lexical-ablated` — the two comparable rows — on `BAAI/bge-small-en-v1.5`, chunked 1600/200,
max-pooled over chunk pairs:

| repo | pool~ | n | dense R@10 | lexical R@10 | dense MRR | lexical MRR |
|---|---|---|---|---|---|---|
| encode/httpx | 24 | 148 | 0.77 | **0.82** | 0.50 | **0.67** |
| fastapi/fastapi | 685 | 82 | 0.52 | **0.61** | 0.39 | **0.45** |
| pallets/flask | 35 | 396 | 0.76 | **0.82** | 0.56 | **0.66** |
| psf/requests | 23 | 53 | 0.62 | **0.76** | 0.30 | **0.37** |
| pydantic/pydantic | 101 | 346 | 0.35 | **0.57** | 0.30 | **0.47** |

The dense arm works — fastapi's 0.52 R@10 on a 685-file pool against a shuffled floor of 0.01 is
real retrieval, not noise. It simply loses to IDF-weighted token overlap with no dependencies, on
every repo, on both metrics.

**Two-thirds of that is not individually readable, and saying so is the point.** Compared against
each repo's own noise range, only pydantic (0.22 gap vs 0.06 spread) and fastapi (0.09 vs 0.04)
show a loss larger than the metric's noise on this dataset; httpx, flask and requests are all
inside it. What carries the conclusion is not any single repo but that the direction is consistent
**five for five**, which a sign test puts at p ≈ 0.03. Three of these repos, reported alone, would
be "not shown".

**The comparison that was pre-registered and then not made.** pydantic's dense arm falls 0.47 →
0.35 R@10 under ablation where lexical only falls 0.59 → 0.57, which looks like the dense arm
leaning far harder on the miner's own evidence tokens. That inference is unavailable, and it was
written down as unavailable *before* the run: the dense ablation redacts words from text, the
lexical one subtracts tokens from a set, and deleting `HTTPTransport` perturbs the sentence around
it. A harsher intervention producing a larger drop is not evidence of more circularity.

### Worse overall is not the same as useless, so that was measured too

A ranker can lose on average and still be right about cases the winner misses — that is the whole
premise of hybrid retrieval. `scripts/complementarity.py` tests it as hit@10 per query, both arms
ablated:

```
repo                    n  both lex only dense only neither  lex@10  union  lex@20 union wins
encode/httpx          148   133        7          1       7    0.95   0.95    0.99         no
fastapi/fastapi        82    49       10          6      17    0.72   0.79    0.80         no
pallets/flask         396   332       24         10      30    0.90   0.92    0.96         no
psf/requests           53    35        7          2       9    0.79   0.83    0.96         no
pydantic/pydantic     346   179       82         14      71    0.75   0.79    0.85         no
```

Dense does find queries lexical misses — 1 to 14 per repo, and a union of the two top-10s lifts
hit@10 by 1 to 7 points. **That lift is an artefact of the budget, not a property of the ranker,
and the last column is the control that shows it.** A union of two top-10s inspects twenty files,
so the honest comparison is not lexical@10 but *lexical@20* — the other thing the same budget
buys. Lexical@20 wins on all five repos, `psf/requests` by 0.96 to 0.83. More lexical results are
worth more than dense results, so the dense arm does not earn its half of the candidate budget
either.

Without that control every second ranker that is not actively harmful shows a lift, and the lift
is the budget. It is the same failure the shuffled floor exists to catch, one level up: a number
that goes up for a reason that has nothing to do with the thing being tested.

### What this does and does not license saying

It does **not** show that embeddings lose at doc→code retrieval. The ground truth is shape-A
mined pairs, and shape A only ever proposes a doc and a code file **that already share an
identifier** — so the corpus is selected for precisely the signal the lexical ranker consumes.
The dense arm is being asked to win on the other arm's home ground. The already-documented weak
ablation is the same limit seen from the other side: striking evidence tokens bounds one
circularity channel and cannot touch the selection effect.

So the finding is narrow and real: **on identifier-overlap-selected ground truth, a 384-dim
general-purpose text encoder is not worth its dependencies.** Testing the embedding hypothesis
needs ground truth this mining rule did not select — a ground-truth problem, not a modelling one,
and the reason stage 2c sits ahead of `bge-m3` in the roadmap. Buying a model 17x the size to win
on a corpus built around the competitor's strength would answer a question nobody asked.

Stage 2c has since built that ground truth and scored it. **It half-confirms this section and
half-contradicts it**, which is written up below rather than folded into the numbers above.

### The design, and the measurement that set it before any model was installed

Everything below was settled before the numbers above existed, and each choice would have gone
the other way by default.

**The default design does not survive the corpus.** Embed each file, embed the doc, take a
cosine — that requires both to fit in the encoder's window, and neither does. Code files have a
median of 7.9k characters and a 90th percentile of 47k; 17% exceed roughly 8k tokens and the
largest is 396k characters. Docs are no smaller: median 11.6k characters, with 94% over 2000. So
something has to give, and the two candidates are truncate or chunk.

**Truncation was priced with the free ranker, before committing to either.** `Lexical` can be
handed a shortened file just as easily as a model can, so the cost of a truncating design was
measurable for the price of two extra eval runs:

```
MRR, ablated       full   8000 chars   2000 chars (~512 tokens)
encode/httpx       0.67         0.51         0.45
pallets/flask      0.66         0.52         0.36
pydantic/pydantic  0.47         0.38         0.30
psf/requests       0.37         0.25         0.20
fastapi/fastapi    0.45         0.33         0.34
```

**A third to a half of the retrieval signal is not in the first 512 tokens of a code file.** A
truncating dense arm would therefore start handicapped below the free baseline, and would lose
for a reason that has nothing to do with embeddings — the experiment would run, produce a number,
and answer a different question than the one asked. So both sides are chunked at 1600 characters
with 200 of overlap, and nothing is dropped. The overlap is what keeps a definition that lands on
a window boundary intact *somewhere*, a loss that is otherwise invisible in the score.

That measurement is now a regression test rather than a paragraph:
`test_a_match_at_the_end_of_a_long_file_still_ranks_first` fails if someone later optimises this
by embedding only the head.

**Scoring is max over (doc chunk, code chunk) pairs — two maxes, no mean.** Justified by what a
positive actually *is* here: the doc makes one claim, about one function, in one file. Mean-pooling
either side averages that against every unrelated paragraph in a 12k-character document and every
unrelated method in a 47k-character module, diluting the exact localised match the label is about.
This is late interaction at chunk granularity rather than token granularity — ColBERT's MaxSim
reasoning, done coarsely because the vectors have to fit in memory on a laptop. The cost is
recorded: a file that merely *mentions* the right symbol once scores as highly as one built around
it. Term frequency has the same weakness in `Lexical`, and it is written down in both places.

**The cache is keyed on content, and stamped.** Queries are scored at the tree their judgement was
made at, which means 629 distinct trees — but only 8148 unique code blobs behind them, because most
files are byte-identical from one sha to the next. A path-keyed cache would miss nearly every one of
those hits and turn minutes into hours. The subtler half is the stamp: the model id and the chunking
parameters are folded into the key *and* written into the file, and a mismatch refuses to load.
Changing the chunk size changes no shape, no column and no schema, so a cache that ignored it would
keep serving vectors built under the old windows and the run would look entirely clean. Cosines
between two different encodings are finite, plausible and meaningless, and nothing downstream can
detect them — refusing is the only safe behaviour.

**The dense ablation redacts text; the lexical one subtracts tokens. These are not the same
operation.** `Lexical` can remove the mined evidence tokens exactly, because it consumes tokens.
A model consumes text, so the only available analogue is deleting the words — which perturbs the
sentence around them too. The dense ablation is therefore *strictly harsher* than the lexical one,
and **a wider dense gap is not by itself evidence of more circularity.** This is written here, in
the module docstring, and in the eval's own output, because the two gaps will be printed in
adjacent rows and that invites exactly the wrong inference.

**The bar was `lexical-ablated` per repo, not the shuffled floor**, and it was set in writing
before the run. Beating a shuffled ranking is not an achievement — `path` failed to do it on two
repos, but a free tokeniser clears it comfortably. Naming fastapi's 0.61 R@10 in advance is what
makes the result above a finding rather than a disappointment: had the bar been the floor, the
dense arm's 0.52 against 0.01 would have been written up as a success.

The whole arm is an optional extra (`uv sync --extra embed`), so stages 1 and 2 stay regenerable
in CI years from now without resolving an inference stack.

## Stage 2c: the ground truth the 5/5 result needs, and the plan it falsified

The 2b loss is confounded with how the corpus was built. Shape A proposes a doc/code pair only
when the two already share an identifier, so the ground truth is selected for exactly the signal
`Lexical` scores with, and "embeddings lose at doc→code retrieval" is not a claim that measurement
supports. Stage 2c builds judgements that rule never touched: **documents read by a person, with
the repository's whole code pool as the candidate list.**

18 documents were sampled and labelled by hand. **The result splits: the MRR ordering survives,
the recall ordering reverses, and neither is readable at this sample size.** Details below the
design, because the design is what makes the numbers mean anything.

**The stage as first specified does not exist, and the check that showed it took four minutes.**
The roadmap line above used to read "hand-labelled pairs sharing no identifier." Across the 2135
pairs already judged, that population is **2 pairs** — 0 of 343 in httpx, 0 of 180 in fastapi,
0 of 727 in flask, 0 of 75 in requests, 2 of 810 in pydantic — with a median pair sharing 18 to
65 identifiers. At file granularity a 10k-character document and a 5k-character module share
tokens regardless of what either is about. So overlap is not a usable partition here, and the
answerable question is not *pairs with no overlap* but **pairs no overlap rule selected**.

### Who proposes the candidates decides the answer

Two cheaper designs were rejected, and the reasons are the design:

- **Label a ranker's top 10.** This measures whether that ranker's suggestions are good. A pair
  the dense arm finds and the lexical arm misses can never enter the corpus, so whichever ranker
  generates the candidates wins the evaluation it is then graded by.
- **Label random pairs.** Unbiased and unaffordable: pools run 22 to 685 files with a handful
  relevant, a positive rate near 1%, so thirty judgements would return roughly zero positives.

The unit of judgement is therefore the **document**, and the candidate set is the repository tree
— which has no opinion. Every pair either ranker could return is reachable, including pairs
neither one ranks.

### Four decisions in the sheet itself

18 documents, six each from httpx, requests and flask, sampled uniformly at a recorded seed from
one pinned tree per repo.

- **`NONE` is an answer, and it is distinct from an unmarked case.** A doc that makes no claim
  about any specific module is a real judgement. Both have zero ticked files, and scoring an
  unmarked case as "about nothing" would add a query every ranker necessarily loses — dragging
  recall down by an amount set by what the sample happened to draw, and reporting it as a fact
  about the rankers.
- **A freehand `EXTRA:` line**, so the checklist cannot cap the answer at what was listed.
- **The sample is a shuffled prefix, not `random.sample`.** Equally uniform, but nested: at the
  same seed, nine documents per repo contains every one that six chose. Sheets get extended when
  `NONE` turns out common, and a redraw would strand judgements already made. What that does not
  license is drawing twice and reporting the nicer answer — extending is only sound because every
  drawn case is labelled and counted, so the stopping rule is a query count fixed in advance.
- **Both the documents and the entire code pool are written to disk.** The clones are bare, so
  there is no working tree to open, and "does this document make a claim about this module" is
  usually not answerable from the document alone.

### No ablation here, and that is correct rather than missing

The ablation arm exists to bound circularity injected by the mining rule — it strikes the tokens
that caused a pair to be proposed. These pairs were proposed by a person reading prose, so there
is no such channel and nothing to strike. Every query carries empty evidence, pinned by a test,
and the ablated rows are dropped from the output rather than printed as byte-identical copies of
their unablated twins. A duplicated row in a results table reads as a measurement that was made.
**The 2c rows are compared against the *ablated* rows of the 2b table.**

### The result: 18 documents, 14 scoreable queries, a split verdict

All 18 cases were answered. **Four were marked `NONE`** — requests' `install.rst`,
`contributing.rst` and `community/recommended.rst`, and flask's `patterns/mongoengine.rst`:
installation guides, contribution process, and a third-party integration recipe, all of which make
claims about the world outside the tree rather than about a module in it. That is 22% of the
sample, which is the whole argument for `NONE` being a first-class answer — scored as queries they
would have pulled every ranker's recall down by a quantity set by the draw.

| repo | n | ranker | R@1 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|---|
| encode/httpx | 6 | shuffle (floor) | 0.05 | 0.22 | 0.46 | 0.38 |
| | | *noise range* | *0.00–0.21* | *0.09–0.40* | *0.28–0.63* | *0.18–0.57* |
| | | path | 0.00 | 0.53 | 0.70 | 0.27 |
| | | lexical | 0.15 | **0.70** | 0.94 | **0.81** |
| | | dense | 0.15 | 0.64 | **0.96** | 0.76 |
| pallets/flask | 5 | shuffle (floor) | 0.03 | 0.14 | 0.28 | 0.31 |
| | | *noise range* | *0.00–0.15* | *0.03–0.35* | *0.13–0.54* | *0.12–0.60* |
| | | path | 0.08 | 0.08 | 0.08 | 0.43 |
| | | lexical | **0.17** | **0.49** | 0.68 | **0.82** |
| | | dense | 0.12 | 0.44 | **0.78** | 0.73 |
| psf/requests | 3 | shuffle (floor) | 0.06 | 0.24 | 0.47 | 0.39 |
| | | *noise range* | *0.00–0.17* | *0.00–0.58* | *0.17–0.83* | *0.10–0.72* |
| | | path | 0.00 | 0.08 | 0.42 | 0.17 |
| | | lexical | **0.33** | **0.83** | **0.92** | **1.00** |
| | | dense | 0.08 | 0.50 | 0.83 | 0.49 |

**On MRR the 2b direction survives: lexical wins 3 of 3.** Where the first correct answer lands is
the metric the pipeline actually spends money on, and on ground truth no overlap rule selected,
IDF-weighted token overlap still puts it earlier than a 384-dim encoder. The 5/5 result was
therefore not purely a selection artefact — which is the one thing 2c was built to find out.

**On recall@10 it reverses: dense wins 2 of 3** (httpx 0.96 vs 0.94, flask 0.78 vs 0.68), having
lost 3 of 3 on these same repos in 2b. Dense *finds* relevant files that lexical does not and
*orders* them worse — the same find-but-don't-rank pattern `scripts/complementarity.py` measured
independently, arrived at here from a different corpus and a different metric.

**Nothing in the table is individually readable, and the per-query view says why.** Every
dense-vs-lexical gap sits inside its repo's noise range; the widest, requests' 0.51 MRR, is inside
a 0.62-wide range. Decomposed to the 14 queries, **8 are ties at MRR 1.00** — both rankers put a
relevant file first, so the task as sampled is easy and the entire difference lives in 6 documents.
Paired per query: lexical takes MRR 5–1, dense takes R@10 5–2. Sign tests give p ≈ 0.11 and
p ≈ 0.23; the repo-level 3/3 on MRR gives p ≈ 0.125. **This is a direction, not a result.** And
requests' MRR gap is one document — `community/faq.rst`, where lexical scores 1.00 and dense 0.12.
One doc out of three carrying a repo's headline number is what n=3 looks like from the inside.

**The magnitudes are not comparable across the two corpora, only the orderings.** Lexical's MRR
here (0.81 / 0.82 / 1.00) towers over its ablated MRR on the mined corpus (0.67 / 0.66 / 0.37),
and almost none of that is retrieval getting better:

| repo | 2c relevant/query | mined relevant/query | 2c pool~ | mined pool~ |
|---|---|---|---|---|
| encode/httpx | 4.00 | 2.32 | 23 | 24 |
| pallets/flask | 4.40 | 1.84 | 35 | 35 |
| psf/requests | 3.33 | 1.42 | 22 | 23 |

A person reading a document marks about twice as many files as the miner proposes for it, out of an
identically-sized pool. Twice as many correct answers makes hitting one at rank 1 roughly twice as
easy, so MRR rises mechanically; recall@k, needing to cover a doubled denominator, gets *harder*.
Dense holding roughly its 2b recall against twice the denominator is the quieter half of the
reversal above. The two corpora differ in ground-truth provenance and in relevant-set size — not
in pool size, which is the confound that would have been fatal and is the one that is absent.

`path` collapses on flask: R@10 of 0.08 against a floor of 0.28, meaningfully *below chance*. Its
whole signal is filename-to-filename token overlap, and flask's docs are named for tasks
(`errorhandling`, `templating`) while its modules are named for structures (`app.py`, `blueprints.py`).
A bare 0.08 reads as a weak baseline; only the floor shows it is an actively misleading one.

### The limitation, stated because it is not recoverable

**pydantic (267 code files) and fastapi (685) are excluded** — a checklist that long is not a
usable instrument. Those are the only two repos where the dense loss was individually readable
against its noise range. 2c could therefore test whether the ordering survives ground truth the
mining rule did not select, and it did; it **cannot confirm or overturn the readable half of the
5/5 result**, and the split verdict above must not be read as doing either. The three repos 2c
covers are exactly the three that 2b already reported as "not shown" individually.

With three to six queries per repo the noise ranges came out 0.35 to 0.62 wide, and that width is
the finding rather than something to average away. The honest summary of the whole two-stage
exercise is that **the direction has now been observed on two corpora selected two incompatible
ways, and has not once been observed at a magnitude larger than its own noise.** Fixing that needs
more labelled documents, not a better model — which is what makes 2d (a reranker over `lexical`'s
top 20, scored on both corpora) the next thing worth building and `bge-m3` still not worth buying.

Two silent defects in already-shipped code surfaced the first time the new command printed a
table, both in the results footer: it named the module's default trial count rather than the
run's, so a low-trial run claimed forty trials and understated its own noise range; and it
explained the `lexical-ablated` row whether or not that row existed, implying numbers had been
bounded for circularity when they had not. Both are now parameterised, gated, and tested.

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

## Stage 3: the judge, and the free half of it that runs first

The question the project is named after: shown a document and some code *at one commit*, does
the document say something false about the code? 125 hand-written verdicts already exist across
seven review sheets, so this stage is scored rather than demonstrated.

Nothing has called a model yet, and that is the point of the ordering. Everything below runs with
no key, no network and no `anthropic` installed, because a model's number is uninterpretable
without it.

### The five labels are not the target, and using them would have been silent

The sheets ask for one of `drift`, `new`, `cosmetic`, `unrelated` or `unclear`. Three of those
five are defined by the *correcting* commit, not by the state being judged — a judge that sees
only the parent cannot separate "cosmetic" from "unrelated" even in principle, because both mean
"nothing was false". So the space collapses to one binary: was this documentation false about the
code at this commit?

| label | n | prospective target |
|---|---|---|
| `drift` | 30 | **false at parent** |
| `new` | 10 | not false |
| `cosmetic` | 61 | not false |
| `unrelated` | 4 | not false |
| `unclear` | 20 | held out — abstention calibration, not a class |

`new` is the trap, and I had it backwards. The legend reads "documenting something that did not
exist yet", which sounds like a doc that ran ahead of its code — a positive. Reading two actual
cases first: they are "Added support for signals", the feature and its documentation landing in
one commit. At the parent neither existed, so nothing was false, and the miner proposing the pair
is itself the false positive. Ten of 105 cases turn on that one constant, and a flipped label
there would have penalised a judge for being right.

`unclear` is held out rather than scored. Julie could not decide *with both diffs in front of
her*; a judge working from strictly less has no defensible answer either. Those 20 become the
calibration set for abstention instead.

### Accuracy is near-useless here, so the floors are the result

At a 28.6% positive rate, answering "not false" every single time scores **71.4% accuracy**. Any
accuracy in the sixties or seventies is consistent with a judge that has learned nothing. So the
primary metric is F1 on the positive class — where that same constant scores 0.00.

But F1 has its own floor, and it is not zero. Answering "drift" every time scores **F1 0.44**.
Both constants are reported on every table, because they catch opposite failures.

Retrieved arm, k=5, 105 scoreable cases:

| judge | F1 | precision | recall | accuracy |
|---|---|---|---|---|
| `always-not-false` — the majority floor | 0.00 | 0.00 | 0.00 | **71.4%** |
| `always-false` — the F1 floor | **0.44** | 0.29 | 1.00 | 28.6% |
| `lexical-absence(>=1)` | 0.45 | 0.30 | 0.97 | 33.3% |
| `lexical-absence(>=3)` | 0.45 | 0.29 | 0.93 | 34.3% |
| `lexical-absence(>=6)` | 0.42 | 0.29 | 0.80 | 38.1% |
| *chance, 200 trials, p5–p95* | *0.18–0.39* | *0.19–0.40* | | *52–67%* |

`lexical-absence` flags a document that marks up an identifier — backticked or fenced, never bare
prose — which appears in none of the code files shown. It is the thing you would write in an
afternoon without an LLM, and it is the comparison that actually matters. At its best threshold
it beats a stuck switch by **one point of F1**, on a chance range 0.21 wide, and tightening the
threshold makes it worse. Its confusion matrix says why: it answers "false" on 29 of 30 drift
cases *and* 58 of 61 cosmetic ones. It is a constant with extra steps.

Two claims this pre-empts, both of which I would otherwise have been able to make:

- "Our judge beats a non-LLM baseline." The non-LLM baseline is not a baseline.
- "Our judge scores F1 0.40." That is worse than a stuck switch, and against the accuracy floor
  alone it would have read as a respectable result.

### The retrieval ceiling, measured rather than assumed

80 of the 125 cases are doc-only commits with **no code side at all**, so the code has to be
retrieved and stage 2 is load-bearing here rather than an add-on. The other 45 carry the file the
commit actually touched, which makes the retrieval ceiling a free measurement:

| | hit@1 | hit@3 | hit@5 | hit@10 | hit@20 |
|---|---|---|---|---|---|
| commit's own code file, `lexical` rank | 20% | 38% | **60%** | 87% | 98% |

Median rank 5; the file is present in the pool all 45 times. So the planned k=3 would have capped
the arm near 38% on shape A before a judge read a word, and an oracle-vs-retrieved gap would
mostly have been that cap. k=5 buys 22 points for two more files; k=10 buys 27 more but shows
seven distractors, and this arm's job is an end-to-end number rather than the best number.

Two arms, fixed before any model ran. **Oracle** (45 cases) hands over the commit's own file and
isolates judging skill from retrieval quality — not a product configuration, since in production
nobody hands you the file. **Retrieved** (all 125) is the only arm that covers shape B and the
only end-to-end number. A third diff-shown arm exists as a diagnostic ceiling and must never be
reported as product performance.

### Two fields on every record are the answer

The corpus was mined *from* the correcting commit, so the record describes that commit more than
it describes the state being judged. Two fields give it away outright: `subject` is the fix's
commit message, and this corpus contains subjects like "Fix the incorrect timeout default
documented in the config guide". `shared_identifiers` is the doc diff's removed-only side — the
identifiers the fix *deleted* from the prose, which is a pointer at the drifted sentence and is
the miner's own selection evidence.

Both were sitting on the dataclass the context builder reads. They are named in a
`LEAKING_FIELDS` constant, `render` is the single path from a case to a model, and six tests
assert on the rendered *string* rather than on the context object — a field can be excluded from
the object and still be formatted into the prompt. Leakage of this kind does not fail a test
suite. It produces an excellent F1.

### Three things the harness refuses to do quietly

- **An unparsed reply is an abstention, not a negative.** Defaulting a malformed reply to "not
  false" would earn free credit on 75 of 105 cases. They are counted, warned about, and written
  to disk *before* parsing so they can be read by hand.
- **Abstentions are reported twice and folded into neither.** One accuracy column counts an
  abstention wrong; the other divides by answered cases only. A judge can reach perfect precision
  by abstaining on everything, so precision quoted without an abstention rate is not a result.
- **Abstention is scored by lift, not rate.** The test is whether a judge abstains
  *differentially* on the 20 `unclear` cases versus the 105 scoreable ones. A 90% abstention rate
  everywhere carries no information, however high it is.

And one it refuses to do at all: the response cache is keyed on a hash of the rendered context,
the prompt and the model, not on the case id. Temperature 0 is not determinism, so the cache is
what makes a re-run reproducible — but only if editing the prompt invalidates it. Keyed on the
case id, a prompt change would have appeared to have no effect.

### The corpus was not reproducible from this repository

Found by running the suite in a detached `git worktree` at HEAD instead of in the working tree.
Four failures, all of them the tests that pin the real corpus.

**79 of the 125 hand-written verdicts join to records that exist only in `data/labels-v3.jsonl`
and `data/labels-v10.jsonl`, and `data/labels-v*.jsonl` is gitignored as derived data.** A clean
checkout rebuilt 46 cases, reported 7 positives instead of 30, computed a different majority-class
floor, and raised nothing — one warning, and then every number correct against a corpus two thirds
smaller than the one described three sections above.

The tests that pin 125 / 105 / 30 had been passing all along. They were reading this machine's
`data/` directory, which has every mined version. **A test that reads the repository's own data
directory verifies the developer's disk, not the repository.**

The gitignore already contained the argument and it had not been applied. `data/labels.jsonl` is
tracked because "the hand-labelled verdicts in `review/` join to it by `example_id`. Losing it
would make the ground-truth sheets unattributable." That is true of v3 and v10 for 79 cases.

The fix is `data/judged-records.jsonl`: the 125 records the hand labels actually join to, written
by `driftwood judge-freeze` and tracked. Derived data committed anyway, on the same grounds v1 is —
regenerable *in principle* is not the same as present. Three details are deliberate:

- **Frozen is the preferred source even where the live versions survive**, so `resolved_from` is
  identical on every machine. Otherwise the provenance block in the results JSON differs by
  checkout, and two people comparing results are comparing their checkouts.
- **The live versions are still read**, and one disagreeing with a frozen record is reported: that
  is what a stale freeze looks like.
- **Each record keeps a `frozen_from`** naming the mining run that produced it. That is the field
  needed to explain a case, and it is exactly what a naive concatenation drops.

## Roadmap

| stage | state |
|---|---|
| 1 · Ground-truth miner + eval harness | **built, measured** |
| 2 · Retrieval — free baselines against a shuffled floor | **built, measured** |
| 2b · Retrieval — embeddings, chunked and cached | **built, measured, lost 5/5** |
| 2c · Hand-labelled docs, candidates = the whole tree — the ground truth 2b needs | **built, 18 docs labelled, split verdict** |
| 2d · Cross-encoder reranker over `lexical`'s top 20, scored on both corpora | designed |
| 3 · The judge — does a document make a false claim, at one commit | **harness built, floors run, model arm next** |
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
uv run driftwood retrieve-eval data/mine.jsonl --out data/scores/retrieval.json
uv run pytest
```

Note the explicit `--out`. `mine` refuses to overwrite an existing file without `--force`,
because the flag's default points at `data/labels.jsonl` — the one label set here that
predates manifests and cannot be regenerated. An earlier version of the example above
omitted `--out`, and duly destroyed it. Recovered from git; the guard is the actual fix.

`sample` writes a review sheet a human fills in; `score` reads the verdicts back and reports
precision per shape and per basis with intervals. `retention` checks how a rebuilt label set
treats already-judged cases, which is valid for subtractive rule changes only.

`retrieve-eval` needs the clones `mine` left in `.cache/clones`, since it scores each query on
the tree that query's judgement was made at. It prints the dataset — pool sizes, per-repo
query concentration, lost positives — before any metric, on the grounds that a recall figure
without its pool size is not checkable by the person reading it.

The dense arm is off unless a model is named, so everything above runs with no inference stack
installed:

```
uv sync --extra embed
uv run driftwood retrieve-eval data/mine.jsonl --embed-model --out data/scores/dense.json
uv run python scripts/complementarity.py data/mine.jsonl
```

`--embed-model` bare means `BAAI/bge-small-en-v1.5`; naming a model instead swaps it, and
`BAAI/bge-m3` is a one-flag upgrade at roughly 17x the compute — an overnight run rather than a
different design. Add `--embed-device mps` on Apple silicon.

Stage 3 likewise runs free by default. `judge-cases` prints the class balance and the floors and
touches neither a clone nor a model; `judge-eval` with no flags runs the three judges that need no
key, which is the half of the result that makes the other half readable:

```
uv run driftwood judge-cases
uv run driftwood judge-eval --arms oracle retrieved --out data/scores/judge-floors.json
uv run driftwood judge-eval --dump-prompt
```

`judge-cases` warns if any case resolves only from a gitignored label version, which means the
tracked join table is stale and a clean checkout would silently score a smaller corpus. Rewrite it
from a machine that still holds the mined versions:

```
uv run driftwood judge-freeze
```

`--dump-prompt` prints one rendered prompt so a person can check by eye that no diff, no commit
subject and no mining evidence reached it. The model arm is an extra and needs a key:

```
uv sync --extra judge
uv run driftwood judge-eval --judges always-not-false always-false lexical-absence model
```

Replies are cached under `.cache/judgements`, keyed by content rather than by case id, so
re-running is free and editing the prompt is not.

**Caching is the default and opting out is the flag**, which is the way round that matters here.
The corpus is 8148 unique code blobs behind 629 trees, so a forgotten cache produces an identical
table an hour later — a mistake with no symptom except the wait. The path is *derived* from the
model and the chunking rather than fixed, so switching either one writes a second file instead of
colliding with the first. The stamp check would catch a collision and refuse, which is safe but
would make every switch an error cleared by deleting the cache and re-encoding everything; two
files is the version where the safe path is also the cheap one.

Stage 2c is a separate ground truth with its own two commands:

```
uv run driftwood doc-sample
uv run driftwood doc-eval review/2c/SHEET.md --out data/scores/doclabel.json
```

`doc-sample` writes `review/2c/SHEET.md` plus every sampled document and every candidate code
file under `review/2c/text/`, because the clones are bare and a reviewer needs to read the code
to answer. The sheet is handed over with nothing ticked — a judgement suggested by a ranker
cannot then be used to grade that ranker, and a suggestion from anything else is still an
anchor. `doc-eval` reads the filled sheet back and scores the same rankers with the same
shuffled floor, so the only difference between its table and `retrieve-eval`'s is where the
ground truth came from. Add `--embed-model` to include the dense arm.

## Licence

MIT.
