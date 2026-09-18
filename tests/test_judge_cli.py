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
import re

import pytest

from driftwood.judge.cli import (
    FREE_JUDGES,
    JUDGE_CHOICES,
    _expand_groups,
    add_parser,
)
from driftwood.judge.judge import AnthropicJudge

# Commands a reader could paste, which is why the message backticks them. Reading
# `--judges` to end-of-words instead was the first attempt and it captured the prose
# after the flag ("floors to get the") as more flag values. A quoted span has an end;
# a sentence does not.
_QUOTED_COMMAND = re.compile(r"`(driftwood [^`]+)`")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftwood")
    add_parser(parser.add_subparsers(dest="command"))
    return parser


def _judge_choices() -> set[str]:
    """What `--judges` actually accepts, read off the parser rather than restated."""
    eval_parser = _parser()._subparsers._group_actions[0].choices["judge-eval"]
    for action in eval_parser._actions:
        if action.dest == "judges":
            return set(action.choices)
    raise AssertionError("judge-eval has no --judges argument")


def _no_key_message(monkeypatch) -> str:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError) as raised:
        AnthropicJudge()
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
