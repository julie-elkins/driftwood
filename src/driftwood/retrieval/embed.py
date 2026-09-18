"""Dense retrieval, chunked because truncation was measured and rejected.

The obvious design -- embed each file, embed the doc, take a cosine -- does not
survive contact with the corpus. Code files here have a median of 7.9k characters
and a 90th percentile of 47k; 17% exceed roughly 8k tokens and the largest is 396k
characters. Documentation is no smaller: median 11.6k characters, and 94% of docs
exceed 2000. So neither side fits in a 512-token encoder, and the question of what
to do about it is the whole design.

Truncation was priced first, using the lexical ranker, because that costs nothing:

    MRR, ablated       full   8000 chars   2000 chars (~512 tokens)
    encode/httpx       0.67         0.51         0.45
    pallets/flask      0.66         0.52         0.36
    pydantic/pydantic  0.47         0.38         0.30
    psf/requests       0.37         0.25         0.20
    fastapi/fastapi    0.45         0.33         0.34

Roughly a third to a half of the retrieval signal is not in the first 512 tokens of
a code file. A dense arm that truncated would therefore be handicapped below the
free baseline before the model did any work, and would lose for a reason that has
nothing to do with embeddings. **So both sides are chunked and nothing is dropped.**

Scoring is max over (doc chunk, code chunk) pairs. Justified by what a positive
actually is in this dataset: the doc makes a claim in one section, about one
function, in one file. Mean-pooling either side would average that signal against
every unrelated paragraph in a 12k-character document and every unrelated method in
a 47k-character module -- diluting exactly the localised match the label is about.
The cost is that a file which merely *mentions* the right symbol in one line scores
as highly as one built around it; term frequency has the same weakness in `Lexical`
and it is recorded there too.

This is late interaction at chunk granularity rather than token granularity -- the
same reasoning as ColBERT's MaxSim, done coarsely because the vectors have to fit
in memory on a laptop.

Nothing here is imported unless the dense arm is asked for, so `driftwood mine` and
the free baselines keep working with no inference stack installed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from . import DEFAULT_MODEL
from .rankers import _stable_order

__all__ = [
    "Chunking",
    "Dense",
    "EmbeddingCache",
    "Encoder",
    "SentenceTransformerEncoder",
    "chunk_text",
    "default_cache_path",
]


class Encoder(Protocol):
    """Anything that turns strings into unit vectors.

    A Protocol rather than a class so the tests can stub it. The chunking, pooling
    and caching logic is where the bugs live, and none of it should need a 2GB
    download to exercise.
    """

    model_id: str
    dim: int

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return an (len(texts), dim) float32 array of L2-normalised rows."""


@dataclass(frozen=True)
class Chunking:
    """Window size and overlap, in characters.

    Characters rather than tokens because the chunker must not depend on the
    model's tokeniser -- otherwise swapping the model silently rechunks the corpus
    and the cache from the previous run becomes wrong rather than stale.

    `overlap` exists so a definition split across a boundary survives in one piece
    somewhere. Without it a class signature landing on a window edge is in neither
    chunk intact, and that failure is invisible in the score.
    """

    size: int = 1600
    overlap: int = 200

    def __post_init__(self) -> None:
        if self.overlap >= self.size:
            raise ValueError("overlap must be smaller than size, or chunking cannot advance")

    @property
    def key(self) -> str:
        return f"{self.size}:{self.overlap}"


def chunk_text(text: str, chunking: Chunking) -> list[str]:
    """Split into overlapping windows, covering the whole string.

    Deliberately not sentence- or syntax-aware. tree-sitter chunking on definition
    boundaries is the better answer and is on the roadmap, but it is also a second
    variable: introducing it at the same time as the embedding model would make a
    change in the score unattributable to either.
    """
    if not text.strip():
        return []
    step = chunking.size - chunking.overlap
    out = [text[i : i + chunking.size] for i in range(0, len(text), step)]
    # The final window can be pure overlap when len(text) lands just past a step
    # boundary; it carries no new characters, so drop it.
    if len(out) > 1 and len(out[-1]) <= chunking.overlap:
        out.pop()
    return out


class EmbeddingCache:
    """Chunk vectors keyed by content hash, persisted between runs.

    Keyed by the file's *contents*, not its path: a query is scored on the tree its
    judgement was made at, there are 629 distinct trees across the corpus, and most
    files are byte-identical between them. 8148 unique code blobs stand behind far
    more (path, sha) pairs. A path-keyed cache would miss every one of those hits.

    The key also folds in the model id and the chunking parameters, and the file
    stores them alongside the vectors. Changing the chunk size does not change the
    *shape* of anything, so a cache that ignored it would keep serving vectors built
    under the old windows and the run would look clean. On a mismatch this refuses
    to load rather than mixing two encodings -- the same reason a store bumps its
    schema for a meaning change that touches no column.
    """

    def __init__(self, path: Path | None, model_id: str, chunking: Chunking) -> None:
        self.path = path
        self.model_id = model_id
        self.chunking = chunking
        self._vectors: dict[str, np.ndarray] = {}
        self.hits = 0
        self.misses = 0
        if path is not None and path.exists():
            self._load(path)

    def _stamp(self) -> str:
        return f"{self.model_id}|{self.chunking.key}"

    def _load(self, path: Path) -> None:
        with np.load(path, allow_pickle=False) as handle:
            stamp = str(handle["__stamp__"])
            if stamp != self._stamp():
                raise ValueError(
                    f"embedding cache at {path} was built by {stamp!r}, this run is "
                    f"{self._stamp()!r}. Vectors from two encodings are not comparable; "
                    f"delete the file or pass a different --embed-cache."
                )
            self._vectors = {k: handle[k] for k in handle.files if k != "__stamp__"}

    def key_for(self, text: str) -> str:
        digest = hashlib.blake2b(
            f"{self._stamp()}\0{text}".encode("utf-8", "replace"), digest_size=16
        )
        return digest.hexdigest()

    def get_or_encode(self, texts: dict[str, str], encoder: Encoder) -> dict[str, np.ndarray]:
        """Chunk vectors for many documents, encoding only what is not cached."""
        keys = {name: self.key_for(text) for name, text in texts.items()}
        pending: list[str] = []
        pending_of: list[str] = []
        # Keys queued during *this* call. Nothing reaches `_vectors` until the batch
        # is encoded, so without this a blob appearing at two paths in one call
        # misses twice: encoded twice, and its rows stacked twice into the matrix.
        # Max-pooling hides the duplication, which is what makes it worth a test.
        queued: set[str] = set()
        for name, text in texts.items():
            key = keys[name]
            if key in self._vectors or key in queued:
                self.hits += 1
                continue
            self.misses += 1
            queued.add(key)
            pieces = chunk_text(text, self.chunking)
            if not pieces:
                # An empty or whitespace-only file. Stored as a zero-row array so it
                # is a cache *hit* next time rather than being re-chunked forever.
                self._vectors[key] = np.zeros((0, encoder.dim), dtype=np.float32)
                continue
            for piece in pieces:
                pending.append(piece)
                pending_of.append(key)

        if pending:
            vectors = encoder.encode(pending)
            grouped: dict[str, list[np.ndarray]] = {}
            for key, row in zip(pending_of, vectors, strict=True):
                grouped.setdefault(key, []).append(row)
            for key, rows in grouped.items():
                self._vectors[key] = np.vstack(rows).astype(np.float32, copy=False)

        return {name: self._vectors[keys[name]] for name in texts}

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(self._vectors)
        payload["__stamp__"] = np.array(self._stamp())
        np.savez(self.path, **payload)


def default_cache_path(model_id: str, chunking: Chunking, root: Path) -> Path:
    """A cache path derived from the things a cache must not mix.

    Deriving it rather than defaulting to one filename means two configurations get
    two files instead of colliding on one. The stamp check would catch the collision
    and refuse, which is safe but useless: it makes changing the chunk size an error
    the user has to clear by hand, so the tempting fix is to delete the cache and
    re-encode the corpus every time. Both runs keeping their own vectors is the
    version where the safe thing is also the cheap thing.
    """
    slug = model_id.replace("/", "-").replace(":", "-")
    return root / f"{slug}-{chunking.size}-{chunking.overlap}.npz"


def _redact(text: str, tokens: frozenset[str]) -> str:
    """Remove the mined evidence tokens from the doc text.

    The ablation is defined on tokens, and `Lexical` implements it as exact set
    subtraction. A dense model consumes text, so the only available analogue is to
    take the words out -- which is **not the same operation**. Deleting
    `HTTPTransport` from a sentence also perturbs the sentence around it, so the
    dense ablation is a strictly harsher intervention than the lexical one, and a
    larger ablated-vs-unablated gap on the dense arm is not by itself evidence of
    more circularity. Stated here because the two gaps will be printed side by side
    and the comparison invites exactly that mistake.
    """
    if not tokens:
        return text
    # Longest first, so `ver:0.14` is not half-consumed by a shorter token, and
    # match on non-word boundaries so `create_user` is found inside `create_user()`.
    ordered = sorted(tokens, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(t) for t in ordered), re.IGNORECASE)
    return pattern.sub(" ", text)


@dataclass
class Dense:
    """Rank by max cosine over (doc chunk, code chunk) pairs.

    Holds the pool's chunk vectors as one matrix with an index of which rows belong
    to which file, so a query is one matrix multiply rather than a Python loop over
    candidates. At a 685-file pool that is the difference between seconds and
    minutes per tree.
    """

    name: str = "dense"

    def __init__(
        self,
        encoder: Encoder,
        code_texts: dict[str, str],
        cache: EmbeddingCache,
        name: str = "dense",
    ) -> None:
        self.name = name
        self._encoder = encoder
        self._cache = cache
        per_file = cache.get_or_encode(code_texts, encoder)
        blocks: list[np.ndarray] = []
        self._owners: list[str] = []
        self._offsets: list[int] = []
        cursor = 0
        for path in sorted(per_file):
            vectors = per_file[path]
            if vectors.shape[0] == 0:
                # No chunks at all. Left out of the matrix and therefore scoreless,
                # which `_stable_order` puts in the deterministic tail -- not
                # silently at rank 1 with a zero vector's meaningless cosine.
                continue
            blocks.append(vectors)
            self._owners.append(path)
            self._offsets.append(cursor)
            cursor += vectors.shape[0]
        self._matrix = (
            np.vstack(blocks).astype(np.float32, copy=False)
            if blocks
            else np.zeros((0, encoder.dim), dtype=np.float32)
        )

    def rank(
        self,
        doc_path: str,
        doc_text: str,
        pool: list[str],
        exclude: frozenset[str] = frozenset(),
    ) -> list[str]:
        if self._matrix.shape[0] == 0:
            return _stable_order({}, pool)
        text = _redact(doc_text, exclude)
        doc_vectors = self._cache.get_or_encode({doc_path: text}, self._encoder)[doc_path]
        if doc_vectors.shape[0] == 0:
            return _stable_order({}, pool)

        # (doc chunks x code chunks), then best doc chunk per code chunk, then best
        # code chunk per file. Two maxes rather than a mean, for the reason in the
        # module docstring.
        similarity = doc_vectors @ self._matrix.T
        best_per_chunk = similarity.max(axis=0)
        best_per_file = np.maximum.reduceat(best_per_chunk, self._offsets)

        in_pool = set(pool)
        scores = {
            path: float(score)
            for path, score in zip(self._owners, best_per_file, strict=True)
            if path in in_pool
        }
        return _stable_order(scores, pool)


class SentenceTransformerEncoder:
    """The real encoder. Imported lazily so the package works without torch."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        batch_size: int = 64,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_id = model_name
        self.batch_size = batch_size
        self._model = SentenceTransformer(model_name, device=device)
        # Renamed in sentence-transformers 5; the old name still works but warns, and
        # the warning would be printed once per run forever. New name first so this
        # keeps working when the old one goes.
        getter = getattr(
            self._model,
            "get_embedding_dimension",
            None,
        ) or self._model.get_sentence_embedding_dimension
        self.dim = int(getter())

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,  # so a dot product is a cosine
            show_progress_bar=False,
        )
        return vectors.astype(np.float32, copy=False)
