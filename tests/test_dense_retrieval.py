"""The dense arm, tested where chunking and caching can lie.

None of these tests loads a model. The embedding model is the part least likely to
be wrong and the most expensive to exercise; the chunking, the two-level pooling and
the cache key are the parts that fail *quietly* -- each producing a plausible score
that is simply measuring the wrong thing.

The stub encoder hashes words into buckets, so cosine similarity tracks word overlap
and an assertion about ranking is an assertion about the pooling logic rather than
about a model's taste.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from driftwood.retrieval.embed import (  # noqa: E402
    Chunking,
    Dense,
    EmbeddingCache,
    _redact,
    chunk_text,
    default_cache_path,
)

WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


class HashEncoder:
    """Deterministic bag-of-words vectors. Similarity == word overlap.

    Buckets come from blake2b, not from the built-in `hash()`. String hashing in
    CPython is salted per process, so a `hash()`-based stub puts words in different
    buckets on every run: collisions come and go, and a ranking assertion passes or
    fails by luck of the seed. That is the same defect as the ranker's zero-score
    tail depending on `ls-tree` order, one layer up -- a test harness that cannot
    reproduce itself cannot witness a regression.

    256 buckets rather than 64 for the same reason: fewer accidental collisions
    between the target identifier and the filler words in these fixtures.
    """

    model_id = "stub-hash-v1"
    dim = 256

    def __init__(self) -> None:
        self.calls = 0
        self.texts_seen: list[str] = []

    def _bucket(self, word: str) -> int:
        digest = hashlib.blake2b(word.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dim

    def encode(self, texts: list[str]) -> np.ndarray:
        self.calls += 1
        self.texts_seen.extend(texts)
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in WORD.findall(text.lower()):
                out[row, self._bucket(word)] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return out / norms


class TestChunkingLosesNothing:
    def test_every_character_survives_somewhere(self):
        """The whole point of chunking over truncating. If the concatenation of
        chunks did not cover the input, the dense arm would be a truncating arm
        with extra steps and the measured truncation cost would apply to it."""
        text = "".join(f"line {i}\n" for i in range(500))
        pieces = chunk_text(text, Chunking(size=100, overlap=20))

        assert len(pieces) > 1
        rebuilt = pieces[0]
        for piece in pieces[1:]:
            rebuilt += piece[20:]  # drop the overlap that was already counted
        assert rebuilt == text

    def test_a_definition_on_a_boundary_survives_intact_in_one_chunk(self):
        """Why overlap exists. Without it a signature landing on a window edge is
        in neither chunk whole, and the loss is invisible in the score."""
        target = "def create_user(name, email):"
        text = "x" * 95 + target + "y" * 200
        pieces = chunk_text(text, Chunking(size=100, overlap=40))

        assert any(target in piece for piece in pieces)

    def test_overlap_must_be_smaller_than_the_window(self):
        """Otherwise the chunker cannot advance and would hang or loop."""
        with pytest.raises(ValueError):
            Chunking(size=100, overlap=100)

    def test_whitespace_only_content_yields_no_chunks(self):
        assert chunk_text("   \n\t\n", Chunking()) == []

    def test_a_trailing_pure_overlap_window_is_dropped(self):
        """A final window carrying no new characters is a duplicate vector: it costs
        encoding time and can only ever tie with the chunk it repeats.

        90 characters at size 100 / step 80: the second window would be text[80:90],
        all ten of which the first window already covered.
        """
        pieces = chunk_text("a" * 90, Chunking(size=100, overlap=20))

        assert len(pieces) == 1

    def test_a_trailing_window_with_even_one_new_character_is_kept(self):
        """The complement, and the distinction the drop rule turns on. 105 characters
        at size 100 leaves 5 characters that live in no other window; dropping that
        window to look tidy would silently truncate the file."""
        pieces = chunk_text("a" * 105, Chunking(size=100, overlap=20))

        assert len(pieces) == 2
        assert sum(len(p) for p in pieces) > 105  # overlapping, so strictly greater


class TestPoolingFindsSignalAnywhereInTheFile:
    def test_a_match_at_the_end_of_a_long_file_still_ranks_first(self):
        """This is the measured finding turned into a regression test.

        Truncation to the first 512 tokens cost 30-45% of MRR on this corpus. A
        file whose only relevant content is in its last 200 characters is exactly
        the case that produced that loss, and max-pooling over chunks is what fixes
        it. If someone later 'optimises' this by embedding only the head, this test
        is what fails.
        """
        filler = "unrelated boilerplate padding " * 200
        code = {
            "src/late.py": filler + "\ndef zeta_handler(payload): return payload\n",
            "src/decoy.py": filler + "\ndef alpha_widget(payload): return payload\n",
        }
        encoder = HashEncoder()
        ranker = Dense(encoder, code, EmbeddingCache(None, encoder.model_id, Chunking()))

        ranked = ranker.rank("d.md", "See `zeta_handler` for details.", sorted(code))

        assert ranked[0] == "src/late.py"

    def test_the_score_is_a_max_over_files_not_over_chunks(self):
        """`np.maximum.reduceat` with the wrong offsets silently returns per-chunk
        maxima, which reorders the pool by chunk count rather than by relevance --
        and every metric still computes."""
        code = {
            "src/one_chunk.py": "def zeta_handler(): pass",
            "src/many_chunks.py": "filler text here " * 400,
        }
        encoder = HashEncoder()
        ranker = Dense(encoder, code, EmbeddingCache(None, encoder.model_id, Chunking(size=100, overlap=20)))

        ranked = ranker.rank("d.md", "About `zeta_handler`.", sorted(code))

        # The long file has many chunks and the short one has a single strong chunk.
        assert ranked[0] == "src/one_chunk.py"

    def test_an_empty_file_lands_in_the_deterministic_tail_not_at_rank_one(self):
        """A zero vector's cosine with anything is 0, which can outrank a genuinely
        negative similarity. Excluding chunkless files from the matrix is what keeps
        an empty `__init__.py` out of first place."""
        code = {"src/real.py": "def zeta_handler(): pass", "src/empty.py": "   "}
        encoder = HashEncoder()
        ranker = Dense(encoder, code, EmbeddingCache(None, encoder.model_id, Chunking()))

        ranked = ranker.rank("d.md", "About `zeta_handler`.", sorted(code))

        assert ranked == ["src/real.py", "src/empty.py"]

    def test_a_pool_entry_with_no_vectors_is_still_returned(self):
        """Ranking must be a permutation of the pool. Dropping a candidate would
        shrink the denominator and inflate recall."""
        code = {"src/real.py": "def zeta_handler(): pass"}
        encoder = HashEncoder()
        ranker = Dense(encoder, code, EmbeddingCache(None, encoder.model_id, Chunking()))

        pool = ["src/real.py", "src/never_read.py"]
        assert sorted(ranker.rank("d.md", "zeta_handler", pool)) == sorted(pool)

    def test_ties_do_not_depend_on_pool_order(self):
        code = {"src/a.py": "identical body", "src/b.py": "identical body"}
        encoder = HashEncoder()
        cache = EmbeddingCache(None, encoder.model_id, Chunking())
        ranker = Dense(encoder, code, cache)

        pool = ["src/a.py", "src/b.py"]
        assert ranker.rank("d.md", "nothing", pool) == ranker.rank(
            "d.md", "nothing", list(reversed(pool))
        )


class TestTheCacheIsKeyedOnContent:
    def test_the_same_content_at_two_paths_is_encoded_once(self):
        """629 distinct trees stand behind 8148 unique blobs. A path-keyed cache
        would miss nearly every hit and the run would take hours instead of minutes."""
        encoder = HashEncoder()
        cache = EmbeddingCache(None, encoder.model_id, Chunking())

        cache.get_or_encode({"a.py": "same body here", "b.py": "same body here"}, encoder)

        assert cache.misses == 1 and cache.hits == 1

    def test_a_second_call_with_seen_content_encodes_nothing(self):
        encoder = HashEncoder()
        cache = EmbeddingCache(None, encoder.model_id, Chunking())
        cache.get_or_encode({"a.py": "body"}, encoder)
        calls_before = encoder.calls

        cache.get_or_encode({"a.py": "body"}, encoder)

        assert encoder.calls == calls_before

    def test_an_empty_file_is_cached_rather_than_rechunked_forever(self):
        encoder = HashEncoder()
        cache = EmbeddingCache(None, encoder.model_id, Chunking())
        cache.get_or_encode({"e.py": "  "}, encoder)
        cache.get_or_encode({"e.py": "  "}, encoder)

        assert cache.hits == 1

    def test_changing_the_chunk_size_changes_the_key(self):
        """The trap this guards. Chunk size changes no shape and no column, so a
        cache that ignored it would keep serving vectors built under the old windows
        and the run would look entirely clean."""
        encoder = HashEncoder()
        small = EmbeddingCache(None, encoder.model_id, Chunking(size=800, overlap=100))
        large = EmbeddingCache(None, encoder.model_id, Chunking(size=1600, overlap=200))

        assert small.key_for("identical text") != large.key_for("identical text")

    def test_changing_the_model_changes_the_key(self):
        encoder = HashEncoder()
        a = EmbeddingCache(None, encoder.model_id, Chunking())
        b = EmbeddingCache(None, "some-other-model", Chunking())

        assert a.key_for("identical text") != b.key_for("identical text")

    def test_a_saved_cache_round_trips(self, tmp_path):
        encoder = HashEncoder()
        path = tmp_path / "vectors.npz"
        first = EmbeddingCache(path, encoder.model_id, Chunking())
        first.get_or_encode({"a.py": "def zeta(): pass"}, encoder)
        first.save()

        second = EmbeddingCache(path, encoder.model_id, Chunking())
        second.get_or_encode({"a.py": "def zeta(): pass"}, encoder)

        assert second.hits == 1 and second.misses == 0

    def test_a_cache_from_a_different_model_refuses_to_load(self, tmp_path):
        """Mixing two encodings produces cosines between unrelated vector spaces --
        numbers that are finite, plausible and meaningless. Refusing is the only
        safe behaviour, because there is no way to detect it downstream."""
        encoder = HashEncoder()
        path = tmp_path / "vectors.npz"
        built = EmbeddingCache(path, encoder.model_id, Chunking())
        built.get_or_encode({"a.py": "body"}, encoder)
        built.save()

        with pytest.raises(ValueError, match="not comparable|was built by"):
            EmbeddingCache(path, "a-different-model", Chunking())

    def test_a_cache_from_different_chunking_refuses_to_load(self, tmp_path):
        encoder = HashEncoder()
        path = tmp_path / "vectors.npz"
        built = EmbeddingCache(path, encoder.model_id, Chunking(size=800, overlap=100))
        built.get_or_encode({"a.py": "body"}, encoder)
        built.save()

        with pytest.raises(ValueError):
            EmbeddingCache(path, encoder.model_id, Chunking(size=1600, overlap=200))


class TestTheDerivedCachePathSeparatesConfigurations:
    """The stamp check makes a collision *safe*; a derived path makes it not happen.

    Sharing one filename between two configurations means every switch back and forth
    is a refusal the user clears by deleting the cache and re-encoding 8148 blobs --
    so the safe design would train them to bypass it.
    """

    def test_two_models_get_two_files(self):
        root = Path(".cache/embeddings")
        assert default_cache_path("BAAI/bge-small-en-v1.5", Chunking(), root) != (
            default_cache_path("BAAI/bge-m3", Chunking(), root)
        )

    def test_two_chunkings_get_two_files(self):
        root = Path(".cache/embeddings")
        assert default_cache_path("m", Chunking(size=800, overlap=100), root) != (
            default_cache_path("m", Chunking(size=1600, overlap=200), root)
        )

    def test_the_model_id_is_flattened_into_one_path_component(self):
        """A model id contains a slash. Left in, it would silently create a `BAAI/`
        directory and the derived path would depend on the id's shape."""
        path = default_cache_path("BAAI/bge-small-en-v1.5", Chunking(), Path("root"))

        assert path.parent == Path("root")
        assert "/" not in path.name

    def test_the_same_configuration_is_stable(self):
        root = Path(".cache/embeddings")
        assert default_cache_path("m", Chunking(), root) == default_cache_path(
            "m", Chunking(), root
        )


class TestTheAblationRedactsText:
    def test_the_evidence_token_is_gone_from_what_gets_encoded(self):
        assert "httptransport" not in _redact("See HTTPTransport now.", frozenset({"httptransport"})).lower()

    def test_redaction_is_case_insensitive(self):
        """Tokens are mined lowercased; the doc says `HTTPTransport`. A
        case-sensitive strike would remove nothing and the ablated arm would
        silently equal the unablated one -- reading as 'no circularity'."""
        out = _redact("The HTTPTransport class", frozenset({"httptransport"}))

        assert "HTTPTransport" not in out

    def test_a_token_inside_a_call_expression_is_found(self):
        out = _redact("call create_user(name)", frozenset({"create_user"}))

        assert "create_user" not in out

    def test_longer_tokens_are_struck_before_shorter_ones(self):
        """`ver:0.14` must not be left as `:0.14` by an earlier strike of `ver`."""
        out = _redact("supports ver:0.14 only", frozenset({"ver", "ver:0.14"}))

        assert "0.14" not in out

    def test_an_empty_exclude_set_leaves_the_text_untouched(self):
        text = "unchanged text"
        assert _redact(text, frozenset()) == text

    def test_redaction_changes_the_ranking(self):
        code = {
            "src/transport.py": "class zeta_handler: pass",
            "src/other.py": "class alpha_widget: pass",
        }
        encoder = HashEncoder()
        ranker = Dense(encoder, code, EmbeddingCache(None, encoder.model_id, Chunking()))
        pool = sorted(code)

        assert ranker.rank("d.md", "About zeta_handler.", pool)[0] == "src/transport.py"
        blinded = ranker.rank("d.md", "About zeta_handler.", pool, frozenset({"zeta_handler"}))
        assert blinded == sorted(pool)
