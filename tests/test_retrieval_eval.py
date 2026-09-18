"""The retrieval harness, tested where it can lie rather than where it can crash.

A retrieval eval fails quietly. Every failure mode below produces a plausible
number, which is why each one gets a named test instead of a comment:

- a metric that is silently capped by lost positives
- a floor that is not actually random
- a tail of zero-scoring candidates ordered by dict insertion
- a ranker that looks good because the pool is small
"""

from __future__ import annotations

import json

import pytest

from driftwood.retrieval import evaluate
from driftwood.retrieval.dataset import Query, format_dataset_report
from driftwood.retrieval.rankers import (
    Lexical,
    PathOverlap,
    Shuffle,
    path_tokens,
    stem_tokens,
)


class _FixedRanker:
    """Returns a fixed order, so metric arithmetic is checkable by hand."""

    name = "fixed"

    def __init__(self, order: list[str]) -> None:
        self._order = order

    def rank(self, doc_path, doc_text, pool, exclude=frozenset()):
        return self._order


POOL = [f"src/m{i}.py" for i in range(20)]


def score(ranker, queries, pool, ks=(1, 5, 10)):
    """Mean recall@k and mean MRR for one ranker, the shape the old API returned.

    `score_queries` deliberately hands back per-query values so a repo can be
    averaged across all of its trees at once; the means are what the assertions here
    are about.
    """
    import statistics

    docs = {q.doc_path: "" for q in queries}
    recalls, ranks = evaluate.score_queries({"r": ranker}, queries, pool, docs, ks)["r"]
    return (
        {k: statistics.fmean(r[k] for r in recalls) for k in ks},
        statistics.fmean(ranks),
    )


class TestMetrics:
    def test_recall_counts_only_this_query_s_own_answers(self):
        query = Query("o/r", "d.md", "sha", frozenset({"src/m0.py", "src/m19.py"}))
        ranker = _FixedRanker(["src/m0.py", *POOL[1:]])

        recall, _ = score(ranker, [query], POOL)

        # One of two answers found at every k -- 0.5, not 1.0. A "did we find any"
        # metric would read 1.00 here and hide the missed second answer, which is
        # exactly the case a reranker is supposed to fix.
        assert recall[1] == pytest.approx(0.5)
        assert recall[10] == pytest.approx(0.5)

    def test_mrr_reports_the_first_hit_not_the_best_one(self):
        query = Query("o/r", "d.md", "sha", frozenset({"src/m2.py", "src/m3.py"}))
        ranker = _FixedRanker(["src/m9.py", "src/m2.py", "src/m3.py"])

        _, mrr = score(ranker, [query], POOL, ks=(1,))

        assert mrr == pytest.approx(0.5)  # rank 2

    def test_a_query_with_no_hit_at_all_scores_zero_rather_than_being_skipped(self):
        query = Query("o/r", "d.md", "sha", frozenset({"src/gone.py"}))

        recall, mrr = score(_FixedRanker(POOL), [query], POOL, ks=(10,))

        assert recall[10] == 0.0 and mrr == 0.0

    def test_recall_averages_over_queries_not_over_pairs(self):
        """A doc with eleven answers must not outvote ten docs with one.

        Micro-averaging over pairs would let one heavily-judged file decide the
        whole number, and `pydantic` has docs with double-digit answer sets.
        """
        many = Query("o/r", "a.md", "sha", frozenset(POOL[:10]))
        one = Query("o/r", "b.md", "sha", frozenset({"src/m0.py"}))
        ranker = _FixedRanker(POOL)

        recall, _ = score(ranker, [many, one], POOL, ks=(1,))

        # many: 1/10 found at k=1. one: 1/1. Macro mean = 0.55.
        # A pair-pooled figure would be 2/11 = 0.18.
        assert recall[1] == pytest.approx(0.55)


class TestTheFloorIsRealRandomness:
    def test_shuffle_does_not_return_the_pool_order(self):
        ranked = Shuffle(seed=0).rank("docs/index.md", "", POOL)

        assert sorted(ranked) == sorted(POOL)  # nothing lost or duplicated
        assert ranked != POOL

    def test_the_same_seed_and_doc_give_the_same_order(self):
        """An unrepeatable floor cannot be compared against, which defeats it."""
        assert Shuffle(seed=3).rank("d.md", "", POOL) == Shuffle(seed=3).rank(
            "d.md", "", POOL
        )

    def test_different_seeds_give_different_orders(self):
        """If they did not, the noise range would collapse to a point and every
        gain would look significant."""
        assert Shuffle(seed=1).rank("d.md", "", POOL) != Shuffle(seed=2).rank(
            "d.md", "", POOL
        )

    def test_different_docs_get_different_orders_under_one_seed(self):
        """Otherwise every query in a trial shares one ranking, and the trial
        measures a single coin flip rather than a mean over queries."""
        assert Shuffle(seed=1).rank("a.md", "", POOL) != Shuffle(seed=1).rank(
            "b.md", "", POOL
        )

    def test_the_floor_rises_as_the_pool_shrinks(self):
        """The whole reason the control exists: on a small pool, random is good.

        Averaged over many trials rather than one, because a single trial on a
        four-file pool is a coin flip and would make this test flake -- the same
        reason the harness itself never quotes a one-trial floor.
        """
        query = Query("o/r", "d.md", "sha", frozenset({"src/m0.py"}))

        def floor(pool: list[str]) -> float:
            return sum(
                score(Shuffle(seed=seed), [query], pool, ks=(2,))[0][2]
                for seed in range(200)
            ) / 200

        small, big = floor(POOL[:4]), floor(POOL)

        # 2 of 4 vs 2 of 20: roughly 50% against 10%.
        assert small > 0.35 and big < 0.20


class TestTiesDoNotDependOnPoolOrder:
    def test_a_ranker_that_scores_nothing_is_still_deterministic(self):
        """Most candidates score zero under a sparse ranker. If the zero tail were
        ordered by dict insertion, recall@10 on a 22-file pool would depend on the
        order `ls-tree` emitted -- and two identical runs would disagree."""
        ranker = PathOverlap()
        forwards = ranker.rank("docs/nothing_matches_here.md", "", POOL)
        backwards = ranker.rank("docs/nothing_matches_here.md", "", list(reversed(POOL)))

        assert forwards == backwards == sorted(POOL)


class TestPathOverlap:
    def test_a_mirrored_layout_is_matched(self):
        pool = ["src/routing.py", "src/client.py", "src/utils.py"]

        assert PathOverlap().rank("docs/routing.md", "", pool)[0] == "src/routing.py"

    def test_short_path_pieces_are_not_the_signal(self):
        """`src` and `lib` appear in every path; matching on them would rank the
        whole pool equally and the tiebreak would become the ranker."""
        assert "src" not in path_tokens("src/lib/routing.py")
        assert "routing" in path_tokens("src/lib/routing.py")

    def test_stem_tokens_exclude_the_directories(self):
        assert stem_tokens("docs/advanced/custom_response.md") == {"custom", "response"}

    def test_a_shared_directory_alone_is_not_a_match(self):
        """The regression that put this ranker below chance on flask.

        `docs/api.rst` reduces to the single token `docs`, which `docs/conf.py` shares
        while telling you nothing about which file the doc is about. Matching on it
        made `docs/conf.py` rank 1 for 388 of flask's 396 queries -- a confidently
        wrong baseline, which understates the bar for every model added later.
        """
        pool = ["docs/conf.py", "src/flask/helpers.py"]

        ranked = PathOverlap().rank("docs/api.rst", "", pool)

        # Nothing matches, so the order is the deterministic tiebreak -- not a
        # confident vote for the shortest path in the docs directory.
        assert ranked == sorted(pool)

    def test_a_directory_that_matches_a_filename_still_counts(self):
        """The rule is "at least one filename involved", not "filenames only": a doc
        at `docs/routing/index.md` is about `src/routing.py`."""
        pool = ["src/routing.py", "src/other.py"]

        assert PathOverlap().rank("docs/routing/index.md", "", pool)[0] == "src/routing.py"


class TestTheAblationArm:
    """The lexical ranker is graded on a corpus selected for sharing identifiers with
    it, so the ablated arm is the number that can be defended. These tests are about
    the ablation actually removing something."""

    CODE = {
        "src/transport.py": "class HTTPTransport: pass",
        "src/other.py": "class Unrelated: pass",
    }

    def test_striking_out_the_mined_evidence_changes_the_ranking(self):
        doc = "See `HTTPTransport`."
        ranker = Lexical(self.CODE)
        pool = sorted(self.CODE)

        assert ranker.rank("d.md", doc, pool)[0] == "src/transport.py"
        # With the one token the miner matched on removed, nothing is left to rank on
        # and the result falls back to the deterministic tiebreak.
        blind = ranker.rank("d.md", doc, pool, frozenset({"httptransport"}))
        assert blind == sorted(pool)

    def test_the_ablation_flows_from_the_query_not_from_a_global_list(self):
        """Each query loses its own evidence. A shared stoplist would remove a token
        from queries it was never the evidence for, and understate every arm."""
        query_a = Query("o/r", "a.md", "s", frozenset({"src/transport.py"}),
                        frozenset({"httptransport"}))
        query_b = Query("o/r", "b.md", "s", frozenset({"src/transport.py"}),
                        frozenset({"something_else"}))
        docs = {"a.md": "See `HTTPTransport`.", "b.md": "See `HTTPTransport`."}
        pool = sorted(self.CODE)

        scored = evaluate.score_queries(
            {"lex": Lexical(self.CODE)}, [query_a, query_b], pool, docs,
            ks=(1,), ablate=True,
        )["lex"]

        # b keeps its hit (its evidence token was irrelevant); a loses the signal.
        assert scored[0][0][1] == 0.0
        assert scored[0][1][1] == 1.0

    def test_a_ranker_that_ignores_the_exclude_set_is_unaffected(self):
        """`path` and `shuffle` do not consume identifier tokens, so the ablated run
        must not quietly move them -- otherwise the gap between arms is unreadable."""
        pool = ["src/routing.py", "src/client.py"]

        assert PathOverlap().rank("docs/routing.md", "", pool) == PathOverlap().rank(
            "docs/routing.md", "", pool, frozenset({"routing"})
        )


class TestLexical:
    def test_a_rare_shared_identifier_outranks_a_common_one(self):
        """The point of the IDF weighting, isolated.

        Both candidates share exactly one token with the doc and hold the same
        number of tokens, so overlap count and length cannot decide it. `session`
        is in every file in the pool and carries almost no information; the
        transport class is in one. Only the weighting separates them.
        """
        code = {
            "src/transport.py": "class HTTPTransport: session = None",
            "src/client.py": "class Bland: session = None",
            "src/models.py": "class Other: session = None",
            "src/pools.py": "class Third: session = None",
        }
        doc = "Configure `HTTPTransport` on the `session`."

        ranked = Lexical(code).rank("docs/transports.md", doc, sorted(code))

        assert ranked[0] == "src/transport.py"

    def test_two_shared_tokens_beat_one_even_when_the_one_is_rarer(self):
        """Not a defect -- recorded because it is the ranker's main weakness and it
        will show up in the results before any model does.

        Set overlap has no notion of a token being *central* to a document. A doc
        that names one unusual class from module A and two incidental helpers from
        module B ranks B first. Term frequency is the cheapest fix and is the first
        thing to try if the lexical arm underperforms the path arm.
        """
        code = {
            "src/rare.py": "class HTTPTransport: pass",
            "src/common.py": "def parse_headers(): ...\ndef build_cookie(): ...",
        }
        doc = "Uses `HTTPTransport`, `parse_headers` and `build_cookie`."

        assert Lexical(code).rank("d.md", doc, sorted(code))[0] == "src/common.py"

    def test_a_long_file_does_not_win_on_length_alone(self):
        """Without the length normaliser the biggest module in the repo ranks first
        for every query, which reads as a working ranker with one strong feature."""
        code = {
            "src/huge.py": "\n".join(f"def helper_{i}(self): ..." for i in range(400)),
            "src/small.py": "def helper_7(self): ...",
        }
        doc = "Call `helper_7`."

        assert Lexical(code).rank("d.md", doc, sorted(code))[0] == "src/small.py"

    def test_a_candidate_with_no_readable_text_is_ranked_last_not_crashed_on(self):
        code = {"src/real.py": "def parse_headers(): ...", "src/empty.py": ""}

        ranked = Lexical(code).rank("d.md", "See `parse_headers`.", sorted(code))

        assert ranked == ["src/real.py", "src/empty.py"]


class TestReporting:
    """`build` needs a real clone; `test_read_blobs.py` covers the git side. Here
    only the reporting contract, which is where a caveat gets silently dropped."""

    def test_the_report_names_the_lost_positives(self):
        from driftwood.retrieval.dataset import RepoSplit

        split = RepoSplit(
            repo="o/r",
            clone=None,  # type: ignore[arg-type]
            queries=[Query("o/r", "d.md", "abc", frozenset({"src/a.py"}))],
            pools={"abc": ["src/a.py"]},
            dropped_positives=3,
            dropped_docs=2,
        )

        report = format_dataset_report([split])

        # The count has to be visible, because a positive missing from its own tree
        # caps recall for a reason the ranker cannot fix.
        assert "lost" in report
        assert "5" in report  # 3 dropped positives + 2 dropped docs

    def test_the_report_shows_when_one_document_dominates_a_repo(self):
        """A repo whose queries are 80% one file is reporting that file's score under
        the repo's name, and the reader cannot tell from a recall figure alone."""
        from driftwood.retrieval.dataset import RepoSplit

        busy = [
            Query("o/r", "docs/index.md", f"sha{i}", frozenset({"src/a.py"}))
            for i in range(8)
        ] + [Query("o/r", "docs/other.md", "sha9", frozenset({"src/a.py"}))]
        split = RepoSplit(
            repo="o/r",
            clone=None,  # type: ignore[arg-type]
            queries=busy,
            pools={q.at_sha: ["src/a.py"] for q in busy},
        )

        assert split.busiest_doc_share == pytest.approx(8 / 9)
        assert "89%" in format_dataset_report([split])

    def test_an_unreadable_sha_is_warned_about_rather_than_counted_as_a_miss(self):
        """A sha missing from the clone drops its queries. Silently, that reads as a
        smaller corpus; the warning is what distinguishes it from one."""
        from driftwood.retrieval.dataset import RepoSplit

        split = RepoSplit(
            repo="o/r",
            clone=None,  # type: ignore[arg-type]
            queries=[Query("o/r", "d.md", "abc", frozenset({"src/a.py"}))],
            pools={"abc": ["src/a.py"]},
            shas_unreadable=["deadbeef"],
        )

        assert "WARNING" in format_dataset_report([split])

    def test_json_output_records_the_pool_size_next_to_every_score(self):
        """A recall figure without its pool size is not checkable later."""
        from driftwood.retrieval.dataset import RepoSplit

        query = Query("o/r", "d.md", "abc", frozenset({"src/m0.py"}))
        split = RepoSplit(
            repo="o/r",
            clone=None,  # type: ignore[arg-type]
            queries=[query],
            pools={"abc": POOL},
        )
        result = evaluate.RepoResult(
            repo="o/r",
            pool_median=len(POOL),
            queries=1,
            ranker="lexical",
            recall_at={1: 0.5},
            mrr=0.5,
        )

        payload = json.loads(json.dumps(evaluate.to_json([result], [split])))

        assert payload["results"][0]["pool_median"] == 20
        assert payload["dataset"][0]["pool_min_median_max"] == [20, 20, 20]
        assert payload["null_trials"] == evaluate.NULL_TRIALS
        # Names the design decision, so a future reader of the file knows the score
        # was not taken against one recent tree per repo.
        assert payload["scored_at"] == "each query's own at_sha"


class TestTheFooterDescribesTheRunAndNotTheDefaults:
    """The prose under the table is read as fact about the numbers above it.

    Both of these were live defects found by running `doc-eval`: a low-trial run
    claimed the module default's 40 trials, and a table with no ablated row still
    carried the paragraph explaining what the ablated row means.
    """

    def _result(self, ranker: str) -> evaluate.RepoResult:
        return evaluate.RepoResult(
            repo="a/b",
            pool_median=20,
            queries=3,
            ranker=ranker,
            recall_at={1: 0.1, 5: 0.2, 10: 0.3},
            mrr=0.2,
        )

    def test_the_trial_count_is_the_one_the_run_used(self):
        text = evaluate.format_results([self._result("lexical")], null_trials=8)
        assert "over 8 trials" in text
        assert "40 trials" not in text

    def test_the_ablation_paragraph_is_absent_when_no_ablated_row_is(self):
        text = evaluate.format_results([self._result("lexical")], null_trials=8)
        assert "lexical-ablated re-runs" not in text

    def test_the_ablation_paragraph_is_present_when_the_row_is(self):
        text = evaluate.format_results(
            [self._result("lexical"), self._result("lexical-ablated")], null_trials=8
        )
        assert "lexical-ablated re-runs" in text

    def test_a_dense_row_without_an_ablated_twin_names_lexical_as_the_bar(self):
        text = evaluate.format_results([self._result("lexical"), self._result("dense")])
        assert "The bar for dense is `lexical` PER REPO" in text
        assert "REDACTS" not in text
