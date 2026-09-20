"""Zero-dependency rankers, including the one that is supposed to be bad.

A ranker takes a query document and a pool of candidate code files and returns the
pool ordered best-first. That is the whole interface, so an embedding model, a
reranker or an LLM drops in beside these without the eval changing.

`Shuffle` is not a placeholder. It is the instrument that tells you what the number
you just got is worth. On a 22-file pool, ranking at random puts a correct answer in
the top 10 about 45% of the time -- so a model scoring 50% there has demonstrated
nothing, and the only way to know that is to have run the shuffle on the same pool
and seen 45%. Without it, "recall@10 = 0.50" reads like a result.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from ..mining.identifiers import MIN_TOKEN_LENGTH, extract, extract_counts

__all__ = [
    "DEFAULT_K1",
    "Lexical",
    "LexicalTF",
    "PathOverlap",
    "Ranker",
    "Shuffle",
    "path_tokens",
]


class Ranker(Protocol):
    name: str

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        """Return every path in `pool`, best first.

        `exclude` is the set of tokens the miner used as its evidence that this pair
        is related. Rankers that consume identifier tokens must honour it, so the
        harness can measure how much of a score came from the label definition.
        Rankers that do not use those tokens ignore it.
        """


def _stable_order(scores: dict[str, float], pool: list[str]) -> list[str]:
    """Sort by score, breaking ties by path.

    The tiebreak is load-bearing rather than tidy. Most candidates score exactly
    zero under a sparse ranker, so without a deterministic tiebreak the ordering of
    the zero-scoring tail comes from dict insertion order -- and recall@10 on a
    22-file pool would then depend on the order `ls-tree` happened to emit. Two
    runs of the same code would disagree, and the disagreement would look like
    variance in the ranker.
    """
    return sorted(pool, key=lambda path: (-scores.get(path, 0.0), path))


@dataclass
class Shuffle:
    """The control arm. Ranks at random from a fixed seed.

    Seeded per query *and* per trial, so a single eval run is reproducible while a
    multi-trial null run still explores different orderings. An unseeded shuffle
    would make the floor unrepeatable, which defeats the point of measuring it.
    """

    seed: int = 0
    name: str = "shuffle"

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        order = list(pool)
        random.Random(f"{self.seed}:{doc_path}").shuffle(order)
        return order


def _split(piece: str) -> set[str]:
    return {
        token
        for part in piece.replace("-", "_").replace(".", "_").split("_")
        if len(token := part.lower()) >= MIN_TOKEN_LENGTH
    }


def path_tokens(path: str) -> set[str]:
    """Every token in a path, from its directories and its filename.

    `docs/advanced/custom_response.md` -> {docs, advanced, custom, response}. Short
    pieces are dropped on the same threshold the identifier extractor uses, so `src`,
    `lib` and single letters do not become the whole signal.
    """
    pure = PurePosixPath(path)
    tokens: set[str] = set()
    for piece in (*pure.parent.parts, pure.stem):
        tokens |= _split(piece)
    return tokens


def stem_tokens(path: str) -> set[str]:
    """Just the tokens in the filename."""
    return _split(PurePosixPath(path).stem)


@dataclass
class PathOverlap:
    """Rank by how much the candidate's path resembles the doc's path.

    Worth measuring because it is nearly free and, in a repo whose docs mirror its
    module layout, it is genuinely strong: `docs/api/routing.md` -> `src/routing.py`
    needs no model at all. It is also the baseline most likely to be *quietly*
    beaten-looking, since a repo with that convention rewards it for the convention
    rather than for understanding anything -- which is exactly why the per-repo
    breakdown matters more than the mean.

    A shared token must involve at least one of the two *filenames*. The first version
    of this ranker matched any shared token, directory names included, and scored below
    chance on `pallets/flask`: every flask doc is under `docs/`, most flask doc paths
    reduce to that single token once pieces shorter than four characters are dropped
    (`docs/api.rst` -> {docs}), and `docs/conf.py` is the shortest pool path sharing it.
    So the length normaliser handed `docs/conf.py` rank 1 for 388 of 396 queries.

    Two files sitting in the same directory is not evidence about *which* file, and a
    baseline that is confidently wrong is worse than a weak one -- it understates the
    bar the embedding model has to clear, which is the whole reason for measuring a
    baseline at all.
    """

    name: str = "path"

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        # Path tokens are not what the miner matched on, so there is nothing here to
        # ablate. Ignored explicitly rather than silently.
        doc_all, doc_stem = path_tokens(doc_path), stem_tokens(doc_path)
        scores = {}
        for candidate in pool:
            candidate_all = path_tokens(candidate)
            shared = (doc_all & stem_tokens(candidate)) | (doc_stem & candidate_all)
            if shared:
                # Normalised by the candidate's own token count so a deeply nested
                # path does not win on having more chances to match.
                scores[candidate] = len(shared) / math.sqrt(len(candidate_all) or 1)
        return _stable_order(scores, pool)


@dataclass
class Lexical:
    """Rank by IDF-weighted identifier overlap between doc text and code text.

    Deliberately set overlap rather than full BM25. What matters for "does this doc
    describe this file" is whether a *rare* identifier appears in both at all --
    a doc mentioning `HTTPTransport` once is about the transport module, and it
    being mentioned eleven times in the code does not make it more so. Term
    frequency is the next increment if this underperforms, and it is a cheap one;
    starting without it keeps the baseline something you can reason about by hand.

    IDF is computed over the candidate pool of the repo being evaluated. Tokens
    appearing in nearly every file -- the package's own name, its logger, its base
    exception -- carry almost no weight, which is the whole reason a raw overlap
    count is a poor ranker.
    """

    name: str = "lexical"

    def __init__(
        self,
        code_texts: dict[str, str],
        token_cache: dict[str, frozenset[str]] | None = None,
    ) -> None:
        # Keyed by a hash of the file's contents, not by its path. Queries are scored
        # at ~350 different shas across the corpus and most files are byte-identical
        # between them, so a content-keyed cache turns roughly 40k tokenisations into
        # a few thousand. A path-keyed cache would miss every one of those hits and a
        # sha-keyed one would be no cache at all.
        cache = token_cache if token_cache is not None else {}
        self._tokens: dict[str, frozenset[str]] = {}
        for path, text in code_texts.items():
            digest = hashlib.blake2b(text.encode("utf-8", "replace"), digest_size=16)
            key = digest.hexdigest()
            tokens = cache.get(key)
            if tokens is None:
                tokens = frozenset(extract(text, versions=True))
                cache[key] = tokens
            self._tokens[path] = tokens
        document_count = max(len(self._tokens), 1)
        frequency: Counter[str] = Counter()
        for tokens in self._tokens.values():
            frequency.update(tokens)
        # Smoothed IDF, so a token in every file scores near zero rather than
        # exactly zero and a token in none of them cannot divide by zero.
        self._idf = {
            token: math.log(1 + (document_count - count + 0.5) / (count + 0.5))
            for token, count in frequency.items()
        }

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        wanted = extract(doc_text, versions=True) - exclude
        scores: dict[str, float] = {}
        for candidate in pool:
            tokens = self._tokens.get(candidate)
            if not tokens:
                continue
            shared = wanted & tokens
            if not shared:
                continue
            # Divided by sqrt(len) for the same reason BM25 has a length
            # normaliser: a 2000-line module shares tokens with everything, and
            # without this it would rank first for every query in the repo.
            scores[candidate] = sum(self._idf.get(t, 0.0) for t in shared) / math.sqrt(
                len(tokens)
            )
        return _stable_order(scores, pool)


# Saturation constant for `LexicalTF`. BM25's k1, and the same value BM25 conventionally
# uses. `tf / (tf + k1)` at 1.2 scores one mention at 0.45 and eleven at 0.90, so a token
# repeated eleven times is worth about twice one repeated once -- not eleven times.
#
# The saturating form is chosen because of the argument in `Lexical`'s docstring, not
# despite it: "a doc mentioning `HTTPTransport` once is about the transport module, and it
# being mentioned eleven times in the code does not make it more so". That is an argument
# against RAW term frequency, and raw tf is what a first attempt reaches for. It is not an
# argument against a bounded one.
DEFAULT_K1 = 1.2


@dataclass
class LexicalTF:
    """`Lexical` plus saturating term frequency on the candidate side. One lever.

    The cheapest unrun experiment in the project, and `Lexical`'s own docstring named it:
    "Term frequency is the next increment if this underperforms, and it is a cheap one."
    It is scored BESIDE `lexical` rather than replacing it, because the free baseline is
    what every later stage has to beat and a baseline that moves under it is not a floor.

    **It nests the baseline, which is what makes a result attributable.** As `k1` goes to
    zero, `tf / (tf + k1)` goes to 1 for every token that is present at all, and the score
    collapses exactly onto `Lexical`'s. So this is not a reimplementation that happens to
    be similar -- it is the same ranker with one term added, and a loss can be attributed
    to term frequency rather than to a rewrite. A test pins that limit.

    Three things deliberately held still, because the project's own rule is that two
    levers moved at once make a recovered case unattributable:

    1. **IDF is unchanged**, same smoothed document-frequency weight over the same
       per-tree candidate pool.
    2. **The length normaliser is unchanged** -- `sqrt` of the candidate's DISTINCT token
       count. Full BM25 would normalise by total length against the pool average, which
       is a second lever and a different experiment. Noted as the next increment after
       this one, not folded into it.
    3. **The query side is untouched.** BM25 has a query-term-frequency factor; adding it
       here would also change what `exclude` operates on, and ablation is the measurement
       that bounds circularity on this corpus. It stays exactly as strong as it was.
    """

    name: str = "lexical-tf"

    def __init__(
        self,
        code_texts: dict[str, str],
        token_cache: dict[str, Counter[str]] | None = None,
        k1: float = DEFAULT_K1,
    ) -> None:
        if k1 < 0:
            raise ValueError(f"k1 must not be negative, got {k1}")
        self.k1 = k1
        # The name carries k1 for the same reason `lexical-absence` carries its threshold
        # and the per-claim judge carries its batch size: the eval sweeps it, and two
        # settings must not collide in one results table under one row.
        self.name = f"lexical-tf(k1={k1:g})"
        # Content-keyed, exactly as `Lexical`'s cache is and for the same reason -- most
        # files are byte-identical across the ~350 shas scored. A SEPARATE cache from
        # `Lexical`'s, and it has to be: the values are Counters rather than frozensets,
        # so sharing one dict would hand whichever ranker ran second the wrong type.
        cache = token_cache if token_cache is not None else {}
        self._counts: dict[str, Counter[str]] = {}
        for path, text in code_texts.items():
            digest = hashlib.blake2b(text.encode("utf-8", "replace"), digest_size=16)
            key = digest.hexdigest()
            counts = cache.get(key)
            if counts is None:
                counts = extract_counts(text, versions=True)
                cache[key] = counts
            self._counts[path] = counts
        document_count = max(len(self._counts), 1)
        frequency: Counter[str] = Counter()
        for counts in self._counts.values():
            # DOCUMENT frequency, so this counts files rather than mentions. Feeding the
            # Counter straight in would make IDF a function of term frequency too, which
            # would double-count the very thing under test and make the comparison
            # against `Lexical` meaningless.
            frequency.update(counts.keys())
        self._idf = {
            token: math.log(1 + (document_count - count + 0.5) / (count + 0.5))
            for token, count in frequency.items()
        }

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        wanted = extract(doc_text, versions=True) - exclude
        scores: dict[str, float] = {}
        for candidate in pool:
            counts = self._counts.get(candidate)
            if not counts:
                continue
            shared = wanted & counts.keys()
            if not shared:
                continue
            scores[candidate] = sum(
                self._idf.get(t, 0.0) * (counts[t] / (counts[t] + self.k1))
                for t in shared
            ) / math.sqrt(len(counts))
        return _stable_order(scores, pool)
