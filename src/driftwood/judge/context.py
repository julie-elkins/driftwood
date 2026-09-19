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

Three arms. The first two were fixed before any model ran; the third was added after
the first paid run, because reading the model's own reasons showed the oracle arm could
not answer the question it was built to ask.

- **oracle** (shape A only, 45 cases): the code file the commit actually touched, and
  nothing else. Built to isolate judging skill from retrieval quality. **It does not
  do that, and the number it produced is kept rather than corrected.** The judge
  abstained on 31 of 45, and on the 10 `drift` cases it abstained on, its stated reason
  was one file being insufficient seven times: `requests/__init__.py` "merely imports
  these names", `setup.py` cannot speak to SOCKS support, `flask/testing.py` is not
  where `before_request` lives. A documentation page makes claims about a package, and
  one module is not a package -- so this arm's ceiling is file count, not judging skill.
- **seeded** (shape A only, 45 cases): the commit's own file *plus* retrieval's top hits
  up to `k`. This is what "isolate judging from retrieval" actually requires -- the
  known-relevant file is guaranteed present, so a failure here cannot be retrieval
  missing it, while the judge still gets enough of the package to decide. A separate arm
  rather than a redefinition of `oracle`, because `oracle`'s number is already published
  in `data/scores/` and silently changing what a published arm means is worse than
  carrying a superseded one.
- **retrieved** (all 125): `Lexical` supplies the top-k code files for the document
  from the repo's CODE pool at `at_sha`. The only arm that covers shape B, which is
  80 of the 125 and has no code side in the commit at all, and the only end-to-end
  number.

Code files are **windowed, not head-truncated** -- see `select_relevant`. That changed
for the same reason the third arm exists: the run reported "18 documents were cut" and
said nothing about 29 of 45 code files being cut, and three of the ten `drift`
abstentions named the cut as their reason.

Both read the tree at `at_sha` -- the parent of the fix -- so the state on screen is
the state the verdict was written about. No diff is assembled anywhere in this
module. The diff-shown ceiling arm lives elsewhere and is a diagnostic.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ..mining.gitio import list_files, local_name_for, read_blobs
from ..mining.identifiers import extract, literal_spans
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
    "select_relevant",
]

ARMS = ("oracle", "seeded", "retrieved")

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


# How many lines of a code file's head are kept unconditionally when it has to be cut.
# The module docstring and the import block orient a reader for almost nothing, and they
# are the one region whose relevance cannot be judged by identifier overlap.
_HEAD_LINES = 12

# Lines kept either side of a line that mentions one of the document's identifiers.
# Small on purpose: the budget is fixed, so every line of padding is a line of some
# other function that does not get shown.
_CONTEXT_LINES = 5

_DEF_RE = re.compile(r"^\s*(?:async\s+def|def|class)\s")

# Import and re-export lines, scored at zero so they never buy a window of their own.
_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s")

# A line that DEFINES one of the document's identifiers is worth ten that mention one,
# and the first version of this function weighted them equally. That is the project's own
# lesson turned on itself: `requests/__init__.py` scores ~100% claim coverage while
# containing no implementation, because a token-presence metric cannot tell "defines"
# from "mentions". Ranking windows by raw identifier density does the same thing one level
# down -- the densest lines in a large library module are its docstring, its `__all__` and
# its import block, so an unweighted budget goes to the parts of the file that name
# everything and implement nothing. Measured: unweighted windowing made 5 of 29 cut files
# WORSE than head-truncation, `src/flask/app.py` from 100% to 0%.
_DEFINITION_WEIGHT = 10
_MENTION_WEIGHT = 1


def select_relevant(
    text: str, budget: int, wanted: frozenset[str] | set[str]
) -> tuple[str, bool]:
    """Keep the parts of a code file that mention what the document talks about.

    Replaces head-truncation for code, and the reason is measured rather than
    aesthetic. 29 of the 45 oracle files in the first paid run were over the
    6,000-character budget -- `flask/app.py` is 70,003, `flask.py` 47,528 -- so what the
    judge was shown was the first eighth of a module and the hope that the relevant
    function was near the top. It was not, and the model said so in its own words on
    three of the ten `drift` cases it abstained on: "the Response class methods ... are
    truncated and not visible", "the relevant classes ... are truncated out of the
    provided models.py excerpt".

    That is the whole failure: a budget is unavoidable, choosing the *front* of the file
    is not. Selection is by overlap with the identifiers the document marks up, which is
    a signal available at inference time from the document alone -- it must be, or this
    would be a leak rather than a retrieval step. It deliberately does NOT use
    `shared_identifiers`, which is the miner's evidence and names the drifted sentence.

    Elisions are marked and counted, for the same reason head-truncation was marked: a
    judge answering "no claim about this is made here" on silently-cut code is right
    about what it was shown and wrong about the file, and nothing in the output would
    tell the two apart.
    """
    if len(text) <= budget:
        return text, False
    lines = text.splitlines(keepends=True)
    keep: set[int] = set(range(min(_HEAD_LINES, len(lines))))

    # Score each line by how many of the document's identifiers it mentions, and collect
    # a window around the hits. The nearest enclosing `def`/`class` line is pulled in
    # alongside: a hit inside a function body with its signature cut away cannot answer
    # "does this parameter exist", which is most of what the documentation claims.
    windows: list[tuple[int, set[int]]] = []
    for index, line in enumerate(lines):
        hits = len(wanted & extract(line, versions=False))
        if not hits:
            continue
        if _DEF_RE.match(line):
            score = hits * _DEFINITION_WEIGHT
        elif _IMPORT_RE.match(line):
            score = 0
        else:
            score = hits * _MENTION_WEIGHT
        if not score:
            continue
        span = set(range(max(0, index - _CONTEXT_LINES),
                         min(len(lines), index + _CONTEXT_LINES + 1)))
        for back in range(index, max(-1, index - 60), -1):
            if _DEF_RE.match(lines[back]):
                span.add(back)
                break
        windows.append((score, span))

    # Highest-scoring windows first, so that what survives a tight budget is the densest
    # match rather than whatever happened to be earliest in the file.
    spent = sum(len(lines[i]) for i in keep)
    for _score, span in sorted(windows, key=lambda w: -w[0]):
        cost = sum(len(lines[i]) for i in span - keep)
        if spent + cost > budget:
            continue
        keep |= span
        spent += cost

    if len(keep) == len(lines):
        return text, False

    # Never return something that covers less of what the document talks about than the
    # head-truncation this replaced. Windowing can lose on a file whose relevant
    # definitions happen to sit in the first 6,000 characters: the budget goes to a
    # higher-scoring window further down and drops a definition the head included for
    # free. Measured on 29 real cut files before the weighting above, and it is not an
    # edge case, so it is checked rather than argued about.
    #
    # The comparison is on `wanted` -- the document's own identifiers -- which is the
    # signal this function is already allowed to see. Comparing on the drifted sentence
    # instead would pick the better arm using the answer, and would report a recovery
    # nothing could reproduce on a page whose answer is unknown.
    kept = "".join(lines[index] for index in sorted(keep))
    head, _ = _truncate(text, budget)
    if len(wanted & extract(head, versions=False)) > len(
        wanted & extract(kept, versions=False)
    ):
        return head, True

    out: list[str] = []
    elided = 0
    for index, line in enumerate(lines):
        if index in keep:
            if elided:
                out.append(f"\n... [{elided} line(s) elided] ...\n\n")
                elided = 0
            out.append(line)
        else:
            elided += 1
    if elided:
        out.append(f"\n... [{elided} line(s) elided] ...\n")
    out.append(
        f"\n[This file is {len(lines)} lines / {len(text):,} characters. The "
        f"{len(keep)} line(s) shown were selected as the ones mentioning identifiers "
        "the documentation marks up; the elided lines mention none of them.]\n"
    )
    return "".join(out), True


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
    # The page at `at_sha` with no budget applied, and it is NOT part of any prompt.
    # `render` does not read it, so adding it left every existing cache key
    # byte-identical -- the key is computed over the rendered text, not over this
    # dataclass.
    #
    # It exists because the per-claim judge enumerates the claims on the page, and
    # enumerating them from `doc_text` would rebuild the exact failure the per-claim
    # design exists to fix: `doc_text` is cut at `DOC_BUDGET`, the claim that motivated
    # all of this sits at character 22,461 of a 38,830-character page, and a judge asked
    # only about the first 12,000 characters cannot reach it however many questions it is
    # asked. Costing nothing in prompt tokens is what makes this affordable: the page is
    # read to decide WHAT to ask, and only the chosen sentence is sent.
    #
    # Not miner evidence. This is the document as any reader of that commit would find
    # it, which is the same standard `doc_text` meets; the things that must not reach a
    # prompt are the fix, its diff and its shared identifiers, and none of them is here.
    doc_full: str = ""

    @property
    def usable(self) -> bool:
        """False when there is nothing to judge against: no doc, or no code."""
        return bool(self.doc_text.strip()) and bool(self.code_files)

    @property
    def marked_identifier_coverage(self) -> float:
        """Share of the doc's backticked identifiers that appear in the code shown.

        The cheapest possible check on whether a context can be answered at all, and it
        should have been here before the first paid run rather than after it. The oracle
        arm scored the model at F1 0.40 with a 69% abstention rate, which read as a judge
        with no appetite for committing; the abstentions turned out to be correct and
        specific -- "the only code file provided is config.py, which defines ConfigDict,
        not Field". Median across the 45 shape-A cases: 16% at the time, 24% now.

        **READ THE DENOMINATOR BEFORE QUOTING THIS.** It was quoted once as evidence that
        the oracle arm shows the WRONG FILE, and that conclusion does not follow from this
        number. The denominator is every identifier the *whole document* marks up -- a
        median of 52 per page, spread over many topics -- while one code file will never
        contain most of them even when it is exactly the right file. 16% is therefore
        equally consistent with "the file is irrelevant" and "the file is right and the
        page is long", and a metric that cannot separate those two cannot justify a
        redesign. It was being used to justify one.

        The narrower denominator settles it and lives in `scripts/oracle_file_audit.py`,
        which cannot be computed here: it needs the drifted sentence's own identifiers,
        which is miner evidence that must never reach a prompt. Measured there, the
        commit's file is the single best-covering file in its pool in 37 of 45 cases and
        top-5 in 44 of 45. So this number is a warning that ONE FILE IS NOT ENOUGH -- the
        thing the `seeded` arm exists to fix -- and not evidence that the file is wrong.

        Not a judgement of the case, and deliberately not a filter. A document can
        legitimately discuss code in files other than the one on screen, and a low score
        here is a warning about the CONTEXT, not evidence about the documentation. It
        exists so that a run whose contexts cannot be answered says so on screen, next
        to the estimate, before anything is charged for.
        """
        marked = extract(literal_spans(self.doc_text), versions=False)
        if not marked:
            return 0.0
        present: set[str] = set()
        for code in self.code_files:
            present |= extract(code.text, versions=False)
        return len(marked & present) / len(marked)


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

    def __init__(
        self,
        clone_root: Path,
        *,
        k: int = DEFAULT_K,
        code_budget: int = CODE_BUDGET,
        doc_budget: int = DOC_BUDGET,
    ) -> None:
        self.clone_root = clone_root
        self.k = k
        # A parameter rather than the constant read at the point of use, so that raising
        # it is a recorded flag on one run instead of an edit that silently changes every
        # later run's cache key. The budget is INSIDE that key -- it changes the rendered
        # context -- so a run at a different budget re-pays for every case it touches,
        # and which budget produced a score has to be readable off the score file.
        self.code_budget = code_budget
        # The doc side is a parameter for a sharper reason than symmetry. Measured on the
        # 9 recall-costing cases of the 2026-09-19 seeded arm: on 3 of them the sentence
        # the fixing commit deleted sits BEYOND 12,000 characters -- char 22,461 of a
        # 38,830-character `docs/user/advanced.rst` -- so the false claim was never in the
        # prompt and no amount of code could have answered it. Doc truncation was counted
        # from the first run; whether it cut the CLAIM was not asked until now.
        self.doc_budget = doc_budget
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
        if arm in ("oracle", "seeded") and not case.code_path:
            raise ValueError(
                f"case {case.example_id} is shape {case.shape} and has no code_path; "
                f"the {arm} arm covers shape A only"
            )

        clone = self._clone(case.repo)
        doc_blobs = read_blobs(clone, case.at_sha, [case.doc_path])
        missing: list[str] = []
        raw_doc = doc_blobs.get(case.doc_path)
        if raw_doc is None:
            missing.append(case.doc_path)
            raw_doc = ""
        doc_text, doc_truncated = _truncate(raw_doc, self.doc_budget)

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

        # The selection signal: what the document itself marks up. Derived from the
        # document alone, so the same rule works at inference time on a repository
        # nobody has labelled.
        wanted = extract(literal_spans(raw_doc), versions=False)

        chosen: list[CodeFile] = []
        if arm in ("oracle", "seeded"):
            assert case.code_path is not None
            body = texts.get(case.code_path)
            if body is None:
                # The commit touched it, so it exists at the fix; absent at the parent
                # means the fix created it. Recorded rather than substituted -- a
                # quietly swapped-in retrieved file would put a different arm's
                # context under the oracle arm's label.
                missing.append(case.code_path)
            else:
                text, cut = select_relevant(body, self.code_budget, wanted)
                chosen.append(CodeFile(case.code_path, text, cut, rank=None))
        if arm in ("seeded", "retrieved"):
            ranked = self._ranker(case.repo, case.at_sha).rank(
                case.doc_path, raw_doc, pool
            )
            already = {c.path for c in chosen}
            for position, path in enumerate(ranked, start=1):
                if len(chosen) >= self.k:
                    break
                if path in already:
                    continue
                body = texts.get(path)
                if body is None:
                    missing.append(path)
                    continue
                text, cut = select_relevant(body, self.code_budget, wanted)
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
            doc_full=raw_doc,
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


def render_claim_batch(context: JudgeContext, claims) -> str:
    """The user turn for one batch of claims: the code, then the claims, and no page.

    Two decisions here, and both are the design rather than formatting.

    **The page body is absent.** Only the quoted sentences go in. That is what makes the
    arm affordable -- the priced version of this design measured the shared part as the
    context with no document in it, and putting the 12,000-character page back into all
    168 calls returns the cost to roughly the naive 25x row it was chosen over. It is also
    the point: the per-page judge had the whole page and did not audit it. What this gives
    up is real and belongs in the predictions rather than in a footnote -- a sentence can
    read as false out of the context that qualified it two paragraphs earlier, so this
    arm should be expected to lose precision, not just gain recall.

    **Code first, claims last.** Free to choose, because this rendering is new and every
    key it produces is new whatever order it uses -- the first version of this reasoning
    claimed the order would orphan the existing per-page cache, which was wrong and is
    corrected in `scripts/claim_units.py`. Code first is kept anyway, for the one reason
    that survives: it is the order in which a shared prefix would be cacheable if this
    arm is ever run one claim to a call, and choosing it now costs nothing while choosing
    it later would re-pay every reply.

    The claims are numbered from 1 within the batch, and the reply is required to carry
    the number back. Without that, a reply with fewer items than the batch cannot be
    aligned to the claims it answered, and a silently shifted alignment scores every
    verdict against the wrong sentence -- the same failure `parse_verdicts` avoids by
    splitting on case headers rather than zipping.
    """
    parts = [
        f"Repository: {context.repo}",
        f"Documentation file: {context.doc_path}",
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
        parts.append("")
    parts.append("--- CLAIMS ---")
    for number, claim in enumerate(claims, start=1):
        parts.append(f"{number}. {claim}")
    parts.append("--- END CLAIMS ---")
    return "\n".join(parts)


def context_hash(
    context: JudgeContext,
    prompt: str,
    model: str,
    *,
    request: Mapping[str, object],
    rendered: str | None = None,
) -> str:
    """Cache key for a judgement: everything that could change the answer.

    Keyed on the rendered content rather than on `example_id`, so editing the prompt
    invalidates the cache instead of serving answers from a harness that no longer
    exists. Getting this wrong is expensive in a way that looks free: a stale hit makes
    a change appear to have had no effect.

    `request` is the rest of the call -- the reply budget, the effort setting -- and it
    is required, keyword-only, and the reason this docstring is longer than the
    function. It was missing, while the sentence above used to claim the key covered
    "the prompt or the budgets". It did not cover the budgets. A 700-token reply budget
    truncated 16 of 45 replies mid-reasoning, each was cached as an empty answer, and
    the fix -- a larger budget -- would have served all 16 truncations straight back
    with no call made, no charge, and nothing on screen to suggest the new budget had
    not been tried. A false claim about the code, in the docstring of a tool for
    finding false claims about code. The signature is now shaped so that a caller
    cannot forget the argument, which is the only version of this that stays true.

    `rendered` overrides what gets hashed as the user turn, for a caller whose prompt is
    not `render(context)` -- the per-claim judge, whose turn holds the code and one batch
    of claims. It defaults to None meaning `render(context)`, so every key computed before
    this parameter existed is byte-identical to the one computed now. That property is the
    reason it is an override rather than a second function: two hash functions over the
    same fields is how a subtle divergence gets introduced, and there is no way to notice
    it except by a cache that stops hitting.
    """
    digest = hashlib.blake2b(digest_size=16)
    pieces = [
        model,
        prompt,
        context.arm,
        render(context) if rendered is None else rendered,
    ]
    # Sorted by key, so the same request written in a different order is the same hash
    # -- otherwise the invalidation this exists for would fire at random.
    pieces += [f"{name}={request[name]!r}" for name in sorted(request)]
    for piece in pieces:
        digest.update(piece.encode("utf-8", "replace"))
        digest.update(b"\x00")
    return digest.hexdigest()
