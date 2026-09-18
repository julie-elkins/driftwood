"""Does the dense arm find anything the free baseline misses?

Run after `retrieve-eval --embed-model`, which leaves the vectors this reads:

    uv run python scripts/complementarity.py data/labels-v11.jsonl

`retrieve-eval` established that dense loses to `lexical-ablated` on all five repos.
That kills it as a *replacement* and says nothing about it as a *contributor*: a
ranker can be worse overall and still be right about cases the better ranker misses,
which is the entire premise of hybrid retrieval. This measures that directly instead
of assuming it either way.

Three deliberate choices, each of which the obvious version gets wrong:

**hit@10 as a binary, not recall.** The question a hybrid turns on is whether the
query is answerable at all from the candidates fetched. Recall over a 20-file union
is not comparable to recall at k=10 -- it would credit the union for a larger budget
and report a lift that is purely arithmetic.

**Both arms ablated.** The unablated numbers include the share of the score that came
from the miner's own evidence tokens. Comparing arms on those measures the label
definition as much as the rankers.

**A budget-matched control: lexical@20.** This is the check that matters and the one
that is easy to skip. A union of two top-10s inspects twenty files, so the honest
comparison is not lexical@10 -- it is lexical@20, the other thing you could have done
with the same budget. Without this control, any second ranker that is not actively
harmful shows a "lift", and the lift is the budget rather than the ranker.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from driftwood.mining.gitio import read_blobs
from driftwood.retrieval import dataset
from driftwood.retrieval.embed import (
    Chunking,
    Dense,
    EmbeddingCache,
    SentenceTransformerEncoder,
    default_cache_path,
)
from driftwood.retrieval.rankers import Lexical

K = 10


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--clone-root", type=Path, default=Path(".cache/clones"))
    parser.add_argument("--embed-cache-root", type=Path, default=Path(".cache/embeddings"))
    parser.add_argument("--embed-chunk", type=int, default=1600)
    parser.add_argument("--embed-overlap", type=int, default=200)
    args = parser.parse_args()

    chunking = Chunking(size=args.embed_chunk, overlap=args.embed_overlap)
    encoder = SentenceTransformerEncoder()
    cache_path = default_cache_path(encoder.model_id, chunking, args.embed_cache_root)
    if not cache_path.exists():
        print(f"no vectors at {cache_path}; run retrieve-eval --embed-model first")
        return 2
    embed_cache = EmbeddingCache(cache_path, encoder.model_id, chunking)

    splits = dataset.build(args.labels, clone_root=args.clone_root)
    token_cache: dict[str, frozenset[str]] = {}
    rows = []

    for split in splits:
        by_sha: dict[str, list] = defaultdict(list)
        for query in split.queries:
            by_sha[query.at_sha].append(query)

        cell = {"both": 0, "lexical_only": 0, "dense_only": 0, "neither": 0, "lex20": 0}
        for sha, sha_queries in by_sha.items():
            pool = split.pools[sha]
            docs = read_blobs(split.clone, sha, [q.doc_path for q in sha_queries])
            code = read_blobs(split.clone, sha, pool)
            lexical = Lexical(code, token_cache)
            dense = Dense(encoder, code, embed_cache)

            for query in sha_queries:
                text = docs.get(query.doc_path, "")
                lex_ranked = lexical.rank(query.doc_path, text, pool, query.evidence)
                dense_ranked = dense.rank(query.doc_path, text, pool, query.evidence)
                lex_hit = bool(set(lex_ranked[:K]) & query.relevant)
                dense_hit = bool(set(dense_ranked[:K]) & query.relevant)
                cell["lex20"] += bool(set(lex_ranked[: 2 * K]) & query.relevant)
                if lex_hit and dense_hit:
                    cell["both"] += 1
                elif lex_hit:
                    cell["lexical_only"] += 1
                elif dense_hit:
                    cell["dense_only"] += 1
                else:
                    cell["neither"] += 1
        rows.append((split.repo, cell))

    print(
        f"{'repo':<20}{'n':>5}{'both':>6}{'lex only':>9}{'dense only':>11}{'neither':>8}"
        f"{'lex@10':>8}{'union':>7}{'lex@20':>8}{'union wins':>11}"
    )
    for repo, cell in rows:
        n = cell["both"] + cell["lexical_only"] + cell["dense_only"] + cell["neither"]
        lex10 = (cell["both"] + cell["lexical_only"]) / n
        union = (cell["both"] + cell["lexical_only"] + cell["dense_only"]) / n
        lex20 = cell["lex20"] / n
        print(
            f"{repo:<20}{n:>5}{cell['both']:>6}{cell['lexical_only']:>9}"
            f"{cell['dense_only']:>11}{cell['neither']:>8}"
            f"{lex10:>8.2f}{union:>7.2f}{lex20:>8.2f}"
            f"{('yes' if union > lex20 else 'no'):>11}"
        )

    print()
    print("union = lexical@10 OR dense@10, so it inspects 20 files per query.")
    print("lex@20 is what the same budget buys from the free ranker alone, and is")
    print("therefore the bar the union has to clear. 'no' means the dense arm is not")
    print("worth its half of the budget: more lexical results would have been better.")
    print()
    print("No pooled row. Per repo, as everywhere else in this harness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
