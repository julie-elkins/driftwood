"""Negatives from doc/code pairs that never changed together.

These are the only negatives that permit a false-positive rate. A *matched*
negative is the same doc/code pair one commit after a human fixed it -- so the doc
really is about that code, and a detector that fires on every pair still scores
well. An unrelated pair is the control that catches exactly that failure.

Two flavours, separated by `label_basis`: a uniformly random pair, which is trivial,
and a pair whose paths look related but never co-changed, which is not. Blending
them into one specificity number would hide the only interesting half.

The label is presumed, not confirmed: nobody read these pairs. A doc can be false
about code it was never edited alongside. So they support a false-positive rate and
must never be quoted as accuracy.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from driftwood.mining.labels import (
    BASIS_NEVER_COCHANGED,
    BASIS_NEVER_COCHANGED_RELATED_PATH,
    LABEL_CLEAN,
    SHAPE_NEGATIVE_EASY,
    MineConfig,
    _looks_related,
    _path_tokens,
    mine_repo,
)

COOKIES_DOC = "docs/cookies.rst"
COOKIES_CODE = "requests/cookies.py"
SESSIONS_DOC = "docs/sessions.rst"
SESSIONS_CODE = "requests/sessions.py"
FIXTURE_README = "tests/certs/README.md"

# Every pair except the one that co-changed.
UNRELATED = {
    (COOKIES_DOC, SESSIONS_CODE),
    (SESSIONS_DOC, COOKIES_CODE),
    (SESSIONS_DOC, SESSIONS_CODE),
}


def _run(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def _commit(repo: Path, message: str, *paths: str) -> None:
    for path in paths:
        _run(repo, "add", path)  # by path, never -A
    _run(
        repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """One co-changed pair, and a second pair that looks related and never was.

    Note the shape of this fixture: an initial commit relates *everything it
    creates*, so the later files have to arrive in commits of their own for any
    unrelated pair to exist at all. That is true of real repositories too.
    """
    repo = tmp_path / "r"
    repo.mkdir()
    _run(repo, "init", "-q", "-b", "main")

    _write(repo, COOKIES_DOC, "The ``unicode`` jar is available.\nSecond line.\n")
    _write(repo, COOKIES_CODE, "jar = 'unicode'\n")
    _commit(repo, "initial", COOKIES_DOC, COOKIES_CODE)

    _write(repo, SESSIONS_DOC, "Sessions persist cookies.\nSecond line.\n")
    _commit(repo, "add sessions docs", SESSIONS_DOC)

    _write(repo, SESSIONS_CODE, "keep_alive = True\n")
    _commit(repo, "add sessions module", SESSIONS_CODE)

    _write(repo, COOKIES_DOC, "The ``string`` jar is available.\nSecond line.\n")
    _write(repo, COOKIES_CODE, "jar = 'string'\n")
    _commit(repo, "rename jar", COOKIES_DOC, COOKIES_CODE)

    _write(repo, FIXTURE_README, "Regenerate these certs with make.\n")
    _commit(repo, "document the cert fixtures", FIXTURE_README)
    return repo


def _easy(repo: Path, n: int, seed: int = 17) -> list:
    cfg = MineConfig(easy_negatives_per_repo=n, easy_negative_seed=seed)
    return [e for e in mine_repo(repo, "o/n", cfg) if e.shape == SHAPE_NEGATIVE_EASY]


def test_none_emitted_by_default(repo: Path):
    """Off unless asked for: switching them on changes what every count means."""
    assert not [
        e for e in mine_repo(repo, "o/n", MineConfig()) if e.shape == SHAPE_NEGATIVE_EASY
    ]


def test_labelled_clean_with_a_basis_that_names_the_presumption(repo: Path):
    examples = _easy(repo, 3)
    assert len(examples) == 3  # not vacuous: the assertions below must run
    for example in examples:
        assert example.label == LABEL_CLEAN
        assert example.label_basis in {
            BASIS_NEVER_COCHANGED,
            BASIS_NEVER_COCHANGED_RELATED_PATH,
        }


def test_never_emits_a_pair_that_did_co_change(repo: Path):
    """`docs/cookies.rst` and `requests/cookies.py` changed together twice."""
    pairs = {(e.doc_path, e.code_path) for e in _easy(repo, 3)}
    assert pairs == UNRELATED  # equality, not subset: a vacuous pass is the bug here


def test_the_hard_arm_finds_the_pair_that_looks_related(repo: Path):
    """`docs/sessions.rst` and `requests/sessions.py` share a distinctive word and
    have no shared history. That is the negative worth having: a random pair is not a
    judgement call, and a specificity number built only from random pairs prices the
    problem far below what stage-2 retrieval will actually hand the detector.
    """
    related = {
        (e.doc_path, e.code_path)
        for e in _easy(repo, 3)
        if e.label_basis == BASIS_NEVER_COCHANGED_RELATED_PATH
    }
    assert related == {(SESSIONS_DOC, SESSIONS_CODE)}


def test_a_shortfall_is_not_topped_up_from_the_easy_arm(repo: Path):
    """Only one path-related pair exists, so asking for more must under-deliver.

    Substituting random pairs to hit the requested count would be the worst
    available failure: the number would look complete while measuring something
    easier than it claims.
    """
    bases = [e.label_basis for e in _easy(repo, 50)]
    assert bases.count(BASIS_NEVER_COCHANGED_RELATED_PATH) == 1


def test_co_change_is_recorded_even_from_commits_the_filters_reject(repo: Path):
    """The initial commit is rejected as a source of positives -- an added doc
    cannot have been wrong before it existed -- yet it still relates its files.

    Recording only from *accepted* commits would push a genuinely related pair into
    the negative set: not a missing label but a wrong one, biased in the direction
    that flatters the detector.
    """
    pairs = {(e.doc_path, e.code_path) for e in _easy(repo, 50)}
    assert pairs
    assert (COOKIES_DOC, COOKIES_CODE) not in pairs


def test_exhausts_the_pool_rather_than_spinning(repo: Path):
    """Only three unrelated pairs exist; asking for 50 must return 3, not hang."""
    assert len(_easy(repo, 50)) == 3


def test_sampling_is_reproducible(repo: Path):
    """The manifest promises byte-identical replay, so the draw must be seeded."""
    first = [e.example_id for e in _easy(repo, 3)]
    second = [e.example_id for e in _easy(repo, 3)]
    assert first == second == sorted(set(first), key=first.index)


def test_carries_a_real_date_and_no_fixing_commit(repo: Path):
    """A zero timestamp would sort to 1970 and corrupt a later time-based split."""
    for example in _easy(repo, 3):
        assert example.fix_sha == ""
        assert example.parent_sha == ""
        assert example.committed_at > 0


def test_ids_do_not_collide_with_matched_negatives(repo: Path):
    """Both are `clean`, so a collision would silently overwrite one.

    Safe by construction rather than by luck: a matched negative's pair co-changed
    by definition, and these pairs did not. Asserted anyway, because the guarantee
    lives in two separate places and could drift apart.
    """
    examples = list(mine_repo(repo, "o/n", MineConfig(easy_negatives_per_repo=3)))
    ids = [e.example_id for e in examples]
    assert len(ids) == len(set(ids))


def test_generic_path_words_do_not_make_two_files_look_related():
    """Without a stoplist, every doc shares `docs` with every other doc and the hard
    arm silently degenerates into the easy one while still reporting itself as hard.
    """
    assert _path_tokens("docs/api/index.rst") == frozenset()
    assert _path_tokens("docs/api/cookies.rst") == {"cookies"}
    assert not _path_tokens("docs/advanced.rst") & _path_tokens("src/utils/main.py")


def test_a_generic_stem_shared_by_both_paths_still_counts_as_related():
    """Regression. `docs/api.rst` and `src/requests/api.py` are an obviously related
    pair, and the stoplist reduces both to no tokens at all -- so a token-only test
    called them unrelated and filed one of the hardest negatives available under the
    basis reserved for random ones. Found by reading the sampler's output, not here.
    """
    assert _looks_related("docs/api.rst", "src/requests/api.py")
    assert _looks_related("docs/cookies.rst", "requests/cookies.py")
    assert not _looks_related("docs/index.rst", "src/flask/cli.py")


def test_the_easy_arm_never_contains_a_pair_that_looks_related(repo: Path):
    """Otherwise the tier meant to measure a floor quietly contains the hard cases."""
    easy = [
        e for e in _easy(repo, 50) if e.label_basis == BASIS_NEVER_COCHANGED
    ]
    assert easy
    assert not [e for e in easy if _looks_related(e.doc_path, e.code_path)]


def test_a_readme_inside_a_test_directory_is_not_sampled_as_documentation(repo: Path):
    """`tests/certs/README.md` is instructions for regenerating fixtures, not
    documentation about the code. `classify` keeps it -- it cannot cheaply tell it
    from a root README, and errs towards keeping -- so the sampler excludes it here.

    Measured at 74 of 739 easy negatives before the fix, and all three of
    `psf/requests`' hard negatives were this one file.
    """
    docs = {e.doc_path for e in _easy(repo, 50)}
    assert docs
    assert FIXTURE_README not in docs
