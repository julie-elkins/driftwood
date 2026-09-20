"""The rerank arm, tested where a reranker quietly stops being one.

No model is loaded. The cross-encoder is the part least likely to be wrong and the most
expensive to exercise; the head/tail split, the pair cache and the pooling are the parts
that fail *plausibly* -- each producing a table of numbers that is measuring something
other than what the row is labelled.

The two failures worth the most here are the ones that look like success:

- **Reranking more than the head.** Then R@N is no longer the base's and the arm is a
  different retriever, so the gain it prints is not comparable with the row above it.
- **A default score of zero.** These are logits and they go negative, so zero is a HIGH
  score -- a candidate that got no score at all would be promoted over every real one.

The stub scorer returns word overlap minus five, so its outputs straddle zero for the
same reason a real one's do.
"""

from __future__ import annotations

import re

import pytest

np = pytest.importorskip("numpy")

from driftwood.retrieval import evaluate  # noqa: E402
from driftwood.retrieval.dataset import Query, RepoSplit  # noqa: E402
from driftwood.retrieval.embed import Chunking  # noqa: E402
from driftwood.retrieval.rankers import Lexical  # noqa: E402
from driftwood.retrieval.rerank import (  # noqa: E402
    RERANK_CHUNKING,
    CrossEncoderReranker,
    PairCache,
    default_pair_cache_path,
)

WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


class OverlapScorer:
    """Word overlap between the two sides, shifted negative. Counts its calls.

    Shifted by -5 so the common case is a negative score. A stub whose every output was
    positive would let a zero default for an unscored candidate pass, and that default
    is one of the two bugs this file exists to catch.
    """

    model_id = "stub-cross-v1"

    def __init__(self) -> None:
        self.calls = 0
        self.pairs_seen: list[tuple[str, str]] = []

    def score(self, pairs):
        self.calls += 1
        self.pairs_seen.extend(pairs)
        out = []
        for doc, code in pairs:
            shared = set(WORD.findall(doc.lower())) & set(WORD.findall(code.lower()))
            out.append(float(len(shared)) - 5.0)
        return np.asarray(out, dtype=np.float32)


class FixedOrder:
    """A base ranker that returns a pinned order, and records what it was asked.

    Pinned rather than computed, because every assertion here is about which slice of
    the base order the reranker touched. A real base ranker would make a failure
    ambiguous between the two layers.
    """

    name = "fixed"

    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.excludes: list[frozenset[str]] = []

    def rank(self, doc_path, doc_text, pool, exclude=frozenset()):
        self.excludes.append(exclude)
        return [path for path in self.order if path in set(pool)]


def _pool(n: int) -> list[str]:
    return [f"src/m{i:02d}.py" for i in range(n)]


def _texts(pool: list[str], target: str, needle: str) -> dict[str, str]:
    """Filler for every file, and the needle in exactly one of them."""
    return {
        path: (f"def helper_{path[-5:-3]}(): return None\n" * 4)
        + (f"\ndef {needle}(): return 1\n" if path == target else "")
        for path in pool
    }


def _cache(chunking: Chunking = RERANK_CHUNKING) -> PairCache:
    return PairCache(None, "stub-cross-v1", chunking)


class TestOnlyTheHeadMoves:
    """The head/tail split is the measurement, not an optimisation. If it slips, R@N
    stops being the base ranker's number and the arm's row becomes incomparable with
    the row directly above it -- which is the only row it is meaningful against."""

    def test_recall_at_the_cutoff_is_the_base_rankers_by_construction(self):
        pool = _pool(30)
        base = FixedOrder(pool)
        scorer = OverlapScorer()
        ranker = CrossEncoderReranker(
            base, scorer, _cache(), _texts(pool, "src/m25.py", "transport"), top_n=10
        )

        order = ranker.rank("d.md", "About the transport helper_00.", pool)

        # Same members in the first 10 and in the tail, whatever the scorer said.
        assert set(order[:10]) == set(pool[:10])
        assert order[10:] == pool[10:]

    def test_the_tail_keeps_its_base_order_exactly(self):
        pool = _pool(12)
        # A base order that is NOT sorted, so "kept base order" and "sorted by path"
        # are different strings and the assertion can tell them apart.
        shuffled = [pool[i] for i in (7, 2, 11, 0, 5, 9, 1, 3, 10, 4, 8, 6)]
        base = FixedOrder(shuffled)
        ranker = CrossEncoderReranker(
            base, OverlapScorer(), _cache(), _texts(pool, "src/m05.py", "transport"),
            top_n=4,
        )

        order = ranker.rank("d.md", "About the transport.", pool)

        assert order[4:] == shuffled[4:]

    def test_an_adversarial_scorer_still_cannot_change_recall_at_the_cutoff(self):
        """The invariance is structural, so it must hold for a scorer that is actively
        wrong rather than merely for one that is roughly right."""

        class Inverted(OverlapScorer):
            def score(self, pairs):
                return -super().score(pairs)

        pool = _pool(30)
        ranker = CrossEncoderReranker(
            FixedOrder(pool), Inverted(), _cache(),
            _texts(pool, "src/m03.py", "transport"), top_n=10,
        )

        order = ranker.rank("d.md", "About the transport.", pool)

        assert set(order[:10]) == set(pool[:10])

    def test_a_correct_answer_inside_the_head_can_reach_rank_one(self):
        """The other half of the contract: the arm must actually be able to do
        something, or the invariance test above would pass on a no-op."""
        pool = _pool(30)
        ranker = CrossEncoderReranker(
            FixedOrder(pool), OverlapScorer(), _cache(),
            _texts(pool, "src/m19.py", "transport"), top_n=20,
        )

        order = ranker.rank("d.md", "The transport layer.", pool)

        assert order[0] == "src/m19.py"

    def test_a_correct_answer_outside_the_head_is_unreachable(self):
        """The ceiling, as an assertion. 13% of queries are missed by every arm at
        k=10, and no reranker recovers one of those -- so a gain predicted from a
        recall figure that includes them is predicted from a number that is not
        available."""
        pool = _pool(30)
        ranker = CrossEncoderReranker(
            FixedOrder(pool), OverlapScorer(), _cache(),
            _texts(pool, "src/m25.py", "transport"), top_n=20,
        )

        order = ranker.rank("d.md", "The transport layer.", pool)

        assert order.index("src/m25.py") == 25, "the tail is untouched, gain or not"

    def test_a_cutoff_below_two_is_refused_rather_than_being_a_silent_no_op(self):
        with pytest.raises(ValueError, match="top_n"):
            CrossEncoderReranker(
                FixedOrder(["src/a.py"]), OverlapScorer(), _cache(),
                {"src/a.py": "x"}, top_n=1,
            )

    def test_a_pool_smaller_than_the_cutoff_is_reordered_whole(self):
        """The 2c corpus's pools are 22-35 files against a cutoff of 20, and the mined
        corpus has trees smaller than 20. Neither may crash or silently skip."""
        pool = _pool(3)
        ranker = CrossEncoderReranker(
            FixedOrder(pool), OverlapScorer(), _cache(),
            _texts(pool, "src/m02.py", "transport"), top_n=20,
        )

        order = ranker.rank("d.md", "The transport layer.", pool)

        assert order[0] == "src/m02.py"
        assert sorted(order) == sorted(pool)


class TestScoresAreLogitsNotSimilarities:
    def test_an_unscoreable_candidate_sorts_to_the_back_of_the_head(self):
        """A whitespace-only file yields no chunks and therefore no score. On a default
        of zero it would outrank every real candidate, because these scores go negative
        -- and it would do so at rank 1, which reads as the reranker working."""
        pool = _pool(6)
        texts = _texts(pool, "src/m04.py", "transport")
        texts["src/m00.py"] = "   \n\n  "
        ranker = CrossEncoderReranker(
            FixedOrder(pool), OverlapScorer(), _cache(), texts, top_n=6
        )

        order = ranker.rank("d.md", "The transport layer.", pool)

        assert order[0] == "src/m04.py"
        assert order[-1] == "src/m00.py"

    def test_a_doc_with_no_text_left_falls_back_to_base_order(self):
        """A fully-redacted doc must not be scored against nothing, which would leave
        the head sorted alphabetically and call that a reranking."""
        pool = _pool(5)
        shuffled = [pool[i] for i in (3, 1, 4, 0, 2)]
        ranker = CrossEncoderReranker(
            FixedOrder(shuffled), OverlapScorer(), _cache(),
            _texts(pool, "src/m02.py", "transport"), top_n=5,
        )

        assert ranker.rank("d.md", "   ", pool) == shuffled


class TestTheAblationReachesTheBaseRanker:
    def test_the_base_ranker_is_ablated_too_so_the_head_is_the_ablated_head(self):
        """Reranking the UNablated head under an ablated row would hand the model
        candidates the ablated baseline never proposed, and quietly undo the one
        measurement that bounds circularity on this corpus."""
        pool = _pool(8)
        base = FixedOrder(pool)
        ranker = CrossEncoderReranker(
            base, OverlapScorer(), _cache(), _texts(pool, "src/m03.py", "transport"),
            top_n=4,
        )

        ranker.rank("d.md", "The transport layer.", pool, frozenset({"transport"}))

        assert base.excludes == [frozenset({"transport"})]

    def test_the_evidence_token_is_gone_from_what_the_model_reads(self):
        pool = _pool(4)
        scorer = OverlapScorer()
        ranker = CrossEncoderReranker(
            FixedOrder(pool), scorer, _cache(), _texts(pool, "src/m01.py", "transport"),
            top_n=4,
        )

        ranker.rank("d.md", "The transport layer.", pool, frozenset({"transport"}))

        doc_sides = {doc for doc, _ in scorer.pairs_seen}
        assert doc_sides, "the model saw nothing at all"
        assert not any("transport" in doc.lower() for doc in doc_sides)


class TestTheChunkingFitsOnePairInOneWindow:
    def test_a_pair_of_windows_is_smaller_than_the_dense_arms_single_window(self):
        """A cross-encoder reads BOTH sides inside one 512-token window; the dense arm
        gives each side its own. Reusing the dense arm's 1600 here would truncate
        roughly two thirds of every pair -- the exact failure the dense arm was designed
        around, reintroduced by making the two numbers match."""
        pair_chars = RERANK_CHUNKING.size * 2
        assert pair_chars <= 2000, "512 tokens is roughly 2000 characters of code"
        assert Chunking().size * 2 > 2000, "which the dense arm's chunking would exceed"

    def test_the_overlap_survives_the_smaller_window(self):
        assert 0 < RERANK_CHUNKING.overlap < RERANK_CHUNKING.size


class TestThePairCacheIsKeyedOnBothSides:
    def test_the_same_pair_is_scored_once_across_two_calls(self):
        cache, scorer = _cache(), OverlapScorer()
        pairs = [("doc a", "code a"), ("doc b", "code b")]

        first = cache.get_or_score(pairs, scorer)
        second = cache.get_or_score(pairs, scorer)

        assert first == second
        assert scorer.calls == 1, "the second call should have scored nothing"
        assert cache.hits == 2 and cache.misses == 2

    def test_a_pair_repeated_within_one_call_is_scored_once(self):
        """Two byte-identical files in one head, or a doc chunk that recurs across the
        overlap boundary. Nothing reaches the store until the batch returns, so without
        an in-flight set these are scored twice and the reported cost is wrong."""
        cache, scorer = _cache(), OverlapScorer()

        values = cache.get_or_score([("d", "c"), ("d", "c"), ("d", "c")], scorer)

        assert len(scorer.pairs_seen) == 1
        assert values[0] == values[1] == values[2]

    def test_the_two_sides_are_not_interchangeable(self):
        """The doc side and the code side are different arguments to a cross-encoder,
        which is asymmetric. A key built by concatenating them without separation would
        collide these two pairs, and each would be served the other's score."""
        cache = _cache()

        assert cache.key_for("ab", "c") != cache.key_for("a", "bc")
        assert cache.key_for("doc", "code") != cache.key_for("code", "doc")

    def test_changing_the_model_changes_every_key(self):
        one = PairCache(None, "model-a", RERANK_CHUNKING)
        two = PairCache(None, "model-b", RERANK_CHUNKING)

        assert one.key_for("d", "c") != two.key_for("d", "c")

    def test_changing_the_chunking_changes_every_key(self):
        one = PairCache(None, "model-a", Chunking(800, 100))
        two = PairCache(None, "model-a", Chunking(400, 100))

        assert one.key_for("d", "c") != two.key_for("d", "c")

    def test_a_saved_cache_round_trips(self, tmp_path):
        path = tmp_path / "pairs.npz"
        scorer = OverlapScorer()
        written = PairCache(path, "stub-cross-v1", RERANK_CHUNKING)
        expected = written.get_or_score([("doc one", "doc two"), ("x", "y")], scorer)
        written.save()

        reloaded = PairCache(path, "stub-cross-v1", RERANK_CHUNKING)
        again = reloaded.get_or_score([("doc one", "doc two"), ("x", "y")], scorer)

        assert again == pytest.approx(expected)
        assert scorer.calls == 1, "a reloaded cache should not re-score anything"

    def test_a_cache_from_a_different_model_refuses_to_load(self, tmp_path):
        """Logits from two cross-encoders are not on one scale, so mixing them produces
        an arbitrary ranking from a run that looks clean."""
        path = tmp_path / "pairs.npz"
        written = PairCache(path, "stub-cross-v1", RERANK_CHUNKING)
        written.get_or_score([("d", "c")], OverlapScorer())
        written.save()

        with pytest.raises(ValueError, match="stub-cross-v1"):
            PairCache(path, "other-model", RERANK_CHUNKING)

    def test_a_cache_from_different_chunking_refuses_to_load(self, tmp_path):
        path = tmp_path / "pairs.npz"
        written = PairCache(path, "stub-cross-v1", Chunking(800, 100))
        written.get_or_score([("d", "c")], OverlapScorer())
        written.save()

        with pytest.raises(ValueError, match="800:100"):
            PairCache(path, "stub-cross-v1", Chunking(400, 100))

    def test_a_cache_written_in_the_old_utf32_key_dtype_still_loads(self, tmp_path):
        """The key dtype changed from `<U32` to `S32` to stop a hex digest costing 128
        bytes. Keys that failed to decode would not RAISE -- they would miss, and the
        run would silently re-score a warm cache at four times the cost it reports."""
        path = tmp_path / "legacy.npz"
        cache = PairCache(None, "stub-cross-v1", RERANK_CHUNKING)
        key = cache.key_for("doc", "code")
        np.savez(
            path,
            __stamp__=np.array(f"stub-cross-v1|{RERANK_CHUNKING.key}"),
            keys=np.array([key], dtype="<U32"),
            scores=np.array([1.25], dtype=np.float32),
        )

        scorer = OverlapScorer()
        loaded = PairCache(path, "stub-cross-v1", RERANK_CHUNKING)

        assert loaded.get_or_score([("doc", "code")], scorer) == [1.25]
        assert scorer.calls == 0

    def test_the_written_keys_are_ascii_bytes_not_utf32(self, tmp_path):
        path = tmp_path / "pairs.npz"
        cache = PairCache(path, "stub-cross-v1", RERANK_CHUNKING)
        cache.get_or_score([("d", "c")], OverlapScorer())
        cache.save()

        with np.load(path, allow_pickle=False) as handle:
            assert handle["keys"].dtype == np.dtype("S32")

    def test_no_path_means_nothing_is_written(self, tmp_path):
        cache = PairCache(None, "stub-cross-v1", RERANK_CHUNKING)
        cache.get_or_score([("d", "c")], OverlapScorer())

        cache.save()

        assert list(tmp_path.iterdir()) == []

    def test_two_models_get_two_derived_paths(self, tmp_path):
        one = default_pair_cache_path("cross-encoder/x", RERANK_CHUNKING, tmp_path)
        two = default_pair_cache_path("cross-encoder/y", RERANK_CHUNKING, tmp_path)

        assert one != two
        assert one.parent == tmp_path, "the model id must flatten to one component"


class TestTheModelIsCalledOncePerQueryNotOncePerCandidate:
    def test_one_batch_covers_the_whole_head(self):
        """A cross-encoder is 30-50x faster batched. Twenty forward passes per query is
        the difference between a run that finishes and one that does not, and it is
        invisible in the score."""
        pool = _pool(20)
        scorer = OverlapScorer()
        ranker = CrossEncoderReranker(
            FixedOrder(pool), scorer, _cache(), _texts(pool, "src/m07.py", "transport"),
            top_n=20,
        )

        ranker.rank("d.md", "The transport layer.", pool)

        assert scorer.calls == 1

    def test_the_head_is_the_only_thing_scored(self):
        """Scoring the tail too would cost the pool size instead of the cutoff, and
        would still not change R@N -- paying the full price for the capped result."""
        pool = _pool(30)
        scorer = OverlapScorer()
        ranker = CrossEncoderReranker(
            FixedOrder(pool), scorer, _cache(), _texts(pool, "src/m25.py", "transport"),
            top_n=10,
        )

        ranker.rank("d.md", "The transport layer.", pool)

        code_sides = {code for _, code in scorer.pairs_seen}
        assert not any("def transport" in code for code in code_sides)


class TestTheRowNameCarriesTheExperiment:
    def test_the_name_names_both_the_base_and_the_cutoff(self):
        """Two cutoffs over two bases are four experiments. A shared row name would
        average them, which is unreadable rather than wrong."""
        code = {"src/a.py": "def thing(): ..."}

        assert (
            CrossEncoderReranker(
                Lexical(code), OverlapScorer(), _cache(), code, top_n=20
            ).name
            == "rerank(lexical@20)"
        )
        assert (
            CrossEncoderReranker(
                FixedOrder(["src/a.py"]), OverlapScorer(), _cache(), code, top_n=5
            ).name
            == "rerank(fixed@5)"
        )

    def test_a_reranker_whose_name_disagrees_with_its_row_is_refused(self):
        """`evaluate_split` reserves the row name before the loop, then builds the
        ranker inside it. A mismatch would label a `top_n=5` measurement as `@20`."""
        split = RepoSplit(
            repo="o/r",
            clone=None,  # type: ignore[arg-type]
            queries=[Query("o/r", "d.md", "abc", frozenset({"src/a.py"}))],
            pools={"abc": ["src/a.py"]},
        )

        with pytest.raises(ValueError, match="row name"):
            evaluate.evaluate_split(split, rerank=lambda base, texts: base)

    def test_a_rerank_row_is_appended_after_every_established_row(self):
        """A committed results file must not reorder when a new arm is added -- a table
        that reorders itself is a table two runs cannot be diffed by eye."""
        results = [
            evaluate.RepoResult("o/r", 20, 1, name, {1: 0.5, 20: 0.9}, 0.5)
            for name in ("lexical", "rerank(lexical@20)")
        ]

        text = evaluate.format_results(results, ks=(1, 20))

        assert text.index("lexical ") < text.index("rerank(lexical@20)")


class TestTheFooterSaysWhichNumberCannotMove:
    def test_the_invariance_is_stated_wherever_a_rerank_row_is_printed(self):
        """Without it, an unchanged R@20 reads as the reranker having no effect, when it
        is the one number it cannot possibly move."""
        results = [
            evaluate.RepoResult("o/r", 20, 1, "rerank(lexical@20)", {1: 0.5, 20: 0.9}, 0.5)
        ]

        text = evaluate.format_results(results, ks=(1, 20))

        assert "construction" in text
        assert "N=20" in text

    def test_the_paragraph_is_absent_when_no_rerank_row_is_present(self):
        """Explaining a row that is not in the table implies a measurement that was not
        made -- the same reason the ablation paragraph is gated."""
        results = [evaluate.RepoResult("o/r", 20, 1, "lexical", {1: 0.5}, 0.5)]

        assert "construction" not in evaluate.format_results(results, ks=(1,))

    def test_two_cutoffs_in_one_table_both_get_named(self):
        results = [
            evaluate.RepoResult("o/r", 20, 1, name, {1: 0.5}, 0.5)
            for name in ("rerank(lexical@10)", "rerank(lexical@20)")
        ]

        text = evaluate.format_results(results, ks=(1,))

        assert "N=10, 20" in text
