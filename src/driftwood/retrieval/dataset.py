"""Turn mined shape-A pairs into retrieval queries with judged relevant answers.

One query is one documentation file **at the sha its judgement was made at**, and its
relevant set is the code files that co-changed with it there while sharing an
identifier -- the mining stage's evidence that the doc makes a claim about that code.

The sha is the load-bearing decision, and it was not the first design. Scoring every
query against one recent tree per repo looked simpler and cost 64% of the judged
pairs in `pallets/flask` and 30 of 36 in `psf/requests`: both projects moved to a
`src/` layout inside the mining window, so `requests/adapters.py` is not a path that
exists any more. That loss is not attrition, it is *systematic* -- it deletes exactly
the core library modules and keeps `setup.py` and `docs/conf.py`, leaving a sample
biased toward the odd pairs while still reporting a confident number.

Following the renames was tried and rejected. `git diff -M` between the two trees
returns, for `psf/requests`, three renames of which two are wrong: an empty
`__init__.py` matched a different empty `__init__.py`, and `docs/dev/internals.rst`
was matched to `src/requests/py.typed` at 100% similarity because both are nearly
empty. It never found the real module moves. A remap built from that would have
scored a documentation file against `py.typed` and never said so.

Evaluating at the judged sha needs no rename detection and no per-repo path rule. It
costs a candidate pool that differs per query, which is the honest shape of the
problem anyway: the floor in `evaluate` is computed per query against that query's
own pool, so a small tree cannot borrow credibility from a large one.

Two properties of this ground truth still constrain what can be reported:

1. **Unjudged is not irrelevant.** A doc/code pair that never happened to co-change
   is absence of evidence, not evidence of no relation. So precision@k is
   uninterpretable -- a ranker would be penalised for retrieving a correct file
   nobody judged. Recall@k and MRR only, and both are *lower bounds*.

2. **A doc judged in many commits contributes many queries.** That is a real
   weighting: `docs/index.md` fixed twenty times is twenty retrieval instances. It
   is also how one file could quietly decide a repo's score, so the report prints
   distinct docs beside the query count and the largest single-doc share.

And one that constrains what can be *believed*, which is worse. Shape A selects pairs
that co-changed **while sharing an identifier**, so the ground truth was built with the
same signal the lexical ranker scores with. A lexical baseline is therefore being
graded on a set chosen for suiting it, which is the same error as quoting a retention
figure computed on the cases its filter was designed against. Every record names the
identifiers the miner accepted as its reason, so each query carries them as
`evidence`, and `evaluate` runs a second lexical arm with exactly those tokens struck
out of the query. The gap between the two arms is the part of the score that came from
the label definition rather than from retrieval.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ..mining.gitio import list_files, local_name_for
from ..mining.paths import Kind, classify

__all__ = ["Query", "RepoSplit", "build", "format_dataset_report"]

# Only shape A carries a code path. Shape B is a doc-only fix: no second file, so it
# judges nothing about retrieval and is not a query here.
SHAPE_WITH_CODE_PATH = "A"
POSITIVE_LABEL = "drift"


@dataclass(frozen=True)
class Query:
    repo: str
    doc_path: str
    at_sha: str
    relevant: frozenset[str]
    # The identifiers the miner used as its reason for believing this pair is
    # related. Carried so the lexical ranker can be scored with them removed --
    # see the circularity note in the module docstring.
    evidence: frozenset[str] = frozenset()

    @property
    def query_id(self) -> str:
        return f"{self.repo}:{self.at_sha[:12]}:{self.doc_path}"


@dataclass
class RepoSplit:
    """One repo's queries, plus the candidate pool at each sha they are scored on."""

    repo: str
    clone: Path
    queries: list[Query]
    pools: dict[str, list[str]]
    # A judged code file absent from its own tree's CODE pool. Should be ~zero by
    # construction; it is counted anyway, because "should be zero" is how a silent
    # ceiling on recall gets shipped.
    dropped_positives: int = 0
    dropped_docs: int = 0
    shas_unreadable: list[str] = field(default_factory=list)

    @property
    def judged_pairs(self) -> int:
        return sum(len(q.relevant) for q in self.queries)

    @property
    def distinct_docs(self) -> int:
        return len({q.doc_path for q in self.queries})

    @property
    def pool_sizes(self) -> tuple[int, int, int]:
        """min, median, max candidate-pool size across this repo's queries."""
        sizes = sorted(len(self.pools[q.at_sha]) for q in self.queries)
        if not sizes:
            return (0, 0, 0)
        return (sizes[0], sizes[len(sizes) // 2], sizes[-1])

    @property
    def busiest_doc_share(self) -> float:
        if not self.queries:
            return 0.0
        counts = Counter(q.doc_path for q in self.queries)
        return counts.most_common(1)[0][1] / len(self.queries)


def build(
    labels_path: Path,
    *,
    clone_root: Path,
    repos: list[str] | None = None,
) -> list[RepoSplit]:
    """Read a mined label file and assemble one `RepoSplit` per repo.

    No manifest is needed: the tree each query is scored against comes from the
    record's own `at_sha`, so a clone fetched since the mine cannot move a pool.
    """
    wanted = set(repos) if repos else None
    # (repo, sha, doc_path) -> code paths judged relevant in that state.
    grouped: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    # ...and the identifiers the miner accepted as its reason, unioned over the pairs
    # that share a query. Unioned rather than kept per pair because the ablation asks
    # "could this doc find its code without the tokens that selected it", and any of
    # those tokens would have served.
    evidence: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    with labels_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["shape"] != SHAPE_WITH_CODE_PATH:
                continue
            if record["label"] != POSITIVE_LABEL:
                continue
            if wanted is not None and record["repo"] not in wanted:
                continue
            key = (record["repo"], record["at_sha"], record["doc_path"])
            grouped[key].add(record["code_path"])
            evidence[key].update(record.get("shared_identifiers") or ())

    by_repo: dict[str, list[tuple[str, str, set[str], set[str]]]] = defaultdict(list)
    for key, code_paths in grouped.items():
        repo, sha, doc_path = key
        by_repo[repo].append((sha, doc_path, code_paths, evidence[key]))

    splits: list[RepoSplit] = []
    for repo in sorted(by_repo):
        clone = clone_root / local_name_for(repo)
        pools: dict[str, list[str]] = {}
        queries: list[Query] = []
        dropped_positives = 0
        dropped_docs = 0
        unreadable: list[str] = []

        for sha, doc_path, code_paths, tokens in sorted(
            by_repo[repo], key=lambda row: (row[0], row[1])
        ):
            if sha not in pools:
                try:
                    present = list_files(clone, sha)
                except Exception:  # a shallow or re-cloned repo can lack the sha
                    unreadable.append(sha)
                    pools[sha] = []
                    continue
                pools[sha] = sorted(
                    path for path in present if classify(path) is Kind.CODE
                )
            pool = pools[sha]
            if not pool:
                dropped_docs += 1
                continue
            keep = code_paths & set(pool)
            dropped_positives += len(code_paths) - len(keep)
            if not keep:
                dropped_docs += 1
                continue
            queries.append(
                Query(
                    repo=repo,
                    doc_path=doc_path,
                    at_sha=sha,
                    relevant=frozenset(keep),
                    evidence=frozenset(tokens),
                )
            )

        splits.append(
            RepoSplit(
                repo=repo,
                clone=clone,
                queries=queries,
                pools=pools,
                dropped_positives=dropped_positives,
                dropped_docs=dropped_docs,
                shas_unreadable=sorted(set(unreadable)),
            )
        )
    return splits


def format_dataset_report(splits: list[RepoSplit]) -> str:
    """What the eval is running on, printed before any metric.

    A retrieval figure quoted without its pool size and its concentration is not
    checkable by the person reading it, so both go above the results rather than in
    a footnote nobody reaches.
    """
    lines = [
        "dataset (doc -> code; each query scored on the tree its judgement was made at)",
        f"{'repo':<20}{'queries':>8}{'docs':>6}{'pairs':>7}"
        f"{'pool min/med/max':>19}{'top doc':>9}{'lost':>6}",
    ]
    for split in splits:
        low, mid, high = split.pool_sizes
        lines.append(
            f"{split.repo:<20}{len(split.queries):>8}{split.distinct_docs:>6}"
            f"{split.judged_pairs:>7}{f'{low}/{mid}/{high}':>19}"
            f"{split.busiest_doc_share:>8.0%}"
            f"{split.dropped_positives + split.dropped_docs:>6}"
        )
        if split.shas_unreadable:
            lines.append(
                f"{'':<20}  WARNING: {len(split.shas_unreadable)} sha(s) not in the "
                "clone -- their queries are absent, not failed"
            )
    lines.append(
        "  top doc = share of this repo's queries coming from its most-judged file."
    )
    lines.append(
        "  A high share means the score is one document's score wearing a repo's name."
    )
    lines.append(
        "  lost = judged files absent from their own tree's pool; should be ~0 here, "
        "and is printed"
    )
    lines.append("  rather than assumed, because a lost positive caps recall silently.")
    return "\n".join(lines)
