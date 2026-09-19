"""The command-line surface, and the one bug in it that was the project's own subject.

`AnthropicJudge`'s no-key error told the reader to run `--judges floors`. There was no
`floors` value: argparse would have rejected it. A false claim about the code, in the
error path of a tool built to find false claims about code -- and the test covering that
message asserted `match="floors"`, so it passed on the word while the instruction was
unrunnable.

Matching prose against prose is the mistake. These tests build the real parser and check
the message against what it accepts, which is the only version of the check that keeps
working when either side moves.
"""

from __future__ import annotations

import argparse
import builtins
import json
import re
import tomllib
from pathlib import Path

import pytest

from driftwood.judge.cases import JudgeCase
from driftwood.judge.claims import DEFAULT_BATCH
from driftwood.judge.cli import (
    FREE_JUDGES,
    JUDGE_CHOICES,
    _build_judges,
    _cmd_eval,
    _expand_groups,
    _expand_only_cases,
    _is_paid,
    _judge_arg,
    _model_from_judges,
    add_parser,
)
from driftwood.judge.context import CODE_BUDGET, DOC_BUDGET, CodeFile, JudgeContext
from driftwood.judge.evaluate import (
    CHARS_PER_TOKEN,
    estimate_spend,
    format_spend,
    measured_spend,
)
from driftwood.judge.judge import (
    DEFAULT_MAX_TOKENS,
    SYSTEM_PROMPT,
    AnthropicJudge,
    Judgement,
    PerClaimJudge,
)

# Commands a reader could paste, which is why the message backticks them. Reading
# `--judges` to end-of-words instead was the first attempt and it captured the prose
# after the flag ("floors to get the") as more flag values. A quoted span has an end;
# a sentence does not.
_QUOTED_COMMAND = re.compile(r"`(driftwood [^`]+)`")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftwood")
    add_parser(parser.add_subparsers(dest="command"))
    return parser


def _eval_parser() -> argparse.ArgumentParser:
    return _parser()._subparsers._group_actions[0].choices["judge-eval"]


def _provenance(payload: dict) -> dict:
    """Read the provenance block off a written score file rather than a returned dict.

    Through the file, because that is what a later session reads. A test on the dict
    handed to `to_json` would pass on a field that never survived serialisation.
    """
    return payload["provenance"]


# The estimate, read back off the preflight notice. Through the printed line rather
# than by calling `estimate_spend` again, because the thing under test is what the RUN
# prices -- an assertion against a second call to the same function would pass while the
# run priced something else entirely.
_ESTIMATED_TOKENS = re.compile(r"~([\d,]+) input tokens")


def _estimated_tokens(text: str) -> int:
    found = _ESTIMATED_TOKENS.search(text)
    assert found, f"no estimate on screen in:\n{text}"
    return int(found.group(1).replace(",", ""))


def _claim_reply(*rows: dict) -> str:
    """One batch reply: the JSON array `CLAIM_SYSTEM_PROMPT` asks for."""
    return json.dumps(list(rows))


class _ScriptedClient:
    """Answers each call with the next queued reply, and raises when it runs dry.

    Deliberately not shared with `tests/test_per_claim.py`, which has its own: this one
    exists to pre-warm a cache so the CLI can be run with no key, and a stub two files
    depend on grows options for both of them until it is a mock framework.
    """

    def __init__(self, replies) -> None:
        self.replies = list(replies)
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        index = len(self.calls)
        self.calls.append(kwargs)
        assert index < len(self.replies), f"unscripted call {index + 1}"
        reply = self.replies[index]

        class _Block:
            type = "text"
            text = reply

        class _Response:
            content = [_Block()]
            stop_reason = "end_turn"

        return _Response()


def _judge_accepts(value: str) -> bool:
    """Does `--judges` actually take this word? Asked by parsing it.

    Was `set(action.choices)` until `--judges` grew a validator that also accepts
    `model:<id>`, at which point `choices` became None and this helper raised instead of
    reporting. Trying the parse is the version that does not care how the check is
    implemented -- and it is what the callers below were really asking.
    """
    try:
        _eval_parser().parse_args(["--judges", value])
    except SystemExit:
        return False
    return True


def _judge_choices() -> set[str]:
    """The documented choices that the parser really accepts."""
    return {name for name in JUDGE_CHOICES if _judge_accepts(name)}


def _no_key_message(monkeypatch) -> str:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # `preflight()` rather than construction: the client is built on the first cache
    # miss now, so that a cached arm can be re-read with no key. The message is the
    # same message and these tests are about its quality, not about when it fires.
    with pytest.raises(RuntimeError) as raised:
        AnthropicJudge().preflight()
    return str(raised.value)


class TestTheHelpAndTheErrorsNameFlagsThatExist:
    def test_the_no_key_error_names_a_command(self, monkeypatch):
        assert _QUOTED_COMMAND.findall(_no_key_message(monkeypatch)), (
            "the error must tell the reader what to run instead, in backticks so the "
            "command is separable from the sentence"
        )

    def test_every_command_it_suggests_parses(self, monkeypatch):
        # Take the message at its word and feed the whole command to argparse. This is
        # the check that the old `match="floors"` assertion only appeared to make: a
        # SystemExit here means the message is telling the reader to run something this
        # tool rejects.
        for command in _QUOTED_COMMAND.findall(_no_key_message(monkeypatch)):
            program, *argv = command.split()
            assert program == "driftwood"
            _parser().parse_args(argv)

    def test_it_does_not_suggest_the_arm_that_needs_the_missing_key(self, monkeypatch):
        # Suggesting `--judges model` to someone who has just been told they have no key
        # would be the same bug in a different costume: a runnable command that cannot
        # work for the reader being handed it.
        for command in _QUOTED_COMMAND.findall(_no_key_message(monkeypatch)):
            args = _parser().parse_args(command.split()[1:])
            assert "model" not in _expand_groups(args.judges)

    def test_every_documented_group_is_a_real_choice(self):
        assert set(JUDGE_CHOICES) <= _judge_choices()


class TestTheFloorsGroup:
    def test_it_stands_for_exactly_the_judges_that_need_no_key(self):
        assert _expand_groups(["floors"]) == set(FREE_JUDGES)

    def test_it_is_the_default_so_a_bare_run_costs_nothing(self):
        args = _parser().parse_args(["judge-eval"])
        assert _expand_groups(args.judges) == set(FREE_JUDGES)
        assert "model" not in _expand_groups(args.judges)

    def test_it_composes_with_the_model_arm(self):
        assert _expand_groups(["floors", "model"]) == {*FREE_JUDGES, "model"}

    def test_naming_a_judge_directly_still_works(self):
        assert _expand_groups(["always-false"]) == {"always-false"}

    def test_a_group_and_one_of_its_members_is_not_a_duplicate_run(self):
        # `--judges floors always-false` must not build always-false twice; judges are
        # keyed by name downstream, and a duplicated key would make one arm's table
        # disagree with its own row count.
        assert _expand_groups(["floors", "always-false"]) == set(FREE_JUDGES)


class TestTheCommandsTheReadmeShows:
    """Pasted command lines wrap, and a wrapped line runs as two broken ones.

    `--out` losing its argument, then the stray path being executed by the shell, is the
    observed failure. 115 characters is where this terminal folds.
    """

    WRAP_LIMIT = 115

    def test_the_full_model_run_fits_on_one_line(self):
        command = (
            "uv run driftwood judge-eval --arms oracle retrieved "
            "--judges floors model --out data/scores/judge-model.json"
        )
        assert len(command) <= self.WRAP_LIMIT
        _parser().parse_args(command.split()[3:])


class TestPricingTheRunBeforePayingForIt:
    """The estimate exists because the first version of this number was arithmetic I
    did in a scratch script and reported in prose. A cost figure that lives outside
    the tool cannot be re-checked, and cannot be wrong in public.
    """

    def test_it_measures_the_prompts_rather_than_counting_cases(self):
        # Prompts here span 20x in size -- a doc at the character budget against a
        # one-line README. A per-case multiplier would be wrong by that factor on any
        # arm whose mix differs from the one it was calibrated on.
        small = estimate_spend(["x" * 100], system="", max_tokens=700)
        large = estimate_spend(["x" * 100_000], system="", max_tokens=700)
        assert small["calls"] == large["calls"] == 1
        assert large["input_tokens_approx"] > 900 * small["input_tokens_approx"]

    def test_the_output_bound_follows_the_reply_budget(self):
        assert estimate_spend(["x"] * 10, system="", max_tokens=700)["output_tokens_high"] == 7000
        assert estimate_spend(["x"] * 10, system="", max_tokens=50)["output_tokens_high"] == 500

    def test_it_reports_tokens_and_never_dollars(self):
        # A hardcoded price is a claim about the world that goes stale silently, which
        # is the failure this whole project is built to detect. If a currency symbol
        # ever appears here, the tool has started making the mistake it looks for.
        rendered = format_spend(estimate_spend(["x" * 5000], system="", max_tokens=700))
        assert "$" not in rendered and "USD" not in rendered.upper()
        assert "input tokens" in rendered

    def test_an_empty_arm_does_not_divide_by_zero(self):
        got = estimate_spend([], system="", max_tokens=700)
        assert got["calls"] == 0 and got["longest_prompt_chars"] == 0
        assert "0 call(s)" in format_spend(got)


class TestTheEstimateIsCheckedAgainstTheBill:
    def _judgements(self, **kwargs):
        return {
            "c1": Judgement(
                example_id="c1", arm="retrieved", judge="model:m", answer=False, **kwargs
            )
        }

    def test_usage_absent_is_unknown_and_not_zero(self):
        # A free judge, or a reply cached before usage was recorded. Summing those as
        # zero would make a fully cached run report itself as costing nothing, which is
        # true of the bill and false of the measurement.
        got = measured_spend(self._judgements())
        assert got["calls_measured"] == 0
        assert got["unknown"] == 1
        assert got["input_tokens"] == 0

    # A prompt that the heuristic estimates at exactly 1,000 tokens, derived from the
    # constant rather than written as 3600. These two tests hardcoded a length that was
    # only right while CHARS_PER_TOKEN was 3.6, so recalibrating it against a real bill
    # broke them -- a test coupled to the value of the thing it is measuring with. The
    # arithmetic is the invariant; 3.6 was not.
    EXACTLY_1000_TOKENS = "x" * round(1000 * CHARS_PER_TOKEN)

    def test_a_measured_run_reports_the_heuristics_error(self):
        judgements = self._judgements(input_tokens=1000, output_tokens=200)
        rendered = format_spend(
            estimate_spend([self.EXACTLY_1000_TOKENS], system="", max_tokens=700),
            measured_spend(judgements),
        )
        assert "billed: 1,000 input + 200 output" in rendered
        assert "+0.0%" in rendered

    def test_an_overestimate_is_reported_as_positive_error(self):
        judgements = self._judgements(input_tokens=500, output_tokens=10)
        rendered = format_spend(
            estimate_spend([self.EXACTLY_1000_TOKENS], system="", max_tokens=700),
            measured_spend(judgements),
        )
        assert "+100.0%" in rendered

    def test_cached_replies_are_called_out(self):
        judgements = {
            "c1": Judgement(
                example_id="c1", arm="retrieved", judge="model:m", answer=False,
                input_tokens=10, output_tokens=2, cached=True,
            )
        }
        rendered = format_spend(estimate_spend(["x" * 36], system="", max_tokens=700), measured_spend(judgements))
        assert "served from cache" in rendered


class TestTheTokenBudgetRefusesBeforeSending:
    def test_the_flag_exists_and_defaults_to_off(self):
        args = _parser().parse_args(["judge-eval"])
        assert args.max_input_tokens == 0

    def test_the_budget_is_in_tokens_not_currency(self):
        # Same reason the report is. A dollar budget would need a price table in the
        # repo, and a price table in the repo is a stale claim waiting to happen.
        args = _parser().parse_args(["judge-eval", "--max-input-tokens", "50000"])
        assert args.max_input_tokens == 50_000

    def test_the_reply_budget_the_estimate_multiplies_by_is_the_one_used(self):
        # If --max-tokens and the judge's own default drift apart, the estimate is
        # wrong in the direction that looks safe.
        args = _parser().parse_args(["judge-eval"])
        assert args.max_tokens == DEFAULT_MAX_TOKENS


class TestTheMissingDependencyMessage:
    """The no-key message's sibling, and the same failure was available to it.

    A bare ModuleNotFoundError is a dead end for the reader, and it lands at the worst
    moment: key set, run started, nothing said about the command that fixes it. So the
    message names an extra -- and an extra named in prose can be as fictional as a flag
    named in prose, which is what makes the pyproject check below the point of this class.
    """

    def _message(self, monkeypatch) -> str:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
        real_import = builtins.__import__

        def no_anthropic(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_anthropic)
        with pytest.raises(RuntimeError) as raised:
            AnthropicJudge().preflight()
        return str(raised.value)

    def test_it_explains_rather_than_raising_modulenotfounderror(self, monkeypatch):
        message = self._message(monkeypatch)
        assert "uv sync --extra judge" in message
        assert "floors" in message, "it should say the free half needs neither"

    def test_the_extra_it_names_is_declared_in_pyproject(self, monkeypatch):
        # The dependency-side version of "does the flag exist". Read the manifest rather
        # than trusting the sentence: `--extra judge` is as unrunnable as `--judges
        # floors` was if nothing declares it.
        named = set(re.findall(r"--extra ([a-z0-9-]+)", self._message(monkeypatch)))
        assert named

        manifest = tomllib.loads(
            (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )
        declared = set(manifest["project"]["optional-dependencies"])
        assert named <= declared, f"{named - declared} is not a declared extra"


class TestTheSystemPromptIsBilledToo:
    """The estimate's own bug, and it was wrong in the direction that looks cheap.

    The first version summed the rendered prompts only. The system prompt is 1,395
    characters resent on every call, so the 45-case oracle arm read 11% under. An
    estimate that errs cheap is worse than none: it is the number you check *because*
    you are about to spend, and it quietly tells you to go ahead.
    """

    def test_it_is_counted_once_per_call(self):
        without = estimate_spend(["x" * 1000], system="", max_tokens=700)
        with_system = estimate_spend(["x" * 1000], system="y" * 500, max_tokens=700)
        assert with_system["input_chars"] - without["input_chars"] == 500

        ten = estimate_spend(["x" * 1000] * 10, system="y" * 500, max_tokens=700)
        assert ten["input_chars"] - 10 * 1000 == 10 * 500, "per call, not per run"

    def test_the_longest_prompt_includes_it(self):
        got = estimate_spend(["x" * 1000], system="y" * 500, max_tokens=700)
        assert got["longest_prompt_chars"] == 1500

    def test_the_caller_cannot_forget_it(self):
        # Keyword-only and no default. A default of "" is how the first version got it
        # wrong, and a silently-zero overhead is unobservable in the output.
        with pytest.raises(TypeError):
            estimate_spend(["x"], max_tokens=700)  # type: ignore[call-arg]

    def test_the_real_system_prompt_moves_the_real_arm_materially(self):
        # Pinned as a proportion rather than a character count, so editing the prompt
        # does not fail this test while still failing to be counted.
        prompts = ["x" * 13_000] * 45
        under = estimate_spend(prompts, system="", max_tokens=700)
        correct = estimate_spend(prompts, system=SYSTEM_PROMPT, max_tokens=700)
        shortfall = 1 - under["input_tokens_approx"] / correct["input_tokens_approx"]
        assert shortfall > 0.05, "the omission was worth more than a rounding error"

    def test_the_report_says_the_overhead_is_per_call(self):
        rendered = format_spend(
            estimate_spend(["x" * 1000] * 3, system=SYSTEM_PROMPT, max_tokens=700)
        )
        assert "system prompt resent every call" in rendered


class TestSelectingCasesByIdForACheapProbe:
    """`--only-cases`, added so the 9 recall-costing cases can be re-asked for ~$0.57
    instead of re-paying all 45 at ~$2.84.

    The flag's danger is not cost, it is interpretation: the cases are chosen *because*
    they failed, so the subset is selected on the outcome being measured and its F1 is
    meaningless. These tests pin the guard rails rather than the plumbing.
    """

    def test_the_flag_exists_and_defaults_to_off(self):
        args = _parser().parse_args(["judge-eval"])
        assert args.only_cases is None

    def test_it_takes_several_ids(self):
        args = _parser().parse_args(["judge-eval", "--only-cases", "aaa", "bbb"])
        assert args.only_cases == ["aaa", "bbb"]

    def test_the_help_says_it_is_not_a_result(self):
        for action in _eval_parser()._actions:
            if action.dest == "only_cases":
                assert "NOT A RESULT" in (action.help or "")
                return
        raise AssertionError("judge-eval has no --only-cases argument")

    def test_an_at_file_is_read_one_id_per_line(self, tmp_path):
        ids = tmp_path / "ids.txt"
        ids.write_text("aaa\n\n# the two drift abstentions\nbbb\nccc  # trailing\n")
        assert _expand_only_cases([f"@{ids}"]) == {"aaa", "bbb", "ccc"}

    def test_bare_ids_and_a_file_compose(self, tmp_path):
        ids = tmp_path / "ids.txt"
        ids.write_text("bbb\n")
        assert _expand_only_cases(["aaa", f"@{ids}"]) == {"aaa", "bbb"}

    def test_a_repeated_id_is_not_two_cases(self, tmp_path):
        ids = tmp_path / "ids.txt"
        ids.write_text("aaa\n")
        assert _expand_only_cases(["aaa", f"@{ids}"]) == {"aaa"}

    def _one_case_loaded(self, monkeypatch):
        """A loader that yields exactly one case, id `aaa`, with no code side.

        No `code_path` on purpose: the oracle arm then skips it before any clone or
        context build, so these tests exercise the selection and the provenance block
        without git, a network, or a judge.
        """
        case = JudgeCase(
            example_id="aaa", repo="acme/widget", shape="B", basis="b",
            doc_path="docs/x.rst", code_path=None, at_sha="a", fix_sha="f",
            subject="s", shared_identifiers=(), verdict="drift", sheet="s.md",
            resolved_from="labels.jsonl",
        )
        monkeypatch.setattr(
            "driftwood.judge.cli.load_cases", lambda *a, **k: ([case], {})
        )
        monkeypatch.setattr(
            "driftwood.judge.cli.format_case_report", lambda *a, **k: ""
        )

    def test_an_unknown_id_is_refused_rather_than_skipped(self, monkeypatch, capsys):
        # The failure this prevents: a mistyped id selects fewer cases than asked for and
        # the run reports a confident number over a set nobody chose. Same shape as the
        # `retried` bug -- a false claim about the run, printed by the tool built to find
        # false claims about code.
        self._one_case_loaded(monkeypatch)
        args = _parser().parse_args(["judge-eval", "--only-cases", "aaa", "typo"])
        assert _cmd_eval(args) == 1
        assert "typo" in capsys.readouterr().err

    def test_it_refuses_before_any_judge_is_built(self, monkeypatch):
        # Ordering matters for cost: the refusal has to land before a client could be
        # constructed, so a typo cannot reach the API even with --judges model.
        self._one_case_loaded(monkeypatch)
        monkeypatch.setattr(
            "driftwood.judge.cli._build_judges",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("built a judge")),
        )
        args = _parser().parse_args(["judge-eval", "--only-cases", "typo"])
        assert _cmd_eval(args) == 1

    def test_the_chosen_ids_are_recorded_not_just_their_count(self, monkeypatch, tmp_path):
        # A score file is the measurement history. "1 case" in a provenance block cannot
        # distinguish a deliberate probe from a run that lost 44 cases to a loader bug,
        # which is the mistake the frozen join table exists for. So the ids go in, sorted.
        self._one_case_loaded(monkeypatch)
        out = tmp_path / "probe.json"
        args = _parser().parse_args(
            ["judge-eval", "--arms", "oracle", "--only-cases", "bbb", "aaa",
             "--out", str(out)]
        )
        # `bbb` is not loaded, so this must refuse rather than write a file scoring one
        # case under a name claiming two.
        assert _cmd_eval(args) == 1
        assert not out.exists()

        args = _parser().parse_args(
            ["judge-eval", "--arms", "oracle", "--only-cases", "aaa",
             "--out", str(out)]
        )
        assert _cmd_eval(args) == 0
        written = json.loads(out.read_text(encoding="utf-8"))
        assert _provenance(written)["only_cases"] == ["aaa"]

    def test_the_code_budget_is_recorded_so_a_score_says_which_harness_made_it(
        self, monkeypatch, tmp_path
    ):
        # The probe changes the budget, and the budget is inside the cache key. Two score
        # files over the same cases at different budgets are two different measurements,
        # and nothing else in the payload would say which was which.
        self._one_case_loaded(monkeypatch)
        out = tmp_path / "wide.json"
        args = _parser().parse_args(
            ["judge-eval", "--arms", "oracle", "--code-budget", "36000",
             "--out", str(out)]
        )
        assert _cmd_eval(args) == 0
        assert _provenance(json.loads(out.read_text(encoding="utf-8")))["code_budget"] == 36_000

    def test_the_code_budget_defaults_to_the_published_constant(self):
        # Every score already in `data/scores/` was produced at this value. A default
        # that drifted from it would make a re-run measure a different harness and say
        # nothing about having done so.
        args = _parser().parse_args(["judge-eval"])
        assert args.code_budget == CODE_BUDGET

    def test_the_code_budget_help_warns_that_it_re_pays_the_cache(self):
        for action in _eval_parser()._actions:
            if action.dest == "code_budget":
                assert "CACHE KEY" in (action.help or "")
                return
        raise AssertionError("judge-eval has no --code-budget argument")

    def test_a_run_without_the_flag_records_it_as_absent_not_as_every_id(
        self, monkeypatch, tmp_path
    ):
        # `null` rather than the full id list, so a reader of the score file can tell a
        # whole-corpus run from a probe that happened to select everything.
        self._one_case_loaded(monkeypatch)
        out = tmp_path / "full.json"
        args = _parser().parse_args(
            ["judge-eval", "--arms", "oracle", "--out", str(out)]
        )
        assert _cmd_eval(args) == 0
        assert _provenance(json.loads(out.read_text(encoding="utf-8")))["only_cases"] is None


class TestTheDocumentBudgetFlag:
    """The lever the earlier diagnosis missed, so it gets the same treatment as `--k`
    and `--code-budget`: a flag, recorded in provenance, defaulting to the constant every
    published score was produced at.
    """

    def test_it_defaults_to_the_published_constant(self):
        assert _parser().parse_args(["judge-eval"]).doc_budget == DOC_BUDGET

    def test_it_is_separate_from_the_code_budget(self):
        args = _parser().parse_args(
            ["judge-eval", "--doc-budget", "40000", "--code-budget", "9000"]
        )
        assert (args.doc_budget, args.code_budget) == (40_000, 9_000)

    def test_the_help_warns_that_it_re_pays_the_cache(self):
        for action in _eval_parser()._actions:
            if action.dest == "doc_budget":
                assert "CACHE KEY" in (action.help or "")
                return
        raise AssertionError("judge-eval has no --doc-budget argument")


class TestPastingAJudgeNameBackIn:
    """The form the reports print must be runnable, because it is what gets pasted.

    Written after a probe was typed with `--judges model:claude-sonnet-5`, copied from a
    score file, and rejected by argparse -- which exits before the spend preflight, so the
    terminal showed a usage message where a result was expected and the run looked done.
    """

    def test_the_bare_choice_still_works(self):
        args = _eval_parser().parse_args(["--judges", "model"])
        assert args.judges == ["model"]

    def test_the_form_the_reports_print_is_accepted(self):
        args = _eval_parser().parse_args(["--judges", "model:claude-sonnet-5"])
        assert args.judges == ["model:claude-sonnet-5"]
        assert _expand_groups(args.judges) == {"model"}
        assert _model_from_judges(args.judges, "unused-fallback") == "claude-sonnet-5"

    def test_an_inline_id_beats_the_model_flag(self):
        # Rather than the other way round: the inline form is the more specific of the
        # two, and it is the one the person typed most recently.
        args = _eval_parser().parse_args(
            ["--judges", "model:claude-opus-5", "--model", "claude-sonnet-5"]
        )
        assert _model_from_judges(args.judges, args.model) == "claude-opus-5"

    def test_the_model_flag_is_the_fallback_when_nothing_is_inline(self):
        args = _eval_parser().parse_args(["--judges", "model", "--model", "claude-opus-5"])
        assert _model_from_judges(args.judges, args.model) == "claude-opus-5"

    def test_it_composes_with_a_group(self):
        args = _eval_parser().parse_args(["--judges", "floors", "model:claude-sonnet-5"])
        assert _expand_groups(args.judges) == {*FREE_JUDGES, "model"}
        assert _model_from_judges(args.judges, "x") == "claude-sonnet-5"

    def test_two_inline_models_are_refused_rather_than_silently_picked(self):
        # One score file describes one model. Picking either would write a provenance
        # block that disagrees with half the cache keys the run created.
        args = _eval_parser().parse_args(
            ["--judges", "model:claude-sonnet-5", "model:claude-opus-5"]
        )
        with pytest.raises(SystemExit) as excinfo:
            _model_from_judges(args.judges, "x")
        assert "more than one model" in str(excinfo.value)

    def test_a_bare_colon_is_refused(self):
        with pytest.raises(SystemExit):
            _eval_parser().parse_args(["--judges", "model:"])

    def test_an_unknown_judge_is_still_refused(self):
        with pytest.raises(SystemExit):
            _eval_parser().parse_args(["--judges", "always-maybe"])

    def test_the_refusal_names_the_inline_form_as_a_way_out(self):
        # The point of the change is the message, not the parse. A rejection that lists
        # only the bare choices is what sent someone looking for a flag that was there.
        with pytest.raises(argparse.ArgumentTypeError) as excinfo:
            _judge_arg("sonnet")
        assert "model:<id>" in str(excinfo.value)


class TestTheScoreFileRecordsEverythingInTheCacheKey:
    """A score file has to say which harness produced it, and the reply budget is part of
    that harness. Two runs of the same probe -- one with `--retry-max-tokens 12000`, one
    without -- came out with 2 truncated replies against 0, a different confusion matrix,
    and nothing in either provenance block to tell them apart.
    """

    def _written(self, tmp_path, monkeypatch, argv):
        case = JudgeCase(
            example_id="aaa", repo="acme/widget", shape="B", basis="b",
            doc_path="docs/x.rst", code_path=None, at_sha="a", fix_sha="f",
            subject="s", shared_identifiers=(), verdict="drift", sheet="s.md",
            resolved_from="labels.jsonl",
        )
        monkeypatch.setattr(
            "driftwood.judge.cli.load_cases", lambda *a, **k: ([case], {})
        )
        monkeypatch.setattr("driftwood.judge.cli.format_case_report", lambda *a, **k: "")
        out = tmp_path / "probe.json"
        args = _eval_parser().parse_args([*argv, "--arms", "oracle", "--out", str(out)])
        assert _cmd_eval(args) == 0
        return _provenance(json.loads(out.read_text()))

    def test_the_retry_ceiling_is_recorded(self, tmp_path, monkeypatch):
        provenance = self._written(
            tmp_path, monkeypatch, ["--retry-max-tokens", "12000"]
        )
        assert provenance["retry_max_tokens"] == 12000

    def test_its_absence_is_recorded_as_absent_not_as_the_base_ceiling(
        self, tmp_path, monkeypatch
    ):
        # None, not `max_tokens`. A run that never retried and a run that retried at its
        # own ceiling reach different cache keys, and reading the second off the first is
        # how a truncated reply gets counted as an answer.
        provenance = self._written(tmp_path, monkeypatch, [])
        assert provenance["retry_max_tokens"] is None
        assert provenance["max_tokens"] == DEFAULT_MAX_TOKENS

    def test_the_effort_setting_is_recorded(self, tmp_path, monkeypatch):
        provenance = self._written(tmp_path, monkeypatch, ["--effort", "high"])
        assert provenance["effort"] == "high"

    def test_every_flag_inside_the_cache_key_reaches_the_score_file(
        self, tmp_path, monkeypatch
    ):
        # The list, stated once. `context_hash` takes the rendered context plus the
        # request dict, so the key is: what shapes the context (k, both budgets, the
        # chosen cases) and what shapes the call (both ceilings, effort). A flag added to
        # either half without a provenance entry makes a score file unattributable.
        provenance = self._written(tmp_path, monkeypatch, [])
        for field in (
            "k", "code_budget", "doc_budget", "only_cases",
            "max_tokens", "retry_max_tokens", "effort",
        ):
            assert field in provenance, f"{field} is in the cache key but not the score file"


class TestTheSecondPaidJudgeIsRecognisedAsPaid:
    """`per-claim` costs money, and the preflight is the only thing between a mis-set flag
    and a bill. A spend check that silently does not recognise a paid judge is the one bug
    in this file that cannot be caught by reading the output afterwards -- by then it has
    been paid for.
    """

    def test_it_is_a_judge_choice_and_takes_the_inline_form_the_reports_print(self):
        assert "per-claim" in JUDGE_CHOICES
        assert _judge_accepts("per-claim")
        assert _judge_accepts("per-claim:claude-sonnet-5")

    def test_the_inline_form_expands_to_the_judge_and_names_the_model(self):
        args = _eval_parser().parse_args(["--judges", "per-claim:claude-sonnet-5"])
        assert _expand_groups(args.judges) == {"per-claim"}
        assert _model_from_judges(args.judges, "unused") == "claude-sonnet-5"

    def test_a_bare_colon_is_refused_here_too(self):
        with pytest.raises(SystemExit):
            _eval_parser().parse_args(["--judges", "per-claim:"])

    def test_naming_two_models_across_the_two_paid_judges_is_refused(self):
        # The same rule as two inline `model:` ids, and the case that would slip through a
        # check written only against one prefix: one score file describes one model.
        args = _eval_parser().parse_args(
            ["--judges", "model:claude-sonnet-5", "per-claim:claude-opus-5"]
        )
        with pytest.raises(SystemExit) as excinfo:
            _model_from_judges(args.judges, "x")
        assert "more than one model" in str(excinfo.value)

    def test_both_paid_judges_together_expand_to_both(self):
        args = _eval_parser().parse_args(["--judges", "floors", "model", "per-claim"])
        assert _expand_groups(args.judges) == {*FREE_JUDGES, "model", "per-claim"}

    @pytest.mark.parametrize(
        "name,paid",
        [
            ("model:claude-sonnet-5", True),
            ("model:claude-sonnet-5(high)", True),
            ("per-claim/8:claude-sonnet-5", True),
            ("per-claim/8:claude-sonnet-5(high)", True),
            ("always-not-false", False),
            ("always-false", False),
            ("lexical-absence(>=3)", False),
        ],
    )
    def test_the_paid_test_matches_the_names_the_judges_actually_carry(self, name, paid):
        # Against the built names rather than the flag words, because that is what
        # `_cmd_eval` iterates. `per-claim/8:...` does not start with `per-claim:`, which
        # is why the prefix tuple holds the bare word.
        assert _is_paid(name) is paid

    def test_the_built_judge_carries_the_batch_size_from_the_flag(self):
        args = _eval_parser().parse_args(
            ["--judges", "per-claim:m", "--claim-batch", "4"]
        )
        judges = _build_judges(args)
        assert "per-claim/4:m" in judges
        assert judges["per-claim/4:m"].batch_size == 4

    def test_the_batch_size_defaults_to_the_size_the_pricing_was_read_at(self):
        # Every number in the plan file's pricing table is at 8. A default that drifted
        # would make the arm that gets built a different arm from the one that was priced.
        assert _eval_parser().parse_args([]).claim_batch == DEFAULT_BATCH

    def test_the_batch_size_help_warns_that_it_re_asks_everything(self):
        for action in _eval_parser()._actions:
            if action.dest == "claim_batch":
                assert "cache key" in (action.help or "")
                return
        raise AssertionError("judge-eval has no --claim-batch argument")


class TestThePerClaimArmEndToEndOffACachedRun:
    """One case, judged per claim, with no key at all -- the arm's replies pre-cached.

    Everything after the call is what this exercises, and it is the half that cannot be
    checked by reading `judge.py`: whether the estimate is priced per judge, whether the
    located row reaches the table and the score file, and whether the provenance block
    records the batch size that was in the cache key.
    """

    _DOC = (
        "The `connect` helper opens a socket.\n"
        "\n"
        "The `timeout` setting defaults to 30 seconds.\n"
    )

    def _case(self):
        return JudgeCase(
            example_id="aaa", repo="acme/widget", shape="A", basis="b",
            doc_path="docs/x.rst", code_path="src/c.py", at_sha="a", fix_sha="f",
            subject="s", shared_identifiers=("timeout",), verdict="drift",
            sheet="s.md", resolved_from="labels.jsonl",
        )

    def _context(self):
        return JudgeContext(
            example_id="aaa", repo="acme/widget", arm="oracle", doc_path="docs/x.rst",
            doc_text=self._DOC, doc_truncated=False, at_sha="a",
            code_files=(CodeFile("src/c.py", "def connect(): ...", False, None),),
            pool_size=1, doc_full=self._DOC,
        )

    def _run(self, tmp_path, monkeypatch, *, replies, argv=()):
        """Pre-warm the cache with `replies`, then run the CLI with no key.

        The pre-warm uses the same cache directory, model, ceiling and batch size as the
        run, so every call is a hit. Deleting the key is what makes that a claim rather
        than an assumption: a miss here raises instead of quietly costing money.
        """
        case = self._case()
        context = self._context()
        cache = tmp_path / "cache"
        monkeypatch.setattr(
            "driftwood.judge.cli.load_cases", lambda *a, **k: ([case], {})
        )
        monkeypatch.setattr("driftwood.judge.cli.format_case_report", lambda *a, **k: "")

        class _Builder:
            def __init__(self, *a, **k) -> None:
                pass

            def build(self, case, arm):
                return context

        monkeypatch.setattr("driftwood.judge.cli.ContextBuilder", _Builder)

        warm = PerClaimJudge(
            client=_ScriptedClient(replies), cache_dir=cache, model="m",
            batch_size=1,
        )
        warm.judge(context)

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        out = tmp_path / "probe.json"
        args = _eval_parser().parse_args(
            [
                "--judges", "per-claim:m", "--claim-batch", "1",
                "--arms", "oracle", "--cache", str(cache),
                "--null-trials", "5", "--out", str(out), *argv,
            ]
        )
        assert _cmd_eval(args) == 0
        return json.loads(out.read_text(encoding="utf-8"))

    def _both_rows(self, payload):
        return payload["arms"]["oracle"]["judges"]

    def test_the_located_row_sits_beside_the_aggregate_one(self, tmp_path, monkeypatch):
        # One axis, not a separate report. The whole difficulty with construct validity is
        # that it is invisible next to a number that looks fine, so the two rows go in the
        # same table against the same floors.
        payload = self._run(
            tmp_path, monkeypatch,
            replies=[
                _claim_reply({"n": 1, "verdict": "false", "reason": "no connect"}),
                _claim_reply({"n": 1, "verdict": "not-false", "reason": "fine"}),
            ],
        )
        rows = self._both_rows(payload)
        assert "per-claim/1:m" in rows
        assert "per-claim/1:m [located]" in rows

    def test_a_flag_the_label_cannot_speak_to_is_held_out_not_scored_wrong(
        self, tmp_path, monkeypatch
    ):
        # `shared_identifiers` is `("timeout",)`, so a flag on the `connect` sentence is a
        # verdict the label says nothing about. Aggregate: a true positive on a `drift`
        # case. Located: an abstention, and the case stays in `n`.
        payload = self._run(
            tmp_path, monkeypatch,
            replies=[
                _claim_reply({"n": 1, "verdict": "false", "reason": "no connect"}),
                _claim_reply({"n": 1, "verdict": "not-false", "reason": "fine"}),
            ],
        )
        rows = self._both_rows(payload)
        assert rows["per-claim/1:m"]["abstained"] == 0
        assert rows["per-claim/1:m [located]"]["abstained"] == 1
        assert rows["per-claim/1:m [located]"]["n"] == rows["per-claim/1:m"]["n"]

    def test_a_flag_on_the_labelled_sentence_survives_both_scorings(
        self, tmp_path, monkeypatch
    ):
        payload = self._run(
            tmp_path, monkeypatch,
            replies=[
                _claim_reply({"n": 1, "verdict": "not-false", "reason": "fine"}),
                _claim_reply({"n": 1, "verdict": "false", "reason": "timeout is 5"}),
            ],
        )
        rows = self._both_rows(payload)
        assert rows["per-claim/1:m"]["f1"] == rows["per-claim/1:m [located]"]["f1"]
        assert rows["per-claim/1:m [located]"]["abstained"] == 0

    def test_the_located_row_is_free(self, tmp_path, monkeypatch):
        # No call is made for it. If it cost anything the two scorings would be a choice
        # rather than both, and the construct-validity number is the one that would lose.
        payload = self._run(
            tmp_path, monkeypatch,
            replies=[
                _claim_reply({"n": 1, "verdict": "false", "reason": "no connect"}),
                _claim_reply({"n": 1, "verdict": "not-false", "reason": "fine"}),
            ],
        )
        # The assertion is that the run finished at all: `_run` deletes the key, so a
        # single cache miss would have raised rather than returned a score file. Both rows
        # are therefore in that file having cost nothing beyond the two replies the
        # aggregate row already needed.
        rows = self._both_rows(payload)
        assert set(rows) == {"per-claim/1:m", "per-claim/1:m [located]"}

    def test_the_batch_size_is_recorded_in_the_provenance(self, tmp_path, monkeypatch):
        payload = self._run(
            tmp_path, monkeypatch,
            replies=[
                _claim_reply({"n": 1, "verdict": "not-false"}),
                _claim_reply({"n": 1, "verdict": "not-false"}),
            ],
        )
        assert _provenance(payload)["claim_batch"] == 1

    def test_a_run_with_no_per_claim_judge_records_it_as_absent(
        self, tmp_path, monkeypatch
    ):
        # Null rather than the default. A recorded 8 on a run that had no per-claim arm
        # reads as a setting that was in force, which is the `retry_max_tokens: 0` mistake
        # in a different field.
        case = JudgeCase(
            example_id="aaa", repo="acme/widget", shape="B", basis="b",
            doc_path="docs/x.rst", code_path=None, at_sha="a", fix_sha="f",
            subject="s", shared_identifiers=(), verdict="drift", sheet="s.md",
            resolved_from="labels.jsonl",
        )
        monkeypatch.setattr(
            "driftwood.judge.cli.load_cases", lambda *a, **k: ([case], {})
        )
        monkeypatch.setattr("driftwood.judge.cli.format_case_report", lambda *a, **k: "")
        out = tmp_path / "free.json"
        args = _eval_parser().parse_args(["--arms", "oracle", "--out", str(out)])
        assert _cmd_eval(args) == 0
        assert _provenance(json.loads(out.read_text()))["claim_batch"] is None


class TestThePerClaimEstimateIsPricedAsItsOwnJudge:
    """A single estimate for the arm would under-read the per-claim judge by its batch
    count -- 168 calls against the per-page judge's 45 on the seeded arm, 3.5x -- and it
    would do it in the cheap-looking direction. That is the one direction an estimate must
    not be wrong in, and this project has made that mistake twice already: once by
    omitting the system prompt from the count, once by guessing chars-per-token high.
    """

    _DOC = (
        "The `connect` helper opens a socket.\n"
        "\n"
        "The `timeout` setting defaults to 30 seconds.\n"
        "\n"
        "The `retries` count is 3.\n"
    )

    def _setup(self, monkeypatch):
        case = JudgeCase(
            example_id="aaa", repo="acme/widget", shape="A", basis="b",
            doc_path="docs/x.rst", code_path="src/c.py", at_sha="a", fix_sha="f",
            subject="s", shared_identifiers=("timeout",), verdict="drift",
            sheet="s.md", resolved_from="labels.jsonl",
        )
        context = JudgeContext(
            example_id="aaa", repo="acme/widget", arm="oracle", doc_path="docs/x.rst",
            doc_text=self._DOC, doc_truncated=False, at_sha="a",
            code_files=(CodeFile("src/c.py", "def connect(): ...", False, None),),
            pool_size=1, doc_full=self._DOC,
        )
        monkeypatch.setattr(
            "driftwood.judge.cli.load_cases", lambda *a, **k: ([case], {})
        )
        monkeypatch.setattr("driftwood.judge.cli.format_case_report", lambda *a, **k: "")

        class _Builder:
            def __init__(self, *a, **k) -> None:
                pass

            def build(self, case, arm):
                return context

        monkeypatch.setattr("driftwood.judge.cli.ContextBuilder", _Builder)

    def _refused(self, monkeypatch, capsys, argv):
        """Run with a token cap low enough to refuse, and read the estimate off the notice.

        The refusal path is what makes this checkable without spending: the preflight
        prints its per-judge figures and then returns 1 before anything is sent.
        """
        self._setup(monkeypatch)
        args = _eval_parser().parse_args(
            ["--arms", "oracle", "--max-input-tokens", "1", *argv]
        )
        assert _cmd_eval(args) == 1
        return capsys.readouterr()

    def test_each_paid_judge_gets_its_own_line(self, monkeypatch, capsys):
        captured = self._refused(
            monkeypatch, capsys, ["--judges", "model:m", "per-claim:m"]
        )
        assert "model:m:" in captured.out
        assert "per-claim/8:m:" in captured.out

    def test_the_cap_is_checked_against_the_total_not_per_judge(self, monkeypatch, capsys):
        # Two judges each just under the cap are a bill over it, and the cap exists to
        # bound the bill.
        captured = self._refused(
            monkeypatch, capsys, ["--judges", "model:m", "per-claim:m"]
        )
        assert "across all paid judges" in captured.out
        assert "REFUSING" in captured.err

    def test_nothing_is_sent_when_it_refuses(self, monkeypatch, capsys):
        # Both paid judges are constructed, and neither may reach a client. With the key
        # deleted, a call would raise rather than return 1.
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        self._refused(monkeypatch, capsys, ["--judges", "model:m", "per-claim:m"])

    def test_a_smaller_batch_is_priced_higher_than_a_larger_one(self, monkeypatch, capsys):
        # The direction that matters: one claim per call repeats the code side once per
        # claim, so the estimate has to rise as the batch shrinks. A single per-arm
        # estimate would report these two as the same number.
        one = self._refused(
            monkeypatch, capsys, ["--judges", "per-claim:m", "--claim-batch", "1"]
        ).out
        eight = self._refused(
            monkeypatch, capsys, ["--judges", "per-claim:m", "--claim-batch", "8"]
        ).out
        assert _estimated_tokens(one) > _estimated_tokens(eight)
