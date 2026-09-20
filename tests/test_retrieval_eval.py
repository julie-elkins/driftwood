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
    DEFAULT_K1,
    Lexical,
    LexicalTF,
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


class TestLexicalTF:
    """One lever added to `Lexical`, and the tests are about that being true.

    The reason this class is mostly about NESTING rather than about the new ranker
    winning: a reimplementation that scored better would be uninterpretable, because a
    rewrite and a term-frequency factor are two changes and the table has one column.
    """

    def test_k1_of_zero_reproduces_lexical_exactly_on_real_source_text(self):
        """The limit that makes a result attributable. At k1=0 the factor
        `tf / (tf + k1)` is 1 for every token present at all, and the IDF and the
        length normaliser are untouched -- so the ORDER must be identical, not merely
        correlated.

        Run over the project's own files rather than a fixture: a two-file pool has
        too few ties for an ordering difference to show up, and the zero-scoring tail
        is where a rewrite's disagreement with `_stable_order` would hide.
        """
        from pathlib import Path

        code = {
            str(path): path.read_text(encoding="utf-8")
            for path in sorted(Path("src/driftwood").rglob("*.py"))
        }
        pool = sorted(code)
        doc = Path("README.md").read_text(encoding="utf-8")

        baseline = Lexical(code).rank("README.md", doc, pool)
        nested = LexicalTF(code, k1=0.0).rank("README.md", doc, pool)

        assert nested == baseline

    def test_term_frequency_fixes_the_weakness_lexical_s_own_docstring_names(self):
        """The same pool as
        `TestLexical.test_two_shared_tokens_beat_one_even_when_the_one_is_rarer`, which
        records set overlap's main weakness: a doc names one unusual class from module A
        and two incidental helpers from module B, and B ranks first. Here the class is
        named eleven times in the file it belongs to, and that is the signal set
        overlap throws away.

        This is the experiment, not a passing assertion about it. Whether the flip is
        worth anything on the real corpora is what the eval measures; all this pins is
        that the lever moves the thing it was added to move -- and, on the third line,
        that it is the lever doing it rather than anything else in the new class.
        """
        code = {
            "src/transport.py": "class HTTPTransport: pass\n" + "HTTPTransport()\n" * 10,
            "src/helpers.py": "def headers(): ...\ndef cookie(): ...",
        }
        doc = "Uses `HTTPTransport`, plus `headers` and `cookie`."
        pool = sorted(code)

        assert Lexical(code).rank("d.md", doc, pool)[0] == "src/helpers.py"
        assert LexicalTF(code).rank("d.md", doc, pool)[0] == "src/transport.py"
        assert LexicalTF(code, k1=0.0).rank("d.md", doc, pool)[0] == "src/helpers.py"

    def test_the_query_side_is_untouched_so_repeating_a_word_in_the_doc_changes_nothing(
        self,
    ):
        """Held still deliberately. BM25 has a query-term-frequency factor too, and
        adding it here would be a second lever -- and would change what `exclude`
        operates on, which is the measurement that bounds circularity on this corpus.
        """
        code = {
            "src/transport.py": "class HTTPTransport: session = None",
            "src/client.py": "class Bland: session = None",
        }
        pool = sorted(code)
        ranker = LexicalTF(code)

        once = ranker.rank("d.md", "See `HTTPTransport`.", pool)
        many = ranker.rank("d.md", "`HTTPTransport` " * 40, pool)

        assert once == many

    def test_the_ablation_arm_still_bites(self):
        """`exclude` is honoured, and it has to be: the ablated row is the defensible
        number on the mined corpus, so a ranker that quietly ignored the exclude set
        would report a circular score as a bounded one."""
        code = {
            "src/transport.py": "class HTTPTransport: pass\n" * 11,
            "src/other.py": "def unrelated(): ...",
        }
        pool = sorted(code)
        ranker = LexicalTF(code)

        assert ranker.rank("d.md", "See `HTTPTransport`.", pool)[0] == "src/transport.py"
        ablated = ranker.rank(
            "d.md", "See `HTTPTransport`.", pool, frozenset({"httptransport"})
        )
        assert ablated == pool  # nothing scores, so the stable tiebreak decides

    def test_the_row_name_carries_k1_so_two_settings_cannot_collide(self):
        code = {"src/a.py": "def thing(): ..."}

        assert LexicalTF(code).name == f"lexical-tf(k1={DEFAULT_K1:g})"
        assert LexicalTF(code, k1=0.0).name == "lexical-tf(k1=0)"
        assert LexicalTF(code, k1=2.5).name == "lexical-tf(k1=2.5)"

    def test_a_negative_k1_is_refused_rather_than_inverting_the_ranker(self):
        """At k1 < -1 the factor goes negative and a token mentioned often counts
        AGAINST a file. That is not a setting anyone means, and it produces a plausible
        table."""
        with pytest.raises(ValueError, match="k1"):
            LexicalTF({"src/a.py": "def thing(): ..."}, k1=-1.0)

    def test_the_count_cache_is_keyed_by_contents_not_by_path(self):
        """Same reasoning as `Lexical`'s cache, and the same measurement depends on
        it: queries are scored at ~350 shas and most files are byte-identical between
        them. A path-keyed cache would miss every one of those hits."""
        cache = {}
        LexicalTF({"src/a.py": "def parse_headers(): ..."}, cache)
        assert len(cache) == 1

        LexicalTF({"pkg/renamed.py": "def parse_headers(): ..."}, cache)
        assert len(cache) == 1, "same bytes at a new path should reuse the entry"

        LexicalTF({"src/a.py": "def parse_headers(): pass"}, cache)
        assert len(cache) == 2, "different bytes at the same path must not reuse it"


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

    def test_a_long_ranker_name_widens_the_column_instead_of_shifting_the_numbers(self):
        """`lexical-tf(k1=1.2)-ablated` is 26 characters against a column that was 17.

        An overflowing name pushes the figures right on its own line only, so one row's
        R@1 sits under the next row's R@5. Nothing errors and every number is correct;
        the table just reads as a different table, which is the failure mode this whole
        module exists to catch.
        """
        rows = [self._result("lexical"), self._result("lexical-tf(k1=1.2)-ablated")]
        lines = evaluate.format_results(rows, null_trials=8).splitlines()

        columns = [line.index("0.10") for line in lines if "0.10" in line]
        assert len(columns) == len(rows)
        assert len(set(columns)) == 1
        # Both are right-aligned in the same 7-wide field, so their last characters land
        # on the same column even though the strings are different lengths.
        assert lines[0].index("R@1") + 3 == columns[0] + 4

    def test_a_table_with_no_long_name_keeps_the_width_it_always_had(self):
        """So a run without --tf-k1 produces a table diffable against the committed
        ones by eye. A results file that reflows when an unrelated ranker is added
        cannot be compared against last month's."""
        rows = [self._result("shuffle (floor)"), self._result("lexical-ablated")]
        header = evaluate.format_results(rows, null_trials=8).splitlines()[0]

        assert header == f"{'repo':<20}{'ranker':<17}{'pool~':>6}{'n':>5}" + "".join(
            f"{'R@' + str(k):>7}" for k in (1, 5, 10)
        ) + f"{'MRR':>7}"
