"""Assemble what a judge reads for one case: the parent state, and nothing else.

Every number stage 3 produces depends on this module being paranoid, because the
corpus was built *from* the correcting commit and most of the fields on a mined
record describe that commit rather than the state being judged. Two of them give
the answer away outright:

**`subject`** is the commit subject of the *fix*. The miner reads it -- that is how
`drop_cosmetic_subjects` works -- and subjects in this corpus include things like
"Fix incorrect example in the config docs". A judge shown that does not need to read
the code.

**`shared_identifiers`** is `sides["removed_only"]` from the doc diff: the
identifiers the fixing commit *deleted* from the prose. That is a pointer straight at
the drifted sentence. It is the miner's evidence, and handing a judge its evidence is
the retrieval ablation's mistake made worse.

Neither is excluded by omission here. `LEAKING_FIELDS` names them, `render` is the
only way text reaches a model, and a test asserts the rendered string contains
neither. Leakage of this kind does not fail -- it produces an excellent number.

Two arms, fixed before any model ran:

- **oracle** (shape A only, 45 cases): the code file the commit actually touched.
  Isolates judging skill from retrieval quality. Not a product configuration --
  in production nobody hands you the file.
- **retrieved** (all 125): `Lexical` supplies the top-k code files for the document
  from the repo's CODE pool at `at_sha`. The only arm that covers shape B, which is
  80 of the 125 and has no code side in the commit at all, and the only end-to-end
  number.

Both read the tree at `at_sha` -- the parent of the fix -- so the state on screen is
the state the verdict was written about. No diff is assembled anywhere in this
module. The diff-shown ceiling arm lives elsewhere and is a diagnostic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from ..mining.gitio import list_files, local_name_for, read_blobs
from ..mining.paths import Kind, classify
from ..retrieval.rankers import Lexical
from .cases import JudgeCase

__all__ = [
    "ARMS",
    "CodeFile",
    "ContextBuilder",
    "JudgeContext",
    "LEAKING_FIELDS",
    "render",
]

ARMS = ("oracle", "retrieved")

# Fields on a mined record that describe the correcting commit rather than the state
# being judged. Named rather than merely left out, so the exclusion is testable.
LEAKING_FIELDS = ("subject", "shared_identifiers", "fix_sha")

# Character budgets. Chars rather than tokens because the point is a hard, stable,
# tokeniser-independent bound -- a budget that moves with the model would make two
# arms' numbers incomparable.
#
# Docs get the larger share: the claim being judged is in the prose, and a reference
# page can be long. Code is truncated harder because three files are shown.
DOC_BUDGET = 12_000
CODE_BUDGET = 6_000

# How many code files the retrieved arm shows. Set from a measurement rather than
# picked: on the 45 shape-A cases, where the commit's own file is known, `Lexical`
# puts it at
#
#     hit@1 20%   hit@3 38%   hit@5 60%   hit@10 87%   hit@20 98%   median rank 5
#
# so k=3 caps the retrieved arm near 38% on shape A before a judge reads a word, and
# any oracle-vs-retrieved gap would mostly be that cap. k=5 buys 22 points for two
# more files. k=10 buys 27 more but shows seven distractors per query, and the point
# of the arm is an end-to-end number rather than the best number.
#
# This is a swept dimension, not a settled one -- `--k` exists and the model arm
# should be run at 3, 5 and 10 before any of it is described as the retrieved result.
DEFAULT_K = 5


def _truncate(text: str, budget: int) -> tuple[str, bool]:
    """Head-truncate with a visible marker.

    The marker matters more than the direction. A judge that answers "no claim about
    this is made here" on a silently cut document is right about what it was shown
    and wrong about the document, and nothing in the output would distinguish that
    from a real negative. Truncation rates are reported per arm for the same reason.
    """
    if len(text) <= budget:
        return text, False
    kept = text[:budget]
    dropped = len(text) - budget
    return f"{kept}\n\n... [truncated: {dropped} of {len(text)} characters not shown]", True


@dataclass(frozen=True)
class CodeFile:
    path: str
    text: str
    truncated: bool
    rank: int | None  # 1-based retrieval rank; None when supplied as the oracle


@dataclass(frozen=True)
class JudgeContext:
    """One case, rendered down to the parent state a judge can read."""

    example_id: str
    repo: str
    arm: str
    doc_path: str
    doc_text: str
    doc_truncated: bool
    at_sha: str
    code_files: tuple[CodeFile, ...]
    pool_size: int
    # Where the commit's own code file landed in the retrieved list, when both a
    # code_path and a ranking exist. This is the join between stage 2's numbers and
    # stage 3's: if the retrieved arm loses to the oracle arm, this says whether
    # retrieval is why.
    oracle_rank: int | None = None
    # Paths that did not resolve at `at_sha`. read_blobs omits rather than blanks, so
    # without this a vanished file would silently become an absent code side.
    missing: tuple[str, ...] = field(default=())

    @property
    def usable(self) -> bool:
        """False when there is nothing to judge against: no doc, or no code."""
        return bool(self.doc_text.strip()) and bool(self.code_files)


class ContextBuilder:
    """Builds contexts, caching the per-tree work that dominates the runtime.

    Each case sits at its own `at_sha`, so a naive build lists and reads a whole tree
    per case -- 125 times, several hundred files each. Three caches, in increasing
    order of how much they save:

    - the CODE pool per (repo, sha), one `ls-tree` each;
    - the code texts per (repo, sha), one `cat-file --batch` each;
    - identifier tokenisation keyed by *content hash*, shared across every sha and
      every repo. Most files are byte-identical between neighbouring commits, so
      this is the one that turns the build from minutes into seconds. `Lexical`
      already takes exactly this cache; it is threaded through rather than rebuilt.
    """

    def __init__(self, clone_root: Path, *, k: int = DEFAULT_K) -> None:
        self.clone_root = clone_root
        self.k = k
        self._pools: dict[tuple[str, str], list[str]] = {}
        self._texts: dict[tuple[str, str], dict[str, str]] = {}
        self._rankers: dict[tuple[str, str], Lexical] = {}
        self._token_cache: dict[str, frozenset[str]] = {}

    def _clone(self, repo: str) -> Path:
        return self.clone_root / local_name_for(repo)

    def _pool(self, repo: str, sha: str) -> list[str]:
        key = (repo, sha)
        if key not in self._pools:
            present = list_files(self._clone(repo), sha)
            self._pools[key] = sorted(p for p in present if classify(p) is Kind.CODE)
        return self._pools[key]

    def _code_texts(self, repo: str, sha: str) -> dict[str, str]:
        key = (repo, sha)
        if key not in self._texts:
            pool = self._pool(repo, sha)
            self._texts[key] = read_blobs(self._clone(repo), sha, pool)
        return self._texts[key]

    def _ranker(self, repo: str, sha: str) -> Lexical:
        key = (repo, sha)
        if key not in self._rankers:
            self._rankers[key] = Lexical(
                self._code_texts(repo, sha), token_cache=self._token_cache
            )
        return self._rankers[key]

    def build(self, case: JudgeCase, arm: str) -> JudgeContext:
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}")
        if arm == "oracle" and not case.code_path:
            raise ValueError(
                f"case {case.example_id} is shape {case.shape} and has no code_path; "
                "the oracle arm covers shape A only"
            )

        clone = self._clone(case.repo)
        doc_blobs = read_blobs(clone, case.at_sha, [case.doc_path])
        missing: list[str] = []
        raw_doc = doc_blobs.get(case.doc_path)
        if raw_doc is None:
            missing.append(case.doc_path)
            raw_doc = ""
        doc_text, doc_truncated = _truncate(raw_doc, DOC_BUDGET)

        pool = self._pool(case.repo, case.at_sha)
        texts = self._code_texts(case.repo, case.at_sha)

        oracle_rank: int | None = None
        if case.code_path:
            # Computed in both arms, so the oracle arm also reports where retrieval
            # would have put the file it was handed. Free, and it is the diagnostic
            # that attributes an oracle-vs-retrieved gap.
            ranked = self._ranker(case.repo, case.at_sha).rank(
                case.doc_path, raw_doc, pool
            )
            if case.code_path in ranked:
                oracle_rank = ranked.index(case.code_path) + 1

        chosen: list[CodeFile] = []
        if arm == "oracle":
            assert case.code_path is not None
            body = texts.get(case.code_path)
            if body is None:
                # The commit touched it, so it exists at the fix; absent at the parent
                # means the fix created it. Recorded rather than substituted -- a
                # quietly swapped-in retrieved file would put a different arm's
                # context under the oracle arm's label.
                missing.append(case.code_path)
            else:
                text, cut = _truncate(body, CODE_BUDGET)
                chosen.append(CodeFile(case.code_path, text, cut, rank=None))
        else:
            ranked = self._ranker(case.repo, case.at_sha).rank(
                case.doc_path, raw_doc, pool
            )
            for position, path in enumerate(ranked[: self.k], start=1):
                body = texts.get(path)
                if body is None:
                    missing.append(path)
                    continue
                text, cut = _truncate(body, CODE_BUDGET)
                chosen.append(CodeFile(path, text, cut, rank=position))

        return JudgeContext(
            example_id=case.example_id,
            repo=case.repo,
            arm=arm,
            doc_path=case.doc_path,
            doc_text=doc_text,
            doc_truncated=doc_truncated,
            at_sha=case.at_sha,
            code_files=tuple(chosen),
            pool_size=len(pool),
            oracle_rank=oracle_rank,
            missing=tuple(missing),
        )


def render(context: JudgeContext) -> str:
    """The user-turn text for one case.

    Deliberately not a template file. The prompt is part of the measurement, so it
    lives next to the code that decides what goes in it, and a diff to it shows up in
    review as a change to the experiment rather than to a config asset.

    No commit subject, no shared identifiers, no sha of the fix, no diff. Only the
    two things a reader would have at that commit: the document, and some code.
    """
    parts = [
        f"Repository: {context.repo}",
        f"Documentation file: {context.doc_path}",
        "",
        "--- DOCUMENTATION ---",
        context.doc_text,
        "--- END DOCUMENTATION ---",
        "",
    ]
    for code in context.code_files:
        where = "the file the documentation is about" if code.rank is None else (
            f"candidate {code.rank} of {len(context.code_files)} by identifier overlap"
        )
        parts.extend(
            [
                f"--- CODE: {code.path} ({where}) ---",
                code.text,
                f"--- END CODE: {code.path} ---",
                "",
            ]
        )
    if not context.code_files:
        parts.append("(No code files were available for this document.)")
    return "\n".join(parts)


def context_hash(context: JudgeContext, prompt: str, model: str) -> str:
    """Cache key for a judgement: everything that could change the answer.

    Keyed on the rendered content rather than on `example_id`, so editing the prompt
    or the budgets invalidates the cache instead of serving answers from a harness
    that no longer exists. Getting this wrong is expensive in a way that looks free:
    stale hits would make a prompt change appear to have no effect.
    """
    digest = hashlib.blake2b(digest_size=16)
    for piece in (model, prompt, context.arm, render(context)):
        digest.update(piece.encode("utf-8", "replace"))
        digest.update(b"\x00")
    return digest.hexdigest()
