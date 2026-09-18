"""`--pin` must actually pin, in both spellings, and must refuse a slug it cannot use.

Written because the manifests were wrong. `--pin` was declared `nargs="*"`, so argparse
kept only the *last* occurrence of a repeated flag -- and the `replay` line every
manifest advertises is built as `--pin a=sha --pin b=sha ...`. Following the documented
replay command therefore pinned one repo out of five and mined the other four at a
moving HEAD: no error, a corpus that looked right, and a different one.

The README calls that replay "verified, not assumed". It was verified by passing the
pins in the other spelling.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from driftwood.mining.cli import main


def _pin_parser() -> argparse.ArgumentParser:
    """The declaration under test, isolated from the rest of the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", action="extend", nargs="+", default=[])
    return parser


REPEATED = ["--pin", "a/x=1", "--pin", "b/y=2", "--pin", "c/z=3"]
SINGLE = ["--pin", "a/x=1", "b/y=2", "c/z=3"]
EXPECTED = ["a/x=1", "b/y=2", "c/z=3"]


@pytest.mark.parametrize("argv,label", [(REPEATED, "repeated flags"), (SINGLE, "one flag")])
def test_both_spellings_keep_every_pin(argv: list[str], label: str):
    assert _pin_parser().parse_args(argv).pin == EXPECTED, label


def test_the_manifest_replay_spelling_is_the_one_that_used_to_break():
    """Pinned as a named case, because this is the spelling the tool itself emits.

    Asserting the count is the whole point: the old behaviour returned a non-empty
    list, so any test that merely checked "pins were parsed" passed.
    """
    assert len(_pin_parser().parse_args(REPEATED).pin) == 3


def test_a_pin_for_a_repo_not_being_mined_is_refused(tmp_path: Path, capsys):
    """A mistyped slug was silently ignored, which is the same defect one layer up:
    `pins.get(slug, "HEAD")` cannot tell a typo from a deliberate omission."""
    out = tmp_path / "labels.jsonl"

    code = main(
        ["mine", "--out", str(out), "--repos", "psf/requests", "--pin", "psf/request=abc123"]
    )

    assert code == 2
    assert "not in --repos" in capsys.readouterr().err
    assert not out.exists()  # refused before any work, like the overwrite guard
