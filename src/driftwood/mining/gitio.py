"""Read history out of a local git clone.

Everything here shells out to git rather than using a binding. Git's plumbing
commands are a stable public interface, this pass is I/O-bound on git itself so a
binding would save nothing measurable, and a subprocess boundary means every
result can be reproduced by hand in a terminal when a label looks wrong -- which
it will.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ChangedFile",
    "Commit",
    "GitError",
    "changed_lines",
    "commit_time",
    "diff_line_counts",
    "ensure_clone",
    "file_diff",
    "head_sha",
    "iter_commits",
    "list_files",
    "local_name_for",
    "read_blobs",
]

# ASCII record and unit separators. Commit subjects contain newlines, tabs, pipes
# and every other character someone might reach for as a delimiter; these two are
# the only bytes git will not emit from author-written content.
RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"

_LOG_FORMAT = f"{RECORD_SEP}%H{FIELD_SEP}%P{FIELD_SEP}%ct{FIELD_SEP}%s"

# core.quotePath=false: without it git escapes non-ASCII paths into octal, so a
# path with an accent in it comes back mangled and then silently fails to match
# the path we later ask for. Set on every invocation rather than relying on the
# user's global config.
_BASE_ARGS = ("git", "-c", "core.quotePath=false")


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChangedFile:
    status: str  # A(dded) M(odified) D(eleted) R(enamed) C(opied) T(ypechange)
    path: str  # path as of this commit
    old_path: str | None  # set for renames and copies
    blob_before: str
    blob_after: str


@dataclass(frozen=True)
class Commit:
    sha: str
    parents: tuple[str, ...]
    committed_at: int
    subject: str
    files: tuple[ChangedFile, ...]

    @property
    def parent(self) -> str | None:
        return self.parents[0] if len(self.parents) == 1 else None


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        [*_BASE_ARGS, "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed in {repo}: {proc.stderr.strip()}")
    return proc.stdout


def local_name_for(url: str) -> str:
    """A filesystem-safe directory name for a repo URL or `owner/name` slug."""
    slug = url.removeprefix("https://github.com/").removeprefix("git@github.com:")
    slug = slug.removesuffix(".git").strip("/")
    return re.sub(r"[^A-Za-z0-9._-]+", "__", slug)


def ensure_clone(slug_or_url: str, root: Path) -> Path:
    """Clone `owner/name` into `root`, or return the existing clone.

    Bare, because we never need a working tree -- every read goes through git
    plumbing against a commit-ish. A full clone rather than a partial one
    (`--filter=blob:none`) is deliberate for now: it makes the mining pass fully
    offline and therefore reproducible, which matters more at three repos than
    the disk saving does. Revisit when repo count makes clone time the bottleneck.
    """
    url = slug_or_url
    if "://" not in url and not url.startswith("git@"):
        url = f"https://github.com/{slug_or_url}"

    dest = root / local_name_for(slug_or_url)
    if (dest / "HEAD").exists():
        return dest

    root.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--bare", "--quiet", url, str(dest)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitError(f"clone of {url} failed: {proc.stderr.strip()}")
    return dest


def _parse_raw_line(line: str) -> ChangedFile | None:
    """Parse one `--raw` entry: `:<mode> <mode> <sha> <sha> <status>\\t<path>`."""
    if not line.startswith(":"):
        return None
    meta, *paths = line.rstrip("\n").split("\t")
    fields = meta[1:].split()
    if len(fields) < 5 or not paths:
        return None
    _src_mode, _dst_mode, blob_before, blob_after, status = fields[:5]
    # Renames and copies carry a similarity score (R100, C85) and two paths.
    if len(paths) >= 2:
        return ChangedFile(status[0], paths[1], paths[0], blob_before, blob_after)
    return ChangedFile(status[0], paths[0], None, blob_before, blob_after)


def _parse_record(lines: list[str]) -> Commit:
    header = lines[0].lstrip(RECORD_SEP).rstrip("\n")
    sha, parents_raw, timestamp, subject = header.split(FIELD_SEP, 3)
    files = tuple(
        changed
        for changed in (_parse_raw_line(line) for line in lines[1:])
        if changed is not None
    )
    return Commit(
        sha=sha,
        parents=tuple(parents_raw.split()),
        committed_at=int(timestamp),
        subject=subject,
        files=files,
    )


def head_sha(repo: Path, rev: str = "HEAD") -> str:
    """Resolve a rev to a full sha.

    Recorded in every mine manifest. Without it a label set is not reproducible:
    `--limit 4000` counts backwards from wherever HEAD happens to be, so the same
    command run a month later mines a different commit window and silently yields
    a different corpus.
    """
    return _git(repo, "rev-parse", rev).strip()


def list_files(repo: Path, rev: str = "HEAD") -> list[str]:
    """Every path present in the tree at `rev`.

    Needed to build negatives from pairs that never co-changed: such a pair has no
    commit to read paths from, so the only place to learn that both files exist at
    the same time is the tree itself.
    """
    out = _git(repo, "ls-tree", "-r", "--name-only", rev)
    return [line for line in out.splitlines() if line]


def read_blobs(repo: Path, rev: str, paths: Iterable[str]) -> dict[str, str]:
    """Contents of many paths at one rev, in a single git invocation.

    `git show rev:path` per file would be correct and is what the rest of this
    module does, but the retrieval eval reads every code file in a repo -- 527 of
    them in fastapi -- and a process spawn per file dominates the runtime of the
    whole eval. `cat-file --batch` streams them over one pipe instead.

    A path that does not exist at `rev` is *omitted from the result*, not returned
    empty. An empty string would rank as a document with no terms and silently
    score zero, which is indistinguishable from a real file the ranker got wrong;
    a missing key makes the caller decide, and the callers here count them.

    Binary and undecodable files come back with replacement characters rather than
    raising. They are noise in a lexical ranker either way, and a UnicodeDecodeError
    part-way through a 500-file read would lose the whole batch.
    """
    wanted = list(paths)
    if not wanted:
        return {}

    proc = subprocess.Popen(
        [*_BASE_ARGS, "-C", str(repo), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None and proc.stdout is not None
    query = "".join(f"{rev}:{path}\n" for path in wanted)
    proc.stdin.write(query.encode())
    proc.stdin.close()

    out: dict[str, str] = {}
    try:
        for path in wanted:
            header = proc.stdout.readline()
            if not header:
                raise GitError(f"git cat-file ended early in {repo} at {path}")
            fields = header.split()
            # `<oid> missing`, or `<name> <reason>` for malformed input. Either way
            # there is no body to consume, so do not try to read one.
            if len(fields) < 3:
                continue
            size = int(fields[2])
            body = proc.stdout.read(size)
            proc.stdout.read(1)  # the newline git writes after every body
            out[path] = body.decode("utf-8", errors="replace")
    finally:
        proc.stdout.close()
        proc.wait()
    return out


def commit_time(repo: Path, rev: str = "HEAD") -> int:
    """Commit timestamp of `rev`, as a unix epoch.

    Exists so that an example describing a tree state rather than a fix still
    carries a real date. A zero timestamp would sort to 1970 and quietly corrupt
    any later time-based train/test split.
    """
    return int(_git(repo, "show", "-s", "--format=%ct", rev).strip())


def iter_commits(
    repo: Path,
    *,
    limit: int | None = None,
    since: str | None = None,
    rev: str = "HEAD",
) -> Iterator[Commit]:
    """Stream commits newest-first, one parsed record at a time.

    Deliberately not `--reverse`: git has to buffer the entire log to reverse it,
    which defeats the streaming this function exists to provide. Mining order
    does not matter, so we take the cheap direction.

    `rev` is what makes a run replayable -- pass the sha a manifest recorded and
    the same commit window is mined regardless of what has landed since.
    """
    args = [
        *_BASE_ARGS,
        "-C",
        str(repo),
        "log",
        "--no-merges",
        "--raw",
        "--no-abbrev",
        "-M",  # detect renames rather than reporting delete+add
        f"--format={_LOG_FORMAT}",
    ]
    if limit is not None:
        args += ["-n", str(limit)]
    if since is not None:
        args += [f"--since={since}"]
    args.append(rev)

    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    buffer: list[str] = []
    try:
        for line in proc.stdout:
            if line.startswith(RECORD_SEP):
                if buffer:
                    yield _parse_record(buffer)
                buffer = [line]
            elif buffer:
                buffer.append(line)
        if buffer:
            yield _parse_record(buffer)
    finally:
        if proc.stdout:
            proc.stdout.close()
        stderr = proc.stderr.read() if proc.stderr else ""
        if proc.stderr:
            proc.stderr.close()
        code = proc.wait()
        # 141 is SIGPIPE, which is what we get when a caller breaks out early.
        if code not in (0, 141) and stderr.strip():
            raise GitError(f"git log failed in {repo}: {stderr.strip()}")


def file_diff(
    repo: Path,
    base: str,
    head: str,
    path: str,
    *,
    old_path: str | None = None,
    context: int = 0,
) -> str:
    """Unified diff for one path between two commits.

    `context=0` by default: we want the lines that changed, not the lines near
    them. Context lines would leak unchanged identifiers into the overlap test
    and make almost every pair look related.
    """
    paths = [path] if old_path is None else [old_path, path]
    return _git(repo, "diff", f"-U{context}", "--no-color", base, head, "--", *paths)


_HUNK_HEADER = re.compile(r"^(\+\+\+|---|@@|diff |index |similarity |rename |new file|deleted file)")


def changed_lines(diff_text: str) -> str:
    """Just the added and removed content of a diff, stripped of markers.

    Identifiers are extracted from this rather than from whole files. Whole-file
    extraction would find shared tokens in essentially every doc/code pair, which
    would make the overlap test look like it works while measuring nothing.
    """
    out: list[str] = []
    for line in diff_text.splitlines():
        if _HUNK_HEADER.match(line):
            continue
        if line.startswith(("+", "-")):
            out.append(line[1:])
    return "\n".join(out)


def changed_sides(diff_text: str) -> tuple[str, str]:
    """(added_text, removed_text) from a diff, as two separate blobs.

    Needed for doc-only commits, where there is no code side to compare a doc
    against and the only available contrast is old prose vs new prose.

    One known blind spot, inherited from `_HUNK_HEADER`: a removed line that is
    itself three or more dashes -- an RST section underline, a markdown rule --
    looks exactly like a diff file header and gets skipped. It carries no
    identifiers, so it cannot change an overlap verdict, but it does mean the
    removed side is not a byte-faithful reconstruction.
    """
    added: list[str] = []
    removed: list[str] = []
    for line in diff_text.splitlines():
        if _HUNK_HEADER.match(line):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
    return "\n".join(added), "\n".join(removed)


def diff_line_counts(diff_text: str) -> tuple[int, int]:
    """(added, removed) content lines in a diff."""
    added = removed = 0
    for line in diff_text.splitlines():
        if _HUNK_HEADER.match(line):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed
