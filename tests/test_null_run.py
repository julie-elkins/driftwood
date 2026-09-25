"""Stage 4: the null run, and the four ways its width can be narrower than the truth.

This stage measures the instrument rather than the data, so its failures are not wrong
numbers -- they are *reassuring* numbers. Every one of the following reports a clean
0.000 and gives no sign of trouble:

- two trials sharing a cache directory, so the second is served the first's reply;
- a deterministic judge whose width is nonzero because the harness reordered the cases,
  read as a property of the judge;
- flips that cancel in F1, read off the aggregate as stability;
- an abstention counted as a missing value rather than as the verdict it is.

So these tests mostly pin the shape of the *report* and the *predicate*, not arithmetic.
The arithmetic in `spread` is a max minus a min; the thing that can go wrong is what the
width is claimed to be, and on which judge it is allowed to be zero.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from driftwood.judge.cases import JudgeCase
from driftwood.judge.cli import (
    FREE_JUDGES,
    JUDGE_CHOICES,
    _build_judges,
    _cmd_null_run,
    _is_paid,
    add_parser,
)
from driftwood.judge.evaluate import MIN_CELL
from driftwood.judge.judge import (
    AlwaysJudge,
    AnthropicJudge,
    Judgement,
    LexicalJudge,
    PriorJudge,
)
from driftwood.judge.nullrun import (
    DEFAULT_TRIALS,
    METRICS,
    Trial,
    detectable_effect,
    format_null_run,
    is_deterministic,
    null_run_json,
    spread,
    stability,
    summarise_trial,
    trial_cache,
)

# A judge that is a pure function of its context, which is what `is_deterministic` is
# really claiming and what the harness control rests on. Named here so the claim is
# checked against the classes rather than against a second copy of the name prefixes.
PURE_JUDGES = (AlwaysJudge, LexicalJudge)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftwood")
    add_parser(parser.add_subparsers(dest="command"))
    return parser


def _subparser(name: str) -> argparse.ArgumentParser:
    return _parser()._subparsers._group_actions[0].choices[name]


def _case(example_id: str, verdict: str) -> JudgeCase:
    return JudgeCase(
        example_id=example_id, repo="acme/widget", shape="B", basis="b",
        doc_path="docs/x.rst", code_path=None, at_sha="a", fix_sha="f",
        subject="s", shared_identifiers=(), verdict=verdict, sheet="s.md",
        resolved_from="labels.jsonl",
    )


def _corpus() -> list[JudgeCase]:
    """Two positives, two negatives, and one case that is not scoreable at all."""
    return [
        _case("p1", "drift"), _case("p2", "drift"),
        _case("n1", "cosmetic"), _case("n2", "new"),
        _case("u1", "unclear"),
    ]


def _trial(index: int, answers: dict[str, bool | None], cases=None) -> Trial:
    """A trial built by the real scorer, so its `scores` cannot disagree with its answers.

    Constructing `Scores` by hand would let a test assert a width between two F1 values
    that the confusion matrix underneath them could not produce.
    """
    cases = list(cases or _corpus())
    judgements = {
        example_id: Judgement(
            example_id=example_id, arm="retrieved", judge="j", answer=answer
        )
        for example_id, answer in answers.items()
    }
    return summarise_trial(index, cases, judgements)


@dataclass
class _FixedScores:
    """Metrics set directly, for the width arithmetic and nothing else.

    A real `Scores` cannot be asked for an arbitrary F1 -- it is derived from a confusion
    matrix -- and the width tests are about which number `spread` reports out of several,
    not about whether F1 is computed correctly. The rest of the tests go through the real
    scorer for exactly that reason.
    """

    f1: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    accuracy_all: float = 0.0
    n: int = 4
    abstention_rate: float = 0.0
    abstained: int = 0
    unparsed: int = 0
    truncated: int = 0
    tp: int = 1
    fp: int = 1
    fn: int = 1
    tn: int = 1


def _with_f1(f1: float, index: int = 0) -> Trial:
    return Trial(index=index, answers={}, scores=_FixedScores(f1=f1))  # type: ignore[arg-type]


class TestTheHarnessControlOnItself:
    """The free judges cannot vary, so their width is a test of this code.

    Bought before any paid trial, and the reason is the order of operations: a nonzero
    width on `always-false` measured *after* a paid run would be indistinguishable from
    the judge being noisy, and the paid run would already be spent.
    """

    def test_every_judge_the_flag_can_build_is_classified_by_what_it_is(self, tmp_path):
        # The load-bearing check, and it is against the CLASSES rather than against a
        # second copy of the name prefixes. `is_deterministic` is defined as the
        # complement of `is_paid`, which is only correct while "free" and "pure function
        # of its context" name the same set of judges.
        args = _parser().parse_args(
            ["judge-null-run", "--judges", "floors", "model", "per-claim"]
        )
        judges = _build_judges(args, cache=tmp_path / "trial-00")
        assert len(judges) > len(FREE_JUDGES)
        for name, judge in judges.items():
            assert is_deterministic(name) == isinstance(judge, PURE_JUDGES), name
            # And the agreement with the spend predicate, which is the definition in use.
            assert is_deterministic(name) == (not _is_paid(name)), name

    def test_the_free_sampled_judge_is_deliberately_not_reachable_from_the_flag(self):
        # `PriorJudge` draws a coin per case: free, and NOT a pure function of its
        # context. `is_deterministic("prior")` therefore returns the WRONG answer, and
        # the predicate is safe only because `--judges` cannot build it -- the chance
        # control constructs it directly inside `noise_range`. If it ever becomes a
        # judge choice, the complement of `is_paid` stops being the right definition and
        # the harness control starts passing a judge whose width is nonzero by design.
        assert "prior" not in JUDGE_CHOICES
        assert PriorJudge.name not in FREE_JUDGES
        assert not issubclass(PriorJudge, PURE_JUDGES)

    def test_a_pass_is_claimed_only_at_exactly_zero(self):
        cases = _corpus()
        same = {"p1": True, "p2": True, "n1": True, "n2": True, "u1": True}
        report = format_null_run(
            cases, {"always-false": [_trial(0, same), _trial(1, same)]}, arm="retrieved"
        )
        assert "HARNESS CONTROL" in report
        assert "HARNESS FAULT" not in report
        assert "harness control(s) passed at exactly 0.000: always-false" in report

    def test_a_judge_that_cannot_vary_and_did_is_a_fault_in_the_harness(self):
        # The failure this exists for: a free judge disagreeing with itself means the
        # variance is in the case ordering, the context building or a shared cache. The
        # report has to say that rather than printing a width, because a width here is
        # not a noise floor at all.
        cases = _corpus()
        moved = format_null_run(
            cases,
            {"always-false": [
                _trial(0, {"p1": True, "p2": True, "n1": True, "n2": True}),
                _trial(1, {"p1": True, "p2": False, "n1": True, "n2": True}),
            ]},
            arm="retrieved",
        )
        assert "HARNESS FAULT" in moved
        assert "Do not buy a paid trial" in moved
        assert "passed at exactly 0.000" not in moved

    def test_a_paid_judge_is_given_a_detectable_effect_instead_of_a_control(self):
        cases = _corpus()
        report = format_null_run(
            cases,
            {"model:claude-sonnet-5": [
                _trial(0, {"p1": True, "p2": True, "n1": False, "n2": False}),
                _trial(1, {"p1": True, "p2": False, "n1": False, "n2": False}),
            ]},
            arm="retrieved",
        )
        assert "MINIMUM DETECTABLE EFFECT" in report
        assert "HARNESS CONTROL" not in report


class TestEveryTrialGetsACacheDirectoryOfItsOwn:
    """The bypass, and the one mistake that makes a null run report 0.000 for free.

    `.cache/judgements` is keyed on the rendered prompt and the model, so a second pass
    over it is served byte-identically off disk. That run is clean, cheap, and says
    nothing at all.
    """

    def test_two_trials_are_never_handed_the_same_directory(self):
        root = Path(".cache/null-run")
        paths = {trial_cache(root, i) for i in range(5)}
        assert len(paths) == 5
        assert all(root in p.parents for p in paths)

    def test_the_directory_names_sort_in_run_order(self):
        names = [trial_cache(Path("r"), i).name for i in range(11)]
        assert names == sorted(names), "zero-padded so `ls` reads as the run order"

    def test_the_cli_builds_each_trial_against_its_own_directory(self, tmp_path):
        # Through `_build_judges`, because the per-trial directory only matters if it
        # reaches the judge that writes replies.
        args = _parser().parse_args(["judge-null-run", "--judges", "model"])
        seen = []
        for index in range(2):
            judges = _build_judges(args, cache=trial_cache(tmp_path, index))
            model = next(j for j in judges.values() if isinstance(j, AnthropicJudge))
            seen.append(model.cache_dir)
        assert seen[0] != seen[1]
        assert args.cache_root == Path(".cache/null-run")

    def test_the_cache_root_is_not_the_shared_reply_cache(self):
        null = _parser().parse_args(["judge-null-run"])
        ev = _parser().parse_args(["judge-eval"])
        assert null.cache_root != ev.cache
        # And not a subdirectory of it either: `.cache/judgements` is the published,
        # re-readable history and a null run must neither read nor write it.
        assert ev.cache not in null.cache_root.parents

    def test_the_report_names_the_root_it_used(self):
        report = format_null_run(
            _corpus(),
            {"always-false": [_trial(0, {"p1": True}), _trial(1, {"p1": True})]},
            arm="retrieved", cache_root=Path(".cache/null-run"),
        )
        assert ".cache/null-run" in report


class TestTheWidthIsALowerBoundAndSaysSo:
    def test_identical_trials_have_no_width(self):
        same = {"p1": True, "p2": False, "n1": False, "n2": False}
        widths = spread([_trial(0, same), _trial(1, same)])
        assert all(widths[m]["width"] == 0.0 for m in METRICS)

    def test_the_width_is_the_widest_pair_not_a_percentile(self):
        # Three draws, one of them an outlier. A p5-p95 would shrink towards the middle
        # two and report a narrower width than was actually observed, which is the one
        # direction a noise floor must not be wrong in.
        trials = [
            _with_f1(0.10, 0),
            _with_f1(0.50, 1),
            _with_f1(0.11, 2),
        ]
        got = spread(trials)["f1"]
        assert got["lo"] == 0.10 and got["hi"] == 0.50
        assert abs(got["width"] - 0.40) < 1e-9
        assert got["median"] == 0.11

    def test_recall_is_reported_even_though_the_chance_control_has_no_range_for_it(self):
        # An F1 that holds still while precision and recall trade off is a different
        # finding from an F1 that holds still because nothing moved, and only the pair
        # can tell those apart.
        assert "recall" in METRICS
        widths = spread([_trial(0, {"p1": True}), _trial(1, {"p1": True})])
        assert set(widths) == set(METRICS)

    def test_the_report_calls_it_a_lower_bound_and_gives_the_trial_count(self):
        report = format_null_run(
            _corpus(),
            {"always-false": [_trial(i, {"p1": True}) for i in range(3)]},
            arm="retrieved",
        )
        assert "LOWER BOUND" in report
        assert "3 draws" in report

    def test_the_detectable_effect_is_the_f1_width(self):
        widths = spread([_with_f1(0.2, 0), _with_f1(0.35, 1)])
        assert abs(detectable_effect(widths) - 0.15) < 1e-9

    def test_no_trials_is_reported_rather_than_crashing(self):
        assert spread([])["f1"]["width"] == 0.0
        assert "no trials ran" in format_null_run(
            _corpus(), {"model:x": []}, arm="retrieved"
        )


class TestAStableHeadlineIsNotAStableJudge:
    """The aggregate can be perfectly still while every case underneath it moved."""

    def test_flips_that_cancel_in_f1_are_still_counted_as_instability(self):
        cases = _corpus()
        # p1 and p2 swap answers between trials. One true positive becomes a false
        # negative and the other the reverse, so tp/fp/fn/tn -- and therefore F1,
        # precision, recall and accuracy -- are byte-identical across the two trials.
        first = _trial(0, {"p1": True, "p2": False, "n1": False, "n2": False})
        second = _trial(1, {"p1": False, "p2": True, "n1": False, "n2": False})
        widths = spread([first, second])
        assert all(widths[m]["width"] == 0.0 for m in METRICS), (
            "the premise of this test: the headline does not move"
        )
        _per_case, summary = stability(cases, [first, second])
        assert summary["unstable"] == 2
        assert summary["contradictions"] == 2

    def test_a_contradiction_is_not_also_counted_as_an_abstention_flip(self):
        # A case that answered both ways AND abstained once is a contradiction, which is
        # the worse of the two. Counting it in both buckets would make the two numbers
        # sum past the unstable count and read as more cases than exist.
        cases = _corpus()
        trials = [
            _trial(0, {"p1": True, "p2": True, "n1": False, "n2": False}),
            _trial(1, {"p1": False, "p2": True, "n1": False, "n2": False}),
            _trial(2, {"p1": None, "p2": True, "n1": False, "n2": False}),
        ]
        _per_case, summary = stability(cases, trials)
        assert summary["contradictions"] == 1
        assert summary["abstention_flips"] == 0
        assert summary["unstable"] == 1

    def test_an_abstention_flip_is_instability_of_its_own_kind(self):
        cases = _corpus()
        trials = [
            _trial(0, {"p1": True, "p2": True, "n1": False, "n2": False}),
            _trial(1, {"p1": None, "p2": True, "n1": False, "n2": False}),
        ]
        _per_case, summary = stability(cases, trials)
        assert summary["abstention_flips"] == 1
        assert summary["contradictions"] == 0
        assert summary["unstable"] == 1

    def test_a_case_one_trial_never_answered_is_counted_not_dropped(self):
        # The contexts are built once and shared, so this should be impossible. If it
        # happens it is a fault in the run, and silently excluding the case would hide
        # the fault while shrinking the denominator every rate is computed against.
        cases = _corpus()
        trials = [
            _trial(0, {"p1": True, "p2": True, "n1": False, "n2": False}),
            _trial(1, {"p2": True, "n1": False, "n2": False}),
        ]
        _per_case, summary = stability(cases, trials)
        assert summary["partial"] == 1
        assert summary["n"] == 3

    def test_the_unclear_cases_are_not_in_the_stability_figures(self):
        cases = _corpus()
        answers = {"p1": True, "p2": True, "n1": False, "n2": False, "u1": True}
        per_case, summary = stability(cases, [_trial(0, answers), _trial(1, answers)])
        assert summary["n"] == 4
        assert "u1" not in {c.example_id for c in per_case}

    def test_instability_concentrated_on_the_positives_is_called_out(self):
        # 15% of flips spread over every class is noise; the same 15% sitting on the
        # cases F1 is computed from moves F1 several times further than the flat rate
        # predicts, so the report says which of the two it is looking at.
        cases = _corpus()
        report = format_null_run(
            cases,
            {"model:x": [
                _trial(0, {"p1": True, "p2": True, "n1": False, "n2": False}),
                _trial(1, {"p1": False, "p2": False, "n1": False, "n2": False}),
            ]},
            arm="retrieved",
        )
        assert "CONCENTRATED ON THE POSITIVES" in report

    def test_a_verdict_class_below_the_minimum_cell_is_marked_unreadable(self):
        cases = _corpus()
        report = format_null_run(
            cases,
            {"always-false": [_trial(0, {"p1": True, "p2": True, "n1": True, "n2": True})] * 2},
            arm="retrieved",
        )
        # Every class here is tiny, which is the point: a 2-case class must not read as
        # a rate. `MIN_CELL` rather than the literal, so the two cannot part company.
        assert f"n<{MIN_CELL}: not readable" in report
        assert "by the verdict Julie wrote" in report


class TestReadingItAgainstTheChanceRange:
    """The comparison that can change how every other number in the project is read."""

    CHANCE = {"f1": (0.16, 0.26, 0.36), "accuracy_all": (0.6, 0.65, 0.7),
              "precision": (0.2, 0.26, 0.32)}

    def test_a_run_of_deterministic_judges_only_does_not_print_the_heading(self):
        # A deterministic judge's 0.000 against the chance range is arithmetic on a
        # control rather than a comparison. Printing the heading over an empty list read
        # as a comparison that had failed to produce anything.
        report = format_null_run(
            _corpus(),
            {"always-false": [_trial(0, {"p1": True}), _trial(1, {"p1": True})]},
            arm="retrieved", chance=self.CHANCE,
        )
        assert "READ AGAINST THE CHANCE RANGE" not in report

    def test_a_narrower_run_width_leaves_the_chance_range_binding(self):
        trials = [_with_f1(0.50, 0), _with_f1(0.51, 1)]
        report = format_null_run(
            _corpus(), {"model:x": trials}, arm="retrieved", chance=self.CHANCE
        )
        assert "READ AGAINST THE CHANCE RANGE" in report
        assert "stays the binding floor" in report

    def test_a_wider_run_width_demands_that_everything_be_re_read(self):
        # The money finding. The chance range is 0.20 wide here; a run-to-run width of
        # 0.30 means every gap in this project quoted as "outside the chance range" was
        # quoted against the weaker of two controls.
        trials = [_with_f1(0.20, 0), _with_f1(0.50, 1)]
        report = format_null_run(
            _corpus(), {"model:x": trials}, arm="retrieved", chance=self.CHANCE
        )
        assert "WIDER THAN THE CHANCE RANGE" in report
        assert "re-read against this width" in report


class TestTheReportSaysWhatItDidNotCheck:
    def test_an_unchecked_duplicate_prompt_count_is_not_reported_as_none_found(self):
        # `None` means the check could not run -- only the per-page judge renders one
        # prompt per case. Printing nothing would read as "checked, and clean".
        report = format_null_run(
            _corpus(),
            {"per-claim:x": [_trial(0, {"p1": True}), _trial(1, {"p1": True})]},
            arm="retrieved", duplicate_prompts=None,
        )
        assert "NOT CHECKED" in report

    def test_cases_sharing_a_prompt_are_reported_as_narrowing_every_width(self):
        # Two identical prompts collide on one cache key, so within a trial the second
        # is served the first's reply and the two cannot disagree. Correct -- one prompt
        # is one purchase -- and it suppresses measured variance, so it is counted.
        report = format_null_run(
            _corpus(),
            {"model:x": [_trial(0, {"p1": True}), _trial(1, {"p1": True})]},
            arm="retrieved", duplicate_prompts=6,
        )
        assert "6 case(s) share a rendered prompt" in report
        assert "narrows every width" in report
        assert "NOT CHECKED" not in report

    def test_truncated_replies_make_the_whole_width_not_a_result(self):
        # Truncation follows prompt length, so the damage lands on the hard cases rather
        # than on a random sample. The width that comes out is an artefact of the token
        # ceiling, not a noise floor.
        cases = _corpus()
        answers = {"p1": True, "p2": True, "n1": False, "n2": False}
        judgements = {
            k: Judgement(example_id=k, arm="retrieved", judge="j", answer=v,
                         truncated=(k == "p1"))
            for k, v in answers.items()
        }
        trials = [summarise_trial(i, cases, judgements) for i in range(2)]
        report = format_null_run(cases, {"model:x": trials}, arm="retrieved")
        assert "NOT A RESULT" in report
        assert "--retry-max-tokens" in report

    def test_the_columns_that_read_as_missing_data_are_explained(self):
        # `calls` exceeding `n` (the held-out unclear cases are judged and not scored)
        # and `cached` reading 0 for a free judge both looked like something had gone
        # wrong on the first real run.
        report = format_null_run(
            _corpus(),
            {"always-false": [_trial(0, {"p1": True}), _trial(1, {"p1": True})]},
            arm="retrieved",
        )
        assert "columns:" in report
        assert "SCOREABLE" in report


class TestTheScoreFile:
    def _payload(self, **kwargs) -> dict:
        cases = _corpus()
        trials = [
            _trial(0, {"p1": True, "p2": True, "n1": False, "n2": False}),
            _trial(1, {"p1": None, "p2": True, "n1": False, "n2": False}),
        ]
        return null_run_json(
            cases, {"model:x": trials}, arm="retrieved",
            tally={"sheets": 1, "verdicts": 5}, **kwargs
        )

    def test_it_survives_serialisation(self, tmp_path):
        out = tmp_path / "null.json"
        out.write_text(json.dumps(self._payload(), indent=2))
        again = json.loads(out.read_text())
        assert again["provenance"]["measurement"] == "run_to_run_noise"
        assert again["judges"]["model:x"]["trials"] == 2

    def test_an_abstention_is_recorded_as_a_verdict_not_as_a_missing_value(self):
        # `null` in an answer list reads as "we have no data for this case". The judge
        # said it could not tell, which is a different thing and is one of the answers
        # whose flipping this stage counts.
        answers = self._payload()["judges"]["model:x"]["answers"]["p1"]["answers"]
        assert answers == ["false", "abstain"]
        assert None not in answers

    def test_the_held_out_cases_are_counted_rather_than_filtered_away(self):
        # The corpus here has one `unclear` case, which is judged and not scored. Filtering
        # to the scoreable cases before counting wrote `held_out_unclear: 0` into the file
        # -- a zero that reads as "there were none" rather than as "not counted", which is
        # the exact class of quiet false claim this project exists to find.
        balance = self._payload()["provenance"]["balance"]
        assert balance["held_out_unclear"] == 1
        assert balance["scoreable"] == 4

    def test_the_kind_of_width_is_named_in_the_file(self):
        # A 3-trial width and a 10-trial width are not the same quantity, and a later
        # session comparing two null runs has to be able to see that from the file.
        provenance = self._payload(extra={"trials": 2})["provenance"]
        assert "LOWER BOUND" in provenance["width_is"]
        assert provenance["trials"] == 2

    def test_the_cache_bypass_and_the_trial_order_are_recorded(self):
        provenance = self._payload()["provenance"]
        assert "one cache directory per trial" in provenance["cache_bypass"]
        assert "sequential" in provenance["trial_order"]
        assert "contexts" in provenance["held_constant"]

    def test_the_per_case_matrix_is_in_the_file_and_the_effect_is_named(self):
        judge = self._payload()["judges"]["model:x"]
        assert set(judge["answers"]) == {"p1", "p2", "n1", "n2"}
        assert "minimum_detectable_effect_f1" in judge
        assert judge["deterministic_by_construction"] is False


class TestTheSubcommand:
    def test_one_trial_is_refused_rather_than_clamped(self, capsys):
        # A single pass has no width at all, so printing 0.000 from one would be the
        # most convincing wrong answer this harness could produce. Refused before the
        # corpus is even loaded.
        args = _parser().parse_args(["judge-null-run", "--trials", "1"])
        assert _cmd_null_run(args) == 1
        assert "at least 2" in capsys.readouterr().err

    def test_the_default_trial_count_is_the_published_floor(self):
        args = _parser().parse_args(["judge-null-run"])
        assert args.trials == DEFAULT_TRIALS
        assert DEFAULT_TRIALS >= 3

    def test_the_help_says_the_default_is_a_floor_and_not_a_recommendation(self):
        action = next(
            a for a in _subparser("judge-null-run")._actions if a.dest == "trials"
        )
        assert "FLOOR" in (action.help or "")

    def test_it_takes_one_arm_where_the_eval_takes_several(self):
        # A second arm multiplies the bill by a factor that buys a different question,
        # and the width every other result needs is the width on its own arm.
        args = _parser().parse_args(["judge-null-run"])
        assert isinstance(args.arm, str)
        assert not hasattr(args, "arms")

    def test_every_flag_inside_the_cache_key_is_shared_with_the_eval(self):
        # The flags below are all inside the cache key, so a null run whose defaults had
        # drifted from the eval's would report the run-to-run width of a harness that
        # produced none of the results the width is quoted against. Same values, not
        # merely same names.
        inside_the_key = (
            "judges", "model", "k", "code_budget", "doc_budget", "claim_batch",
            "max_tokens", "retry_max_tokens", "effort", "lexical_thresholds",
        )
        ev = vars(_parser().parse_args(["judge-eval"]))
        null = vars(_parser().parse_args(["judge-null-run"]))
        for flag in inside_the_key:
            assert flag in null, flag
            assert null[flag] == ev[flag], flag

    def test_the_two_trial_counts_are_told_apart_in_the_help(self):
        # `--null-trials` draws 200 free coins for the chance control; `--trials` calls
        # the model. Confusing them is a four-figure mistake in one direction and a
        # meaningless measurement in the other.
        actions = {a.dest: a for a in _subparser("judge-null-run")._actions}
        assert "`--trials`" in (actions["null_trials"].help or "")
        assert actions["null_trials"].default == 200
