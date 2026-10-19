"""The public bench, and mostly the bars it refuses to let a submission past.

RUN THESE INVERTED. Nearly every test here asserts that something is NOT admissible.
A gate that silently passes everything looks exactly like a gate everybody cleared, so
the mutants worth running are the ones that drop a bar -- delete the width comparison,
delete the constant comparison, stop checking the corpus match -- not the ones that
break the happy path.

And the one test that must never be deleted is `test_a_perfect_detector_is_admissible`.
A gate that cannot be passed is as useless as one that cannot be failed, and this project
has already caught itself shipping a check that could not fail.

NO DEPENDENCE ON THE MINED CORPUS. `data/labels-v*.jsonl` is derived data and is not in
the repository, so a test that called `load_cases` would pass here and fail on a clean
checkout. Cases are built by hand.
"""

from __future__ import annotations

import json

import pytest

from driftwood.judge.bench import (
    BenchRefused,
    judge_submission,
    load_bars,
    parse_predictions,
)
from driftwood.judge.cases import JudgeCase


def case(example_id: str, verdict: str) -> JudgeCase:
    """A case carrying a code path, so it lands on the seeded arm.

    `drift` is the only verdict that means the doc WAS false about the code, so it is
    the positive class; `cosmetic` is a negative; `unclear` is not scoreable at all.
    """
    return JudgeCase(
        example_id=example_id, repo="example/repo", shape="A", basis="synthetic",
        doc_path="docs/index.md", code_path="src/thing.py", at_sha="a" * 40,
        fix_sha="b" * 40, subject="thing", shared_identifiers=("thing",),
        verdict=verdict, sheet="test", resolved_from="test",
    )


# 4 positives, 6 negatives. Small on purpose: the arithmetic stays checkable by hand.
CASES = (
    [case(f"pos{i}", "drift") for i in range(4)]
    + [case(f"neg{i}", "cosmetic") for i in range(6)]
    + [case("unclear0", "unclear")]
)
LIVE = {"verdicts": 11, "scoreable": 10, "with_code_path": 10}


def write_bars(
    tmp_path, *, best_free_f1=0.400, constant_accuracy=0.600, width=0.130,
    chance_p95=0.300, corpus=None,
):
    corpus = corpus or LIVE
    floors = tmp_path / "floors.json"
    floors.write_text(json.dumps({
        "provenance": {"corpus": corpus},
        "arms": {"seeded": {"judges": {
            "always-not-false": {"f1": 0.0, "accuracy_all": constant_accuracy},
            "always-false": {"f1": best_free_f1 - 0.05, "accuracy_all": 0.3},
            "lexical-absence(>=6)": {"f1": best_free_f1, "accuracy_all": 0.45},
        }}},
    }))
    width_file = tmp_path / "width.json"
    width_file.write_text(json.dumps({
        "provenance": {"corpus": corpus},
        "judges": {"model:x": {
            "minimum_detectable_effect_f1": width,
            "chance_range": {"f1": [0.1, 0.2, chance_p95]},
        }},
    }))
    return load_bars(floors, width_file, LIVE)


def predictions(fn):
    return {c.example_id: fn(c) for c in CASES if c.scoreable}


class TestTheCorpusMatchComesFirst:
    def test_floors_from_a_different_corpus_refuse_before_scoring(self, tmp_path):
        # The trap this project spent a stage on: floors move every time a sheet is
        # labelled, so a submission paired with the wrong one gets free credit or free
        # blame. Checked, not warned about.
        with pytest.raises(BenchRefused) as caught:
            write_bars(tmp_path, corpus={"verdicts": 9, "scoreable": 8, "with_code_path": 8})
        assert caught.value.state == "CORPUS_MISMATCH"
        assert "NOTHING WAS SCORED" in caught.value.guidance

    def test_a_measurement_with_no_provenance_refuses(self, tmp_path):
        floors = tmp_path / "f.json"
        floors.write_text(json.dumps({"arms": {"seeded": {"judges": {}}}}))
        width = tmp_path / "w.json"
        width.write_text(json.dumps({"provenance": {"corpus": LIVE}, "judges": {}}))
        with pytest.raises(BenchRefused) as caught:
            load_bars(floors, width, LIVE)
        assert caught.value.state == "UNUSABLE_MEASUREMENT"

    def test_no_verdict_without_a_measured_width(self, tmp_path):
        floors = tmp_path / "f.json"
        floors.write_text(json.dumps({
            "provenance": {"corpus": LIVE},
            "arms": {"seeded": {"judges": {
                "always-not-false": {"f1": 0.0, "accuracy_all": 0.6},
                "lexical-absence(>=6)": {"f1": 0.4, "accuracy_all": 0.4},
            }}},
        }))
        width = tmp_path / "w.json"
        width.write_text(json.dumps({
            "provenance": {"corpus": LIVE},
            "judges": {"model:x": {"chance_range": {"f1": [0.1, 0.2, 0.3]}}},
        }))
        with pytest.raises(BenchRefused) as caught:
            load_bars(floors, width, LIVE)
        assert caught.value.state == "UNUSABLE_MEASUREMENT"
        assert "run-to-run width" in caught.value.guidance

    def test_the_best_free_floor_is_read_from_the_file_not_hardcoded(self, tmp_path):
        # A hardcoded floor name is a floor chosen to lose: the winner here has already
        # changed as the corpus grew.
        bars = write_bars(tmp_path, best_free_f1=0.9)
        assert bars.best_free_name == "lexical-absence(>=6)"
        assert bars.best_free_f1 == 0.9


class TestTheBars:
    def test_a_perfect_detector_is_admissible(self, tmp_path):
        # DO NOT DELETE. A gate that cannot be passed is as useless as one that cannot
        # be failed.
        bars = write_bars(tmp_path)
        verdict = judge_submission("oracle", predictions(lambda c: bool(c.target)), CASES, bars)
        assert verdict.admissible, verdict.reasons
        assert verdict.scores.f1 == 1.0

    def test_beating_the_floor_by_less_than_the_width_is_not_a_result(self, tmp_path):
        # THE HEADLINE PROPERTY. A detector genuinely above the free floor but by less
        # than the harness moves on its own has demonstrated nothing, and a leaderboard
        # sorted by F1 would still rank it first.
        bars = write_bars(tmp_path, best_free_f1=0.60, width=0.30, constant_accuracy=0.0)
        # 3 of 4 positives, no false positives -> F1 0.857, which is 0.257 over the
        # floor and inside a 0.300 width.
        answers = predictions(lambda c: bool(c.target) and c.example_id != "pos3")
        verdict = judge_submission("marginal", answers, CASES, bars)
        assert 0 < verdict.scores.f1 - bars.best_free_f1 < bars.width_f1
        assert not verdict.admissible
        assert any("INSIDE THE NOISE" in r for r in verdict.reasons)

    def test_losing_to_the_constant_is_named_even_when_f1_is_high(self, tmp_path):
        bars = write_bars(tmp_path, best_free_f1=0.0, width=0.01, constant_accuracy=0.99)
        verdict = judge_submission("flagger", predictions(lambda c: True), CASES, bars)
        assert not verdict.admissible
        assert any("LOSES TO A CONSTANT" in r for r in verdict.reasons)

    def test_a_tie_with_the_constant_does_not_clear_it(self, tmp_path):
        # Strictly greater, not greater-or-equal. Matching a free constant is not beating
        # it, and `>=` here would admit `always-not-false` itself.
        bars = write_bars(tmp_path, best_free_f1=0.0, width=0.01, constant_accuracy=0.6)
        verdict = judge_submission("tie", predictions(lambda c: bool(c.target)), CASES, bars)
        assert verdict.scores.accuracy_all == 1.0
        bars_tied = write_bars(tmp_path, best_free_f1=0.0, width=0.01, constant_accuracy=1.0)
        tied = judge_submission("tie", predictions(lambda c: bool(c.target)), CASES, bars_tied)
        assert not tied.admissible
        assert any("LOSES TO A CONSTANT" in r for r in tied.reasons)

    def test_inside_the_chance_range_is_not_signal(self, tmp_path):
        # Isolated to the chance bar: the other two are set so low that only this one
        # can fail, which is what makes the assertion about the bar rather than the
        # submission.
        bars = write_bars(
            tmp_path, best_free_f1=0.0, width=0.01, constant_accuracy=0.0, chance_p95=0.99
        )
        # 3 of 4 positives, no false positives -> F1 0.857, under a 0.99 chance ceiling.
        answers = predictions(lambda c: bool(c.target) and c.example_id != "pos3")
        verdict = judge_submission("lucky", answers, CASES, bars)
        assert verdict.scores.f1 < bars.chance_f1_p95
        assert verdict.scores.f1 - bars.best_free_f1 > bars.width_f1
        assert verdict.scores.accuracy_all > bars.constant_accuracy
        assert not verdict.admissible
        assert verdict.reasons == [r for r in verdict.reasons if "INSIDE CHANCE" in r]


class TestAbstentionCannotBuyAPass:
    def test_a_detector_perfect_on_what_it_answered_is_not_comparable(self, tmp_path):
        # The flattering failure: abstain on the hard cases, be right about the easy
        # ones, and F1 reads 1.000 on a denominator nobody agreed to.
        bars = write_bars(tmp_path, best_free_f1=0.0, width=0.01, constant_accuracy=0.0)
        answers = predictions(lambda c: bool(c.target) if c.example_id != "pos0" else None)
        verdict = judge_submission("abstainer", answers, CASES, bars)
        assert verdict.scores.f1 == 1.0
        assert not verdict.comparable
        assert not verdict.admissible
        assert any("NOT COMPARABLE" in r for r in verdict.reasons)

    def test_an_unscored_case_is_neither_right_nor_wrong(self, tmp_path):
        bars = write_bars(tmp_path)
        answers = predictions(lambda c: bool(c.target))
        answers.pop("neg0")
        verdict = judge_submission("partial", answers, CASES, bars)
        assert "neg0" in verdict.missing_ids
        assert verdict.scores.n == 9
        assert not verdict.admissible


class TestTheSubmissionFormat:
    def test_unknown_ids_are_reported_rather_than_scored(self, tmp_path):
        bars = write_bars(tmp_path)
        answers = predictions(lambda c: bool(c.target))
        answers["not-in-this-corpus"] = True
        verdict = judge_submission("stranger", answers, CASES, bars)
        assert verdict.unknown_ids == ["not-in-this-corpus"]
        assert verdict.scores.n == 10

    def test_unclear_cases_are_outside_the_arm_entirely(self, tmp_path):
        bars = write_bars(tmp_path)
        answers = predictions(lambda c: bool(c.target))
        answers["unclear0"] = True
        verdict = judge_submission("guesser", answers, CASES, bars)
        # Held out for being unlabelled, so a prediction about one earns and costs
        # nothing rather than being scored against a verdict that does not exist.
        assert verdict.unknown_ids == ["unclear0"]

    @pytest.mark.parametrize(
        "line",
        ['{"answer": true}', "not json at all", '{"example_id": "x", "answer": "maybe"}'],
    )
    def test_a_bad_line_refuses_the_whole_submission(self, line):
        with pytest.raises(BenchRefused):
            parse_predictions(line, source="test")

    def test_a_duplicated_prediction_refuses(self):
        text = '{"example_id": "a", "answer": true}\n{"example_id": "a", "answer": false}'
        with pytest.raises(BenchRefused) as caught:
            parse_predictions(text, source="test")
        assert caught.value.state == "DUPLICATE_PREDICTION"

    def test_an_empty_submission_is_not_a_silent_detector(self):
        # Flagging nothing IS a detector -- `always-not-false` -- and it is already in
        # the floors. An empty file is a mistake, so it refuses rather than scoring 0.
        with pytest.raises(BenchRefused) as caught:
            parse_predictions("\n# just a comment\n", source="test")
        assert caught.value.state == "EMPTY_SUBMISSION"

    def test_word_answers_are_accepted_so_an_inversion_fails_on_merit(self):
        parsed = parse_predictions(
            '{"example_id": "a", "answer": "stale"}\n'
            '{"example_id": "b", "answer": "not-false"}\n'
            '{"example_id": "c", "answer": "abstain"}',
            source="test",
        )
        assert parsed == {"a": True, "b": False, "c": None}


class TestTheFalseFlagRate:
    def test_it_is_the_share_of_no_fault_cases_flagged(self, tmp_path):
        bars = write_bars(tmp_path)
        verdict = judge_submission("flagger", predictions(lambda c: True), CASES, bars)
        # All 6 negatives flagged.
        assert verdict.false_flag_rate == 1.0

    def test_it_is_none_when_there_are_no_negatives_to_flag(self, tmp_path):
        bars = write_bars(tmp_path)
        only_positives = [c for c in CASES if c.verdict == "drift"]
        verdict = judge_submission(
            "x", {c.example_id: True for c in only_positives}, only_positives, bars
        )
        # Not 0.0. A rate of zero would read as "flagged none of them" when the truth is
        # that there were none to flag.
        assert verdict.false_flag_rate is None
