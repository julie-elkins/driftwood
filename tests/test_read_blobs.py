"""`read_blobs` reads many files at one rev over a single pipe. Tested against a
real repo built in a tmpdir, because the thing that can go wrong is the streaming
protocol and a mock of git would only assert my own assumptions back at me.

The failure that matters is desynchronisation. `cat-file --batch` interleaves
headers and bodies on one stream, so consuming one byte too few after a body shifts
every subsequent file's *content onto the wrong path* -- and the eval would then
score a ranker against text belonging to a different module, at full confidence,
with no error anywhere.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from driftwood.mining.gitio import read_blobs


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    return root


def _commit(repo: Path, files: dict[str, str]) -> str:
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        _git(repo, "add", "--", name)
    _git(repo, "commit", "-q", "-m", "c")
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_every_path_maps_to_its_own_content(repo: Path):
    """The desync test. Sizes deliberately differ, including an empty file and one
    whose body ends without a newline -- the two shapes most likely to be off by a
    byte."""
    files = {
        "a.py": "aaa\n",
        "b.py": "b" * 5000 + "\n",
        "c.py": "",
        "d.py": "no trailing newline",
        "nested/e.py": "eee\n",
    }
    sha = _commit(repo, files)

    got = read_blobs(repo, sha, list(files))

    assert got == files


def test_a_missing_path_is_absent_rather_than_empty(repo: Path):
    """An empty string would rank as a document with no terms and score zero,
    indistinguishable from a real file the ranker simply got wrong."""
    sha = _commit(repo, {"a.py": "aaa\n"})

    got = read_blobs(repo, sha, ["a.py", "does/not/exist.py"])

    assert got == {"a.py": "aaa\n"}
    assert "does/not/exist.py" not in got


def test_a_missing_path_does_not_desynchronise_the_paths_after_it(repo: Path):
    """A `missing` line has no body. Reading one anyway would consume the *next*
    file's header and shift the rest of the batch by one."""
    sha = _commit(repo, {"a.py": "aaa\n", "b.py": "bbb\n"})

    got = read_blobs(repo, sha, ["a.py", "gone.py", "b.py"])

    assert got == {"a.py": "aaa\n", "b.py": "bbb\n"}


def test_undecodable_bytes_do_not_lose_the_whole_batch(repo: Path):
    """A UnicodeDecodeError part-way through a 500-file read would throw away every
    file already read, for a file that is noise to a lexical ranker anyway."""
    (repo / "bin.dat").write_bytes(b"\xff\xfe\x00\x01")
    _git(repo, "add", "--", "bin.dat")
    (repo / "ok.py").write_text("ok\n", encoding="utf-8")
    _git(repo, "add", "--", "ok.py")
    _git(repo, "commit", "-q", "-m", "c")
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    got = read_blobs(repo, sha, ["bin.dat", "ok.py"])

    assert got["ok.py"] == "ok\n"
    assert "bin.dat" in got


def test_an_empty_path_list_does_not_spawn_git(repo: Path):
    assert read_blobs(repo, "HEAD", []) == {}
