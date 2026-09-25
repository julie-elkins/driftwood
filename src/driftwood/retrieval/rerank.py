"""Cross-encoder reranking over another ranker's head, with the ceiling built in.

Stage 2d(c). A reranker cannot surface what retrieval never returned, so this wraps a
base ranker, reorders only its top `top_n`, and leaves the tail in base order. That
makes **recall@k invariant for every k >= top_n, by construction** -- so with the
default `top_n=20`, R@20 is exactly the base ranker's R@20 and the only thing a
cross-encoder can move is where inside that set the right answer lands.

Which is why the ceiling was measured before this file was written, with `--ks 20`, and
why the table belongs in the module that implements the thing it constrains:

    repo               pool~   top-20 is   best free R@10   ceiling R@20   R@10 noise
    psf/requests          23         87%             0.76           0.94        0.349
    encode/httpx          24         83%             0.82           0.97        0.168
    pallets/flask         35         57%             0.83           0.93        0.077
    pydantic/pydantic    101         20%             0.57           0.73        0.060
    fastapi/fastapi      685          3%             0.65           0.71        0.037

On `psf/requests` and `encode/httpx` the whole headroom from the best free baseline to
a PERFECT reranker is smaller than the metric's own noise range. Not unlikely to be
readable -- arithmetically incapable of it. Those two repos also happen to be where
top-20 is 83-87% of the entire candidate pool, which is to say there is barely a
retrieval step left to improve. They are two of the three repos the hand-labelled 2c
corpus covers, so 2c is the corpus LEAST able to say anything about this stage, and the
mined one carries the weight here. `pydantic/pydantic` is the most favourable repo,
inverting the assumption that the biggest pool has the most to gain.

**Chunking is sized differently from the dense arm, and it has to be.** `Dense` embeds
each side separately, so a 512-token encoder gives each side its own 512. A cross-encoder
reads the doc chunk and the code chunk in ONE 512-token window, so 1600-character chunks
on both sides would be silently truncated to roughly a third of the pair -- the same
failure the dense arm was designed to avoid, reintroduced by reusing its numbers. Hence
`RERANK_CHUNKING` at 800/100: two of those plus the separator tokens fit.

Scoring is max over (doc chunk, code chunk) pairs, matching `Dense` exactly, so a
difference between the two arms is attributable to the model rather than to the pooling.
The cost of that parity is quadratic -- a 17-chunk doc against a 12-chunk module is 204
forward passes for ONE candidate -- and it is why the pair cache is not optional here in
the way the embedding cache is merely expensive to skip.
"""

from __future__ import annotations

import hashlib
import math
import os
import time
from pathlib import Path
from typing import Protocol

import numpy as np

from . import DEFAULT_RERANK_MODEL, DEFAULT_TOP_N
from .embed import Chunking, _redact, chunk_text
from .rankers import Ranker

__all__ = [
    "RERANK_CHUNKING",
    "CrossEncoderReranker",
    "CrossEncoderScorer",
    "PairCache",
    "PairScorer",
    "default_pair_cache_path",
]

# Both sides share one 512-token window, unlike the dense arm's 1600/200. 800 characters
# is roughly 200 tokens, so a pair lands near 400 plus specials and nothing is truncated.
RERANK_CHUNKING = Chunking(size=800, overlap=100)

# Seconds between mid-split cache checkpoints. 15 minutes is chosen against a measured
# save cost, not picked round: rebuilding and writing the arrays took 6.3s at 7.9M pairs,
# so ~26s at the full run's 32.5M, which is 2.9% overhead at this interval and bounds a
# crash to a quarter hour of GPU time. Lower it and the write starts to dominate; raise it
# and the bound stops being the point.
DEFAULT_SAVE_INTERVAL = 900.0


class PairScorer(Protocol):
    """Anything that scores (query, passage) pairs.

    A Protocol for the same reason `Encoder` is one: the chunking, pooling, cache and
    head/tail logic is where the bugs are, and none of it should need a model download
    to test.
    """

    model_id: str

    def score(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        """Return one float per pair, higher meaning more relevant.

        Unbounded and not comparable across models -- these are logits, not cosines.
        Nothing downstream may assume a sign or a range, which is why the reranker
        sorts by them rather than mixing them with the base ranker's scores.
        """


class PairCache:
    """Pair scores keyed by the hash of both chunk texts, persisted between runs.

    Keyed on the CHUNK TEXTS rather than on (doc path, code path, sha) for the reason
    `EmbeddingCache` is content-keyed, only more so: the same 800-character window of an
    unchanged module is paired with the same window of an unchanged doc at every sha
    where both survive, and the pair count is the product of two chunk counts. A
    path-keyed cache would miss every one of those hits.

    The stamp folds in the model id and the chunking, and a mismatch refuses to load
    rather than mixing two models' logits -- which would be worse than mixing two
    encodings, because logits from different cross-encoders are not even on the same
    scale, so the resulting ranking would be arbitrary and the run would look clean.
    """

    def __init__(
        self,
        path: Path | None,
        model_id: str,
        chunking: Chunking,
        save_interval: float = DEFAULT_SAVE_INTERVAL,
    ) -> None:
        self.path = path
        self.model_id = model_id
        self.chunking = chunking
        self._scores: dict[str, float] = {}
        self.hits = 0
        self.misses = 0
        # Saving only between repos was measured as the wrong granularity, on the run it
        # cost. `pydantic/pydantic` is 41.8 of the 55.1 priced hours -- 76% of the bill in
        # ONE split -- so the between-repos checkpoint lands immediately before the only
        # place it was needed. A run died ~40 hours into that split on 2026-09-22 and the
        # cache held 7,927,889 pairs, 24.4% of the 32,553,730 priced: exactly the four
        # cheap repos and not one pydantic pair. The four survived and the expensive one
        # did not, which is the same failure the per-repo comment below was written to
        # prevent. So checkpoint on a clock as well, and bound the loss by time instead of
        # by whichever repo happens to be last.
        self.save_interval = save_interval
        self._unsaved = 0
        self._last_save = time.monotonic()
        self.checkpoints = 0
        if path is not None and path.exists():
            self._load(path)

    def _stamp(self) -> str:
        return f"{self.model_id}|{self.chunking.key}"

    def _load(self, path: Path) -> None:
        with np.load(path, allow_pickle=False) as handle:
            stamp = str(handle["__stamp__"])
            if stamp != self._stamp():
                raise ValueError(
                    f"pair cache at {path} was built by {stamp!r}, this run is "
                    f"{self._stamp()!r}. Logits from two cross-encoders are not on one "
                    f"scale; delete the file or pass a different --rerank-cache."
                )
            values = handle["scores"]
            self._scores = {
                # Accepts both dtypes on purpose. The keys are written as fixed-width
                # BYTES now and were written as UTF-32 before, and the difference is 4x
                # the file for an ASCII hex digest -- 4.3GB against 1.1GB at the mined
                # corpus's 32.5M pairs, rewritten after every repo. Reading both means
                # the change costs nothing instead of discarding a warm cache, and a
                # stamp bump here would abort the next run rather than migrate it.
                (k.decode() if isinstance(k, bytes) else str(k)): float(v)
                for k, v in zip(handle["keys"], values, strict=True)
            }

    def key_for(self, doc_chunk: str, code_chunk: str) -> str:
        # The stamp and both sides go through one hash with NUL separators, so a pair
        # cannot collide with a different split of the same concatenation.
        digest = hashlib.blake2b(
            f"{self._stamp()}\0{doc_chunk}\0{code_chunk}".encode("utf-8", "replace"),
            digest_size=16,
        )
        return digest.hexdigest()

    def get_or_score(
        self, pairs: list[tuple[str, str]], scorer: PairScorer
    ) -> list[float]:
        """Scores for many pairs, running the model only on what is not cached.

        Takes the whole query's pairs at once rather than one candidate's, because the
        model is 30-50x faster batched and a per-candidate call would spend the run
        inside 20 tiny forward passes per query.
        """
        keys = [self.key_for(doc, code) for doc, code in pairs]
        pending: list[tuple[str, str]] = []
        pending_keys: list[str] = []
        # Deduplicated within this call as well as against the store. Two candidates in
        # one head can be byte-identical files, and a doc chunk repeated across the
        # overlap boundary is common; nothing reaches `_scores` until the batch returns,
        # so without this those pairs are scored twice.
        queued: set[str] = set()
        for key, pair in zip(keys, pairs, strict=True):
            if key in self._scores or key in queued:
                self.hits += 1
                continue
            self.misses += 1
            queued.add(key)
            pending.append(pair)
            pending_keys.append(key)

        if pending:
            values = scorer.score(pending)
            for key, value in zip(pending_keys, values, strict=True):
                self._scores[key] = float(value)
            self._unsaved += len(pending)
            self.maybe_save()

        return [self._scores[key] for key in keys]

    def maybe_save(self) -> None:
        """Checkpoint if the clock has run out and there is anything new to write.

        Both conditions matter. Without the unsaved count a cache that is scoring nothing
        but hits -- which is what a resumed run does for hours -- would rewrite a 1.1GB
        file every interval for no gain.
        """
        if self.path is None or not self._unsaved:
            return
        if time.monotonic() - self._last_save < self.save_interval:
            return
        self.save()
        self.checkpoints += 1

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Two parallel arrays rather than one key per npz entry: the store reaches
        # millions of pairs, and npz writes one member file per array. `S32` rather than
        # `<U32` because a hex digest is ASCII and UTF-32 spends 128 bytes storing 32 of
        # them; at 32.5M pairs that is the difference between a 1.1GB file and a 4.3GB
        # one, and the file is rewritten after every repo.
        ordered = sorted(self._scores)
        keys = np.array([k.encode("ascii") for k in ordered], dtype="S32")
        values = np.array([self._scores[k] for k in ordered], dtype=np.float32)
        # Written to a sibling and renamed, because the save is no longer rare. At 32.5M
        # pairs the write takes ~26s and now happens every 15 minutes, so "killed during
        # the write" stops being a theoretical case -- and np.savez truncates in place,
        # which would turn a crash into the loss of the ENTIRE cache rather than of the
        # last interval. `os.replace` is atomic on the same filesystem, so a reader sees
        # either the previous complete cache or the new one. Passing an open handle rather
        # than the path also stops np.savez appending a second `.npz` to the temp name.
        tmp = self.path.with_suffix(self.path.suffix + ".partial")
        with tmp.open("wb") as handle:
            np.savez(
                handle, __stamp__=np.array(self._stamp()), keys=keys, scores=values
            )
        os.replace(tmp, self.path)
        self._unsaved = 0
        self._last_save = time.monotonic()


def default_pair_cache_path(model_id: str, chunking: Chunking, root: Path) -> Path:
    """Derived from the things a cache must not mix, exactly as the embedding one is."""
    slug = model_id.replace("/", "-").replace(":", "-")
    return root / f"{slug}-{chunking.size}-{chunking.overlap}.npz"


class CrossEncoderReranker:
    """Reorder a base ranker's top N. Everything past N keeps its base position.

    The head/tail split is not an optimisation, it is the measurement. Reranking the
    whole pool would make the arm a different retriever and its R@20 incomparable with
    the base's; reranking exactly the head the ceiling was measured on means R@20 is
    pinned and the only movable quantities are R@1, R@5, R@10 and MRR. A test asserts
    that invariance rather than trusting the argument.

    The base ranker receives `exclude` untouched, so an ablated run reranks the ABLATED
    head -- the alternative would rerank candidates the ablated baseline never proposed
    and quietly undo the ablation. The doc text this arm reads is redacted with the same
    `_redact` the dense arm uses, and carries the same caveat: deleting a token perturbs
    the sentence around it, so a wider gap here than `lexical`'s is not by itself
    evidence of more circularity.
    """

    def __init__(
        self,
        base: Ranker,
        scorer: PairScorer,
        cache: PairCache,
        code_texts: dict[str, str],
        chunking: Chunking = RERANK_CHUNKING,
        top_n: int = DEFAULT_TOP_N,
    ) -> None:
        if top_n < 2:
            raise ValueError(f"top_n must be at least 2 to reorder anything, got {top_n}")
        self._base = base
        self._scorer = scorer
        self._cache = cache
        self.chunking = chunking
        self.top_n = top_n
        # The name carries both the base and the cutoff, for the reason `lexical-tf`
        # carries its k1: two cutoffs over two bases are four experiments, and a results
        # table that collapsed them onto one row would be unreadable rather than wrong.
        self.name = f"rerank({base.name}@{top_n})"
        self._chunks = {
            path: chunk_text(text, chunking) for path, text in code_texts.items()
        }

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        order = self._base.rank(doc_path, doc_text, pool, exclude)
        head, tail = order[: self.top_n], order[self.top_n :]
        if len(head) < 2:
            return order
        doc_chunks = chunk_text(_redact(doc_text, exclude), self.chunking)
        if not doc_chunks:
            # An empty or fully-redacted doc. Returned in base order rather than
            # scored against nothing, which would rank the head alphabetically.
            return order

        pairs: list[tuple[str, str]] = []
        spans: dict[str, tuple[int, int]] = {}
        for path in head:
            code_chunks = self._chunks.get(path)
            if not code_chunks:
                continue
            start = len(pairs)
            pairs.extend((doc, code) for doc in doc_chunks for code in code_chunks)
            spans[path] = (start, len(pairs))
        if not pairs:
            return order

        values = self._cache.get_or_score(pairs, self._scorer)
        scores = {path: max(values[a:b]) for path, (a, b) in spans.items()}
        # An empty candidate file gets no score and sorts to the BACK of the head, not
        # to the front on a default of zero -- these logits go negative, so zero is a
        # high score here and a default of it would promote whitespace.
        reordered = sorted(head, key=lambda path: (-scores.get(path, -math.inf), path))
        return reordered + tail


class CrossEncoderScorer:
    """The real scorer. Imported lazily so the package works without torch."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANK_MODEL,
        device: str | None = None,
        batch_size: int = 128,
    ) -> None:
        from sentence_transformers import CrossEncoder

        self.model_id = model_name
        self.batch_size = batch_size
        self._model = CrossEncoder(model_name, device=device)

    def score(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        values = self._model.predict(
            pairs,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(values, dtype=np.float32).reshape(-1)
