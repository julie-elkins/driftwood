"""Score rankers per repo, against a measured floor rather than against zero.

Two metrics, both chosen because the ground truth is incomplete (see `dataset`):

- **recall@k** -- of this doc's judged code files, what fraction made the top k.
  Macro-averaged over queries, not pooled over pairs, so a doc with eleven answers
  does not outvote ten docs with one.
- **MRR** -- one over the rank of the first correct answer. Reported because it
  matches how the pipeline will use this: an agent reads a couple of files, so where
  the *first* right answer lands is what decides whether a run is affordable.

Precision@k is absent on purpose. An unjudged file is not a wrong answer here, and
scoring it as one would punish a ranker for being right.

Every eval runs a shuffle arm over several trials, and it is the reason the rest is
readable. Each query is scored against the candidate pool of its own tree, and those
pools run from twenty-odd files to five hundred; ranking four answers out of
twenty-two candidates puts one in the top ten about half the time on its own. The
shuffle arm prices exactly that, per repo, on exactly those pools -- so a baseline
can be seen to be *below* chance, which is a thing that happened on the first run and
would otherwise have been reported as "25% recall".

The trial spread is the second output and the less obvious one. It is the noise floor
of the metric on this dataset: a gain smaller than the spread has not been shown to
be a gain, the same discipline as reporting a Wilson interval instead of a point
estimate.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from ..mining.gitio import read_blobs
from .dataset import Query, RepoSplit
from .rankers import Lexical, LexicalTF, PathOverlap, Ranker, Shuffle

__all__ = [
    "DEFAULT_KS",
    "NULL_TRIALS",
    "RepoResult",
    "evaluate_split",
    "format_results",
    "score_queries",
    "to_json",
]

DEFAULT_KS = (1, 5, 10)

# Enough trials for a stable range without making the eval slow. The shuffle arm
# reads no files and tokenises nothing, so it is the cheapest thing in the harness.
NULL_TRIALS = 40


@dataclass(frozen=True)
class RepoResult:
    repo: str
    pool_median: int
    queries: int
    ranker: str
    recall_at: dict[int, float]
    mrr: float
    # Present only on the shuffle arm: the observed range of each metric under noise.
    recall_spread: dict[int, tuple[float, float]] | None = None
    mrr_spread: tuple[float, float] | None = None


def _recall_at(ranked: list[str], relevant: frozenset[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant)


def _reciprocal_rank(ranked: list[str], relevant: frozenset[str]) -> float:
    for position, path in enumerate(ranked, start=1):
        if path in relevant:
            return 1.0 / position
    return 0.0


def score_queries(
    rankers: dict[str, Ranker],
    queries: list[Query],
    pool: list[str],
    doc_texts: dict[str, str],
    ks: tuple[int, ...] = DEFAULT_KS,
    ablate: bool = False,
) -> dict[str, tuple[list[dict[int, float]], list[float]]]:
    """Per-query recall@k and reciprocal rank for several rankers on one tree.

    With `ablate`, each query's own mined evidence tokens are struck out before
    ranking. That is not a fairer version of the task, it is a *harder* one: it asks
    whether the doc could still find its code without the words that got the pair
    labelled in the first place.

    Returns the per-query values rather than their means, because a repo's score has
    to be averaged across all of its trees at once -- averaging per tree first would
    silently weight a sha with one query the same as a sha with thirty.
    """
    out: dict[str, tuple[list[dict[int, float]], list[float]]] = {
        name: ([], []) for name in rankers
    }
    for name, ranker in rankers.items():
        recalls, ranks = out[name]
        for query in queries:
            ranked = ranker.rank(
                query.doc_path,
                doc_texts.get(query.doc_path, ""),
                pool,
                query.evidence if ablate else frozenset(),
            )
            recalls.append({k: _recall_at(ranked, query.relevant, k) for k in ks})
            ranks.append(_reciprocal_rank(ranked, query.relevant))
    return out


def evaluate_split(
    split: RepoSplit,
    ks: tuple[int, ...] = DEFAULT_KS,
    null_trials: int = NULL_TRIALS,
    token_cache: dict[str, frozenset[str]] | None = None,
    dense: Callable[[dict[str, str]], Ranker] | None = None,
    # Separate from `token_cache` because the values are Counters rather than frozensets;
    # one shared dict would hand whichever ranker ran second the wrong type. Threaded
    # through from the caller for the same reason `token_cache` is -- most files are
    # byte-identical across the ~350 shas scored, and the cache is what makes that cheap.
    count_cache: dict[str, Counter[str]] | None = None,
    tf_k1: float | None = None,
    # Takes the base ranker AND the tree's code texts, because a reranker is a wrapper
    # rather than a peer: it needs the same `lexical` object the baseline rows were
    # scored with, or the head it reorders is not the head those rows reported.
    rerank: Callable[[Ranker, dict[str, str]], Ranker] | None = None,
    rerank_name: str | None = None,
) -> list[RepoResult]:
    """Run the shuffle floor and both free baselines on one repo.

    Walks the repo one tree at a time, because the candidate pool and the IDF
    statistics both belong to a tree. Every ranker sees the same strings for a given
    sha: reading per ranker instead would be slower and would let two rankers be
    scored against different trees if the clone moved mid-run.
    """
    if not split.queries:
        return []

    by_sha: dict[str, list[Query]] = defaultdict(list)
    for query in split.queries:
        by_sha[query.at_sha].append(query)

    # The dense arms are appended rather than interleaved so the free baselines keep
    # their row order across runs with and without a model -- a table that reorders
    # itself is a table two runs cannot be diffed by eye.
    scored_names = ["path", "lexical", "lexical-ablated"]
    # Appended after the established free baselines and before the dense arms, so adding
    # it does not reorder any row that already exists in a committed results file.
    tf_name = f"lexical-tf(k1={tf_k1:g})" if tf_k1 is not None else None
    if tf_name is not None:
        scored_names += [tf_name, f"{tf_name}-ablated"]
    if dense is not None:
        scored_names += ["dense", "dense-ablated"]
    # Last, so the free rows and the dense rows keep the order every committed results
    # file already has. The reranker is also the only arm whose row must be read
    # ADJACENT to its base's: alone it says nothing, because R@top_n is the base's by
    # construction and the gain is only ever a reordering inside that set.
    if rerank is not None:
        if rerank_name is None:
            raise ValueError("a rerank factory needs its row name; two cutoffs must not share a row")
        scored_names += [rerank_name, f"{rerank_name}-ablated"]
    names = ["shuffle (floor)", *scored_names]
    recalls: dict[str, list[dict[int, float]]] = {name: [] for name in names}
    ranks: dict[str, list[float]] = {name: [] for name in names}
    # The floor's per-trial means, so the noise range is a range over *trials* rather
    # than over queries -- those are different quantities and only the first one says
    # whether a difference between two rankers is readable.
    trial_recalls: list[dict[int, float]] = []
    trial_ranks: list[float] = []
    per_trial: dict[int, tuple[list[dict[int, float]], list[float]]] = {
        seed: ([], []) for seed in range(null_trials)
    }
    cache = token_cache if token_cache is not None else {}
    counts = count_cache if count_cache is not None else {}

    for sha, sha_queries in by_sha.items():
        pool = split.pools[sha]
        doc_texts = read_blobs(split.clone, sha, [q.doc_path for q in sha_queries])
        code_texts = read_blobs(split.clone, sha, pool)

        lexical = Lexical(code_texts, cache)
        scored = score_queries(
            {"path": PathOverlap(), "lexical": lexical},
            sha_queries,
            pool,
            doc_texts,
            ks,
        )
        # Same ranker object, same tree, same IDF -- only the query loses the tokens
        # the miner matched on, so the gap between the two rows is attributable.
        scored.update(
            score_queries(
                {"lexical-ablated": lexical}, sha_queries, pool, doc_texts, ks, ablate=True
            )
        )
        if tf_name is not None:
            # Same tree, same pool, same queries as `lexical` above -- the only difference
            # between the two rows is the term-frequency factor, which is what makes the
            # gap between them attributable to it.
            lexical_tf = LexicalTF(code_texts, counts, k1=tf_k1)
            scored.update(
                score_queries({tf_name: lexical_tf}, sha_queries, pool, doc_texts, ks)
            )
            scored.update(
                score_queries(
                    {f"{tf_name}-ablated": lexical_tf},
                    sha_queries, pool, doc_texts, ks, ablate=True,
                )
            )
        if dense is not None:
            # Built per tree, because the chunk matrix belongs to a tree -- but the
            # embedding cache behind it is shared across every tree and every repo,
            # which is what makes 629 trees affordable.
            ranker = dense(code_texts)
            scored.update(
                score_queries({"dense": ranker}, sha_queries, pool, doc_texts, ks)
            )
            scored.update(
                score_queries(
                    {"dense-ablated": ranker}, sha_queries, pool, doc_texts, ks, ablate=True
                )
            )
        if rerank is not None:
            # Wraps the SAME `lexical` object scored above, so `rerank(lexical@20)` and
            # `lexical` differ by the reordering and nothing else -- not by a second
            # tokenisation, and not by a differently-built IDF.
            reranker = rerank(lexical, code_texts)
            if reranker.name != rerank_name:
                raise ValueError(
                    f"reranker names itself {reranker.name!r} but the table reserved "
                    f"{rerank_name!r}; the row would be labelled with the wrong cutoff"
                )
            scored.update(
                score_queries({rerank_name: reranker}, sha_queries, pool, doc_texts, ks)
            )
            scored.update(
                score_queries(
                    {f"{rerank_name}-ablated": reranker},
                    sha_queries, pool, doc_texts, ks, ablate=True,
                )
            )
        for name, (query_recalls, query_ranks) in scored.items():
            recalls[name].extend(query_recalls)
            ranks[name].extend(query_ranks)

        for seed in range(null_trials):
            floor = score_queries(
                {"shuffle": Shuffle(seed=seed)}, sha_queries, pool, doc_texts, ks
            )["shuffle"]
            per_trial[seed][0].extend(floor[0])
            per_trial[seed][1].extend(floor[1])

    for seed in range(null_trials):
        query_recalls, query_ranks = per_trial[seed]
        trial_recalls.append(
            {k: statistics.fmean(r[k] for r in query_recalls) for k in ks}
        )
        trial_ranks.append(statistics.fmean(query_ranks))
    recalls["shuffle (floor)"] = trial_recalls
    ranks["shuffle (floor)"] = trial_ranks

    median_pool = split.pool_sizes[1]
    results = [
        RepoResult(
            repo=split.repo,
            pool_median=median_pool,
            queries=len(split.queries),
            ranker="shuffle (floor)",
            recall_at={k: statistics.fmean(r[k] for r in trial_recalls) for k in ks},
            mrr=statistics.fmean(trial_ranks),
            recall_spread={
                k: (min(r[k] for r in trial_recalls), max(r[k] for r in trial_recalls))
                for k in ks
            },
            mrr_spread=(min(trial_ranks), max(trial_ranks)),
        )
    ]
    for name in scored_names:
        results.append(
            RepoResult(
                repo=split.repo,
                pool_median=median_pool,
                queries=len(split.queries),
                ranker=name,
                recall_at={k: statistics.fmean(r[k] for r in recalls[name]) for k in ks},
                mrr=statistics.fmean(ranks[name]),
            )
        )
    return results


def format_results(
    results: list[RepoResult],
    ks: tuple[int, ...] = DEFAULT_KS,
    null_trials: int = NULL_TRIALS,
) -> str:
    """Per repo, floor first. There is no pooled row, and that is a design choice.

    A mean across repos whose median pools run from 22 files to 527 would be dominated
    by whichever repo contributed the most queries, and would move when the corpus
    changed rather than when the ranker did.

    `null_trials` is a parameter rather than the module constant because the footer
    states it as a fact about the run. A `--null-trials 8` run printing "over 40
    trials" would understate the noise range by a factor the reader cannot see, and
    the noise range is the thing that decides whether any gap in the table is readable.
    """
    # Widened to fit the longest ranker name, floored at the 17 the fixed-width version
    # used. `lexical-tf(k1=1.2)-ablated` is 26 characters and carries its k1 because two
    # settings must not collide under one row; a name overflowing its column shifts every
    # number to the right of it on that line only, which reads as a different table.
    ranker_width = max(17, *(len(result.ranker) + 2 for result in results))
    header = f"{'repo':<20}{'ranker':<{ranker_width}}{'pool~':>6}{'n':>5}"
    for k in ks:
        header += f"{'R@' + str(k):>7}"
    header += f"{'MRR':>7}"
    lines = [header]

    for result in results:
        row = (
            f"{result.repo:<20}{result.ranker:<{ranker_width}}"
            f"{result.pool_median:>6}{result.queries:>5}"
        )
        for k in ks:
            row += f"{result.recall_at[k]:>7.2f}"
        row += f"{result.mrr:>7.2f}"
        lines.append(row)
        if result.recall_spread is not None:
            spread = f"{'':<20}{'  noise range':<{ranker_width}}{'':>6}{'':>5}"
            for k in ks:
                low, high = result.recall_spread[k]
                spread += f" {low:.2f}-{high:.2f}"
            assert result.mrr_spread is not None
            spread += f" {result.mrr_spread[0]:.2f}-{result.mrr_spread[1]:.2f}"
            lines.append(spread)

    lines.append("")
    lines.append(
        f"pool~ is the median candidate count; the floor is a shuffled ranking over "
        f"{null_trials} trials"
    )
    lines.append(
        "on each query's own pool. A ranker inside the noise range has not been shown "
        "to work,"
    )
    lines.append(
        "and one below the floor is worse than chance -- which a bare recall figure "
        "reads as success."
    )
    lines.append(
        "No pooled row: recall on a 22-file pool and on a 527-file pool are not the "
        "same measurement."
    )
    # Gated on an ablated row actually being present. The hand-labelled corpus has no
    # mining rule behind it and therefore no evidence tokens to strike, so printing
    # this paragraph there would explain a row that is not in the table -- and would
    # imply the numbers above it had been bounded for circularity when they had not.
    if any(result.ranker.endswith("-ablated") for result in results):
        lines.append("")
        lines.append(
            "lexical-ablated re-runs the same ranker with each query's mined evidence "
            "tokens struck"
        )
        lines.append(
            "out. The gap to `lexical` is the share of the score that came from the "
            "label definition"
        )
        lines.append(
            "rather than from retrieval: shape A selects pairs for sharing an "
            "identifier, which is"
        )
        lines.append(
            "what this ranker scores with. The ablated row is the defensible number."
        )
    if any(result.ranker.startswith("dense") for result in results):
        lines.append("")
        lines.append(
            "dense chunks both sides and scores max cosine over (doc chunk, code "
            "chunk) pairs."
        )
        lines.append(
            "Truncating to 512 tokens instead costs 30-45% of MRR on this corpus, "
            "measured with"
        )
        lines.append(
            "`lexical` before any model was installed -- so the dense arm chunks and "
            "drops nothing."
        )
        if any(result.ranker == "dense-ablated" for result in results):
            lines.append(
                "Its ablation REDACTS the evidence tokens from the doc text, which "
                "perturbs the"
            )
            lines.append(
                "surrounding context too. A wider dense gap than lexical's is "
                "therefore not by"
            )
            lines.append("itself evidence of more circularity.")
            lines.append(
                "The bar for dense is `lexical-ablated` PER REPO, not the floor."
            )
        else:
            lines.append(
                "The bar for dense is `lexical` PER REPO, not the floor -- and on this "
                "corpus that"
            )
            lines.append(
                "is an unablated `lexical`, because no mining rule selected these "
                "pairs."
            )
    # Printed whenever a rerank row is present, because the row is unreadable without
    # it: a reader who does not know R@N is pinned will read an unchanged R@20 as the
    # reranker having no effect, when it is the one number it cannot possibly move.
    rerank_rows = [r for r in results if r.ranker.startswith("rerank(")]
    if rerank_rows:
        cutoffs = sorted({r.ranker.split("@")[-1].split(")")[0] for r in rerank_rows})
        lines.append("")
        lines.append(
            f"rerank(...@N) reorders only its base ranker's top N (N={', '.join(cutoffs)}) "
            "and leaves the"
        )
        lines.append(
            "tail alone, so recall@k for every k >= N is the BASE ranker's number, "
            "unchanged by"
        )
        lines.append(
            "construction rather than unmoved by the model. Only R@k below N and MRR "
            "can move."
        )
        lines.append(
            "Read each rerank row against its own base row, never against the floor: "
            "the headroom"
        )
        lines.append(
            "is base R@k to base R@N, and on the small-pool repos that whole span is "
            "narrower than"
        )
        lines.append("the noise range -- there, a perfect reranker cannot show a gain.")
    return "\n".join(lines)


def to_json(
    results: list[RepoResult],
    splits: list[RepoSplit],
    provenance: dict | None = None,
    null_trials: int = NULL_TRIALS,
) -> dict:
    """Results as data, so a later run is diffable against this one.

    Same reasoning as the mine manifests: a number that only ever existed in a
    terminal cannot be compared against next month's number.

    `provenance` carries the model id and chunking for a dense run. A dense score
    without them is uncheckable: two runs at different chunk sizes produce different
    numbers from identical code and identical labels, and nothing in the table says
    which is which.

    `null_trials` is a parameter for exactly the reason it is one on `format_results`,
    and this is the third place that defect has been found: the field used to be the
    module constant, so a `--null-trials 8` run wrote "40" into a results file whose
    noise ranges were eight trials wide. The footer lied for one run and was fixed;
    this lied permanently, in the artefact the footer's fix exists to make diffable.
    The `k` values are recorded for the same reason -- they are configurable now, and a
    `recall_at` map is uninterpretable without knowing which ks the run was asked for.
    """
    ks = sorted({int(k) for result in results for k in result.recall_at})
    return {
        "eval": "retrieval-doc-to-code",
        "scored_at": "each query's own at_sha",
        "null_trials": null_trials,
        "ks": ks,
        "ranker_provenance": provenance or {"dense": "not run -- free baselines only"},
        "dataset": [
            {
                "repo": split.repo,
                "queries": len(split.queries),
                "distinct_docs": split.distinct_docs,
                "distinct_shas": len({q.at_sha for q in split.queries}),
                "judged_pairs": split.judged_pairs,
                "pool_min_median_max": list(split.pool_sizes),
                "busiest_doc_share": split.busiest_doc_share,
                "dropped_positives": split.dropped_positives,
                "dropped_docs": split.dropped_docs,
                "shas_unreadable": split.shas_unreadable,
            }
            for split in splits
        ],
        "results": [
            {
                "repo": result.repo,
                "ranker": result.ranker,
                "pool_median": result.pool_median,
                "queries": result.queries,
                "recall_at": {str(k): v for k, v in result.recall_at.items()},
                "mrr": result.mrr,
                "recall_noise_range": (
                    {str(k): list(v) for k, v in result.recall_spread.items()}
                    if result.recall_spread
                    else None
                ),
                "mrr_noise_range": list(result.mrr_spread) if result.mrr_spread else None,
            }
            for result in results
        ],
    }
