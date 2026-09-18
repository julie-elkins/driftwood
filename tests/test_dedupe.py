"""One tree state is one example, however many commits corrected it.

`example_id` hashes the state being labelled -- repo, tree sha, paths, label -- and
deliberately omits `fix_sha`. So two sibling commits sharing a parent and making the
same doc correction collide by design, and the miner must emit one example rather
than two.

This is not hypothetical. `pallets/flask` contains two such pairs in 4000 commits,
from fixes that landed twice off the same base. The symptom was a manifest recording
5314 examples while the scorer, which keys by id, read 5312: no error, no warning,
just two numbers that quietly disagreed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from driftwood.mining.labels import LABEL_DRIFT, MineConfig, _example_id, mine_repo

DOC = "docs/api.rst"
BEFORE = "Use the ``unicode`` converter here.\nA second line so the diff is two lines.\n"
AFTER = "Use the ``string`` converter here.\nA second line so the diff is two lines.\n"


def _run(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def _commit(repo: Path, message: str) -> None:
    # By path, never `-A`. The fixture knows exactly what it touched, and a blanket
    # add here would be a pattern worth not copying.
    _run(repo, "add", DOC)
    _run(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "-m",
        message,
    )


@pytest.fixture
def repo_with_duplicated_fix(tmp_path: Path) -> Path:
    """A base commit, then the same doc fix on two branches, then a merge.

    `git log --no-merges` walks past the merge and reports *both* corrections, each
    with the same parent -- which is precisely the shape that collides.
    """
    repo = tmp_path / "dup"
    repo.mkdir()
    _run(repo, "init", "-q", "-b", "main")
    doc = repo / DOC
    doc.parent.mkdir(parents=True)
    doc.write_text(BEFORE)
    _commit(repo, "initial docs")
    base = _run(repo, "rev-parse", "HEAD")

    doc.write_text(AFTER)
    _commit(repo, "docfix: wrong converter name: unicode -> string fixes #364")

    _run(repo, "checkout", "-q", "-b", "sidebranch", base)
    doc.write_text(AFTER)
    _commit(repo, "docfix: wrong converter name: unicode -> string")

    _run(repo, "checkout", "-q", "main")
    _run(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "merge sidebranch",
        "sidebranch",
    )
    return repo


def test_example_id_ignores_which_commit_did_the_fixing():
    """The collision is a property of the id, not an accident.

    Asserted directly so that anyone tempted to add `fix_sha` to the hash sees that
    two commits correcting one state are meant to share an id.
    """
    first = _example_id("o/n", "aaaa", DOC, None, LABEL_DRIFT)
    second = _example_id("o/n", "aaaa", DOC, None, LABEL_DRIFT)
    assert first == second


def test_one_state_corrected_twice_yields_one_positive(repo_with_duplicated_fix: Path):
    examples = list(mine_repo(repo_with_duplicated_fix, "o/n", MineConfig()))
    positives = [e for e in examples if e.label == LABEL_DRIFT]

    assert len(positives) == 1, (
        "the same doc state was corrected by two sibling commits; that is one "
        f"example, got {[(p.example_id, p.subject) for p in positives]}"
    )
    assert positives[0].doc_path == DOC
    assert "unicode" in positives[0].shared_identifiers


def test_ids_are_unique_across_a_whole_mine(repo_with_duplicated_fix: Path):
    """The invariant the manifest's `examples` count depends on.

    Without this, a count written to the manifest disagrees with what any dict-keyed
    consumer reads back, and the difference is invisible.
    """
    ids = [e.example_id for e in mine_repo(repo_with_duplicated_fix, "o/n", MineConfig())]
    assert len(ids) == len(set(ids))


def test_both_post_fix_states_are_kept_as_distinct_negatives(
    repo_with_duplicated_fix: Path,
):
    """Negatives key on `fix_sha`, so the two corrected trees stay separate.

    They are genuinely different trees. Collapsing them would be the opposite error
    to the one this module fixes.
    """
    negatives = [
        e for e in mine_repo(repo_with_duplicated_fix, "o/n", MineConfig())
        if e.label != LABEL_DRIFT
    ]
    assert len({n.fix_sha for n in negatives}) == 2
