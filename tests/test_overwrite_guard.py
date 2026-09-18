"""`mine` must not silently overwrite its output.

Written because it happened. `--out` defaults to `data/labels.jsonl`, the one label
set in this repo that predates manifests and so cannot be regenerated, and the
README's own usage example omitted `--out` -- which meant following the
documentation destroyed the file the documentation calls irreplaceable. Recovered
from git. This is the fix.

Fitting, for a project about documentation that has quietly stopped being true.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from driftwood.mining.cli import main

SLUG = "o/n"
CLONE_DIR_NAME = "o__n"  # what local_name_for(SLUG) produces


def _run(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def clones(tmp_path: Path) -> Path:
    """A pre-seeded clone directory, so `mine` runs offline.

    `ensure_clone` returns an existing clone rather than fetching, so placing a bare
    repo where it expects one keeps these tests off the network entirely.
    """
    work = tmp_path / "work"
    work.mkdir()
    _run(work, "init", "-q", "-b", "main")
    (work / "README.md").write_text("The ``flag`` is supported.\n")
    _run(work, "add", "README.md")  # by path, never -A
    _run(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")

    root = tmp_path / "clones"
    root.mkdir()
    _run(tmp_path, "clone", "--bare", "--quiet", str(work), str(root / CLONE_DIR_NAME))
    return root


def _mine(out: Path, clones: Path, *extra: str) -> int:
    return main(
        ["mine", "--out", str(out), "--clones", str(clones), "--repos", SLUG, *extra]
    )


def test_refuses_to_overwrite_an_existing_output(tmp_path: Path, clones: Path, capsys):
    out = tmp_path / "labels.jsonl"
    out.write_text('{"example_id": "precious"}\n')

    assert _mine(out, clones) == 2
    assert out.read_text() == '{"example_id": "precious"}\n'
    assert "refusing to overwrite" in capsys.readouterr().err


def test_refuses_before_doing_any_work(tmp_path: Path, capsys):
    """The refusal must land before the clones, or it arrives seven minutes late.

    Asserted by naming a repo that cannot be cloned and passing no seeded clone
    directory: if the guard ran after cloning, this would fail on the clone instead
    of returning the guard's exit code.
    """
    out = tmp_path / "labels.jsonl"
    out.write_text("x\n")

    assert main(["mine", "--out", str(out), "--repos", "no-such-owner/no-such-repo"]) == 2


def test_force_allows_it(tmp_path: Path, clones: Path, capsys):
    """An explicit --force is the intended escape hatch and must not be refused."""
    out = tmp_path / "labels.jsonl"
    out.write_text("stale\n")

    assert _mine(out, clones, "--force") == 0
    assert out.read_text() != "stale\n"
    assert "refusing to overwrite" not in capsys.readouterr().err


def test_a_fresh_path_needs_no_force(tmp_path: Path, clones: Path):
    out = tmp_path / "nested" / "labels.jsonl"

    assert _mine(out, clones) == 0
    assert out.exists()
    # The manifest is written alongside, and is the thing that makes the label file
    # disposable in the first place.
    assert out.with_suffix(".manifest.json").exists()
