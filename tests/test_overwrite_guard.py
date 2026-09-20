"""`mine` and `sample` must not silently overwrite their output.

Written because it happened. `--out` defaults to `data/labels.jsonl`, the one label
set in this repo that predates manifests and so cannot be regenerated, and the
README's own usage example omitted `--out` -- which meant following the
documentation destroyed the file the documentation calls irreplaceable. Recovered
from git. This is the fix.

Fitting, for a project about documentation that has quietly stopped being true.

And then the SAME hole was found in `sample`, which is worse: a review sheet holds
hand labels, so a filled one is the only copy of a judgement nothing regenerates.
The README's usage example writes to `review/batch.md` -- a real, filled sheet --
so following the README as printed destroyed 25 verdicts, and at the time that
file was untracked, so unlike the `mine` case there would have been no git copy.
Fixing one instance of a class and not looking for the others is how a fix becomes
a near miss.
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


def _labels(path: Path) -> Path:
    """One mined positive, enough for `sample` to have something to draw."""
    import json

    path.write_text(
        json.dumps(
            {
                "example_id": "aaa1",
                "label": "drift",
                "shape": "A",
                "repo": SLUG,
                "doc_path": "README.md",
                "code_path": "m.py",
                "at_sha": "a" * 40,
                "fix_sha": "b" * 40,
                "parent_sha": "c" * 40,
                "subject": "s",
                "label_basis": "b",
                "committed_at": "2026-01-01T00:00:00Z",
                "doc_lines_added": 1,
                "doc_lines_removed": 1,
                "files_in_commit": 2,
                "shared_identifiers": ["flag"],
            }
        )
        + "\n"
    )
    return path


def _sample(out: Path, labels: Path, clones: Path, *extra: str) -> int:
    return main(
        [
            "sample", "--out", str(out), "--labels", str(labels),
            "--clones", str(clones), "-n", "1", *extra,
        ]
    )


class TestSampleWillNotEatAFilledSheet:
    """The hand labels are the ground truth; nothing regenerates a filled sheet."""

    def test_refuses_to_overwrite_an_existing_sheet(self, tmp_path: Path, clones, capsys):
        out = tmp_path / "batch.md"
        filled = "## case aaa1\n\nVERDICT: drift\n"
        out.write_text(filled)

        assert _sample(out, _labels(tmp_path / "l.jsonl"), clones) == 2
        assert out.read_text() == filled, "a verdict is not recoverable"
        assert "refusing to overwrite" in capsys.readouterr().err

    def test_the_refusal_names_the_reason_not_just_the_file(self, tmp_path, clones, capsys):
        # `mine`'s message says the output is derived data that may not be regenerable.
        # A sheet is not derived from anything, and a reader deciding whether to reach
        # for --force needs that difference said out loud.
        out = tmp_path / "batch.md"
        out.write_text("VERDICT: cosmetic\n")

        _sample(out, _labels(tmp_path / "l.jsonl"), clones)

        assert "hand labels" in capsys.readouterr().err

    def test_force_allows_it(self, tmp_path: Path, clones):
        out = tmp_path / "batch.md"
        out.write_text("VERDICT: drift\n")

        assert _sample(out, _labels(tmp_path / "l.jsonl"), clones, "--force") == 0
        assert "VERDICT: ?" in out.read_text()

    def test_a_fresh_path_needs_no_force(self, tmp_path: Path, clones):
        out = tmp_path / "nested" / "batch.md"

        assert _sample(out, _labels(tmp_path / "l.jsonl"), clones) == 0
        assert "VERDICT: ?" in out.read_text()

    def test_the_readme_usage_example_does_not_point_at_a_real_sheet(self):
        # The actual defect was a documentation one: the guard makes the command safe,
        # and an example naming a live sheet still invites a --force. Every review sheet
        # in this repo is `shape-{A,B}-batch-NN`, so an example must not collide.
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()
        live = {p.name for p in (Path(__file__).resolve().parents[1] / "review").glob("*.md")}
        for name in live:
            assert f"--out review/{name}" not in readme, (
                f"the README tells a reader to write over {name}"
            )
