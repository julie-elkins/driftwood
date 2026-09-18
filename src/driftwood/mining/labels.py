"""Turn commits into labelled documentation-drift examples.

The claim this module makes is narrow and worth stating precisely: when a human
commit corrects documentation, the tree state immediately *before* that commit
contained documentation that was false, and a human confirmed it by fixing it.
That is a label nobody had to hand-write.

Two positive shapes, because I do not know which is cleaner and would rather
measure than assume:

  Shape A -- co-change. One commit modifies a doc and some code, and the two
    diffs share an identifier. Suspected noise: feature-plus-its-documentation,
    where the doc was not wrong before, it just did not exist yet.

  Shape B -- doc-only fix. A commit modifies documentation and touches no code
    at all. The code did not move, so whatever was corrected was already false.
    Expected to be cleaner but rarer, and it does not tell us which code the
    claim was about -- which is fine, because making retrieval find that is part
    of what we want to test.

Every positive gets a matched negative: the same doc at the fixing commit
itself. Same file, same repo, seconds apart in project time, differing only in
whether the correction landed. If a detector fires equally on both states it is
not detecting drift, it is reacting to something about the file.

The honest asymmetry, which belongs in the README and in any number we publish:
a doc nobody fixed is not a doc that was correct. It may be drift nobody noticed.
Our positives are strong evidence; our negatives are weaker, and absence of a fix
is not evidence of cleanliness.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from . import identifiers
from .gitio import (
    ChangedFile,
    Commit,
    changed_lines,
    changed_sides,
    commit_time,
    diff_line_counts,
    file_diff,
    head_sha,
    iter_commits,
    list_files,
)
from .paths import TEST_PATH_MARKERS, Kind, classify

__all__ = ["Example", "MineConfig", "mine_repo", "LABEL_DRIFT", "LABEL_CLEAN"]

LABEL_DRIFT = "drift"
LABEL_CLEAN = "clean"

BASIS_DOC_ONLY = "doc_only_commit_modified_existing_prose"
BASIS_COCHANGE = "doc_and_code_both_modified_sharing_identifier"
BASIS_POST_FIX = "state_immediately_after_human_fix"
BASIS_NEVER_COCHANGED = "pair_never_cochanged_in_mined_history"
BASIS_NEVER_COCHANGED_RELATED_PATH = "pair_never_cochanged_but_path_related"

SHAPE_NEGATIVE = "negative"
SHAPE_NEGATIVE_EASY = "negative_easy"

# Path tokens too common to imply that two files are about the same thing. Without
# this, every doc shares `docs` with every other doc and every module shares `src`,
# so "related paths" degenerates back into a uniform draw while looking selective.
_GENERIC_PATH_TOKENS = frozenset(
    {
        "api", "src", "lib", "docs", "doc", "documentation", "guide", "guides",
        "index", "readme", "readme_md", "main", "core", "utils", "util", "common",
        "base", "misc", "internal", "advanced", "usage", "reference", "overview",
        "intro", "introduction", "quickstart", "tutorial", "tutorials", "examples",
        "example", "test", "tests", "init", "py", "md", "rst", "txt", "source",
    }
)

# Doc-only commits whose subject says the change was cosmetic. These are real
# doc edits but not drift: nothing about the code was ever misdescribed. Left in,
# they would swamp shape B, because typo fixes are the most common doc commit
# there is.
COSMETIC_SUBJECT_MARKERS = (
    "typo", "typos", "spelling", "misspell", "grammar", "punctuation",
    "capitali", "whitespace", "trailing", "indent", "formatting", "reformat",
    "lint", "prettier", "markdownlint", "rephrase", "reword", "wording",
    "broken link", "dead link", "fix link", "fix links", "update link",
    "bump", "changelog", "release notes", "version number",
    "translat", "i18n", "l10n",
)

# Docs-build refactors. Projects that embed runnable examples reference them by
# generated path -- FastAPI's docs cite `docs_src/.../tutorial001.py` -- so
# renumbering or relocating the examples rewrites many documentation lines while
# changing no claim about the library. Matched against the doc's changed lines
# rather than its filename, because the moved path appears in the content.
_DOCS_BUILD_PATH_RE = re.compile(r"tutorial\d+|docs_src")


@dataclass(frozen=True)
class MineConfig:
    # A commit touching more files than this is a refactor, a merge-by-hand or a
    # mass rename. Whatever it is, we cannot attribute a doc fix to any one code
    # change inside it.
    max_files_in_commit: int = 20
    # How much identifier overlap counts as "these two diffs are about the same
    # thing". One is a deliberately low bar; the hand-review tells us whether it
    # needs raising.
    min_shared_identifiers: int = 1
    # Guards against a commit with many docs and many code files producing a
    # combinatorial pile of weak pairs.
    max_pairs_per_commit: int = 6
    # A doc diff of one changed line is usually a link or a word. Real drift
    # corrections tend to touch a clause or more.
    min_doc_lines_changed: int = 2
    drop_cosmetic_subjects: bool = True
    # Both added 2026-09-18 from the first hand-review, where mechanical repo-wide
    # sweeps (org rename, http->https) were the dominant false positive. Kept as
    # flags rather than baked in, so their contribution stays measurable.
    drop_urls: bool = True
    drop_code_comments: bool = True
    # Shape B only. Require that the doc stopped asserting some identifier -- see
    # identifiers.delta. Added 2026-09-18 because the first hand-review scored
    # shape B at 0/20 with 12 of 20 cosmetic, and none of the filters above
    # touched a single one of them: `psf/requests` writes commit subjects like
    # "docs", so the subject-marker filter had nothing to read.
    require_removed_identifier: bool = True
    # Treat dotted version literals as identifiers. Additive, so its effect needs
    # fresh labels rather than the retention test.
    match_versions: bool = True
    # Negatives from doc/code pairs that never co-changed anywhere in the mined
    # window. Zero by default: switching them on changes the corpus composition, and
    # every count previously reported would silently mean something different.
    #
    # These are the only negatives that permit a false-positive rate at all. Matched
    # negatives answer "does the detector notice the fix?"; they cannot answer "does
    # the detector stay quiet on an unrelated pair?", because in a matched negative
    # the doc genuinely is about that code.
    easy_negatives_per_repo: int = 0
    # Sampling is seeded per repo, because the manifest promises byte-identical
    # replay and an unseeded draw would break that promise silently.
    easy_negative_seed: int = 17
    # Shape A only. Require that some identifier was *withdrawn* from both the doc
    # and the code, not merely that the two diffs share one. Added 2026-09-18 after
    # the second hand-review, where `new` -- a feature landing with its own
    # documentation -- was the largest shape-A error class at 8 of 25, having been
    # entirely absent from the first review's 40 cases. `new` adds a symbol to both
    # sides; a correction withdraws one. This is the same asymmetry
    # `require_removed_identifier` already exploits on the other arm.
    #
    # DEFAULT OFF, deliberately. It catches 8 of 8 `new` cases but also discards 2
    # of 7 true positives, taking measured precision 28% -> 38% at an unmeasured
    # cost in recall -- and that 38% is fitted to the same 25 cases that motivated
    # the rule. Turning it on by default would bake a recall loss into the corpus on
    # the strength of a number that has not been tested out of sample. Left as a
    # flag so a third review can settle it.
    require_withdrawn_claim: bool = False
    # Shape B only. Drop doc changes that are really a docs-build refactor: a
    # tutorial or example include path being renamed or moved. Left deliberately
    # unfiltered through the second review so that its cost would be measured rather
    # than guessed at -- it turned out to be 3 of 20 cases, all `cosmetic`, and
    # removing them costs no true positive at all (35% -> 41%). A pure subtraction
    # with a measured price is worth defaulting on.
    drop_docs_build_paths: bool = True
    # Shape B only. Judge the doc side on marked-up code spans and version literals
    # rather than on all of its prose. Added after reading the first shape-B sheet
    # generated under `require_removed_identifier`, where the surviving cases were
    # firing on HTML attribute names from dead-link removals and on prose nouns
    # like `guarantee` and `stability`. Both are reworded English, and English is
    # most of what a doc contains.
    doc_literals_only: bool = True
    # Shape B only. Reject a doc-only commit whose withdrawn evidence is *entirely*
    # version literals, with no symbol behind it.
    #
    # Added 2026-09-18 from the third review, and it is the best-evidenced filter here
    # -- the split was computed from 37 already-judged cases that were labelled for
    # other reasons, so 9 of the 10 cases it drops were judged before the rule existed.
    # Those ten scored 0/10 (ub 28%) where the rest of the arm scored 12/27 = 44%.
    #
    # The mechanism, from reading all ten: shape B has no code diff, so a withdrawn
    # version literal cannot be checked against anything. What actually withdraws one
    # is a doc rewriting its own example output -- a `User-Agent: python-requests/0.13.1`
    # line, a MIME boundary, a console transcript -- or listing third-party projects'
    # versions, neither of which is a claim about this codebase. The genuine cases
    # ("supports Python 3.3-3.5", "PyPy-c 1.7") are real claims but came back
    # `unclear` every time, because a doc-only commit dropping a support line does not
    # show whether support ended.
    #
    # `ver:` stays on for shape A, where the same claim IS checkable: there the literal
    # has to appear in the code diff too, which is how `python_requires` moving gets
    # caught. Same token, opposite value, because the two arms have different evidence.
    #
    # DEFAULT OFF like the rest, so the corpus does not change under a rule whose price
    # in recall is still zero-measured. Purely subtractive, so `retention` can price it
    # against the existing sheets without relabelling anything.
    require_symbol_beyond_version: bool = False


@dataclass(frozen=True)
class Example:
    example_id: str
    repo: str
    label: str
    label_basis: str
    shape: str  # "A" | "B" | "negative"
    doc_path: str
    code_path: str | None
    at_sha: str  # the tree state this label describes
    fix_sha: str  # the commit that did the correcting
    parent_sha: str
    committed_at: int
    subject: str
    doc_lines_added: int
    doc_lines_removed: int
    files_in_commit: int
    shared_identifiers: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict:
        out = asdict(self)
        out["shared_identifiers"] = list(self.shared_identifiers)
        return out


def _example_id(repo: str, at_sha: str, doc_path: str, code_path: str | None, label: str) -> str:
    """Stable id, so re-running the miner produces a diffable label set.

    Without this the label file churns completely on every run and you cannot see
    what changing a threshold actually did to your data.
    """
    payload = "\x00".join([repo, at_sha, doc_path, code_path or "", label])
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _looks_cosmetic(subject: str) -> bool:
    lowered = subject.lower()
    return any(marker in lowered for marker in COSMETIC_SUBJECT_MARKERS)


def _partition(files: tuple[ChangedFile, ...]) -> tuple[list[ChangedFile], list[ChangedFile], int]:
    docs, code, other = [], [], 0
    for changed in files:
        kind = classify(changed.path)
        if kind is Kind.DOC:
            docs.append(changed)
        elif kind is Kind.CODE:
            code.append(changed)
        else:
            other += 1
    return docs, code, other


def _matched_negative(positive: Example) -> Example:
    """The same doc/code pair one commit later, after the human fixed it."""
    return Example(
        example_id=_example_id(
            positive.repo, positive.fix_sha, positive.doc_path, positive.code_path, LABEL_CLEAN
        ),
        repo=positive.repo,
        label=LABEL_CLEAN,
        label_basis=BASIS_POST_FIX,
        shape="negative",
        doc_path=positive.doc_path,
        code_path=positive.code_path,
        at_sha=positive.fix_sha,
        fix_sha=positive.fix_sha,
        parent_sha=positive.parent_sha,
        committed_at=positive.committed_at,
        subject=positive.subject,
        doc_lines_added=positive.doc_lines_added,
        doc_lines_removed=positive.doc_lines_removed,
        files_in_commit=positive.files_in_commit,
        shared_identifiers=positive.shared_identifiers,
    )


def _mine_commit(
    repo_dir: Path, repo: str, commit: Commit, cfg: MineConfig
) -> Iterator[Example]:
    parent = commit.parent
    if parent is None:  # root commit, or a merge that slipped through
        return
    if len(commit.files) > cfg.max_files_in_commit:
        return
    if cfg.drop_cosmetic_subjects and _looks_cosmetic(commit.subject):
        return

    docs, code, _other = _partition(commit.files)

    # Only *modified* docs. An added doc cannot have been wrong before it existed,
    # and this single filter is what separates drift from new documentation.
    modified_docs = [d for d in docs if d.status == "M"]
    if not modified_docs:
        return

    # Shape B: nothing but documentation changed in this commit.
    doc_only = not code and len(docs) == len(commit.files)

    for doc in modified_docs:
        doc_diff = file_diff(repo_dir, parent, commit.sha, doc.path, old_path=doc.old_path)
        added, removed = diff_line_counts(doc_diff)
        if added + removed < cfg.min_doc_lines_changed:
            continue

        if doc_only:
            if cfg.drop_docs_build_paths and _DOCS_BUILD_PATH_RE.search(
                changed_lines(doc_diff)
            ):
                continue
            doc_added, doc_removed = changed_sides(doc_diff)
            sides = identifiers.delta(
                doc_added,
                doc_removed,
                drop_urls=cfg.drop_urls,
                versions=cfg.match_versions,
                literals_only=cfg.doc_literals_only,
            )
            if cfg.require_removed_identifier and not sides["removed_only"]:
                continue
            if cfg.require_symbol_beyond_version and not any(
                not token.startswith("ver:") for token in sides["removed_only"]
            ):
                continue
            positive = Example(
                example_id=_example_id(repo, parent, doc.path, None, LABEL_DRIFT),
                repo=repo,
                label=LABEL_DRIFT,
                label_basis=BASIS_DOC_ONLY,
                shape="B",
                doc_path=doc.path,
                code_path=None,
                at_sha=parent,
                fix_sha=commit.sha,
                parent_sha=parent,
                committed_at=commit.committed_at,
                subject=commit.subject,
                doc_lines_added=added,
                doc_lines_removed=removed,
                files_in_commit=len(commit.files),
                # What the doc stopped saying. Carried onto the example so the
                # review sheet can show the reviewer the signal the miner fired
                # on. In the first review 8 of 20 shape-B cases came back
                # `unclear`, and the sheet showing a bare doc diff with no stated
                # reason is at least part of why.
                shared_identifiers=tuple(sides["removed_only"][:12]),
            )
            yield positive
            yield _matched_negative(positive)
            continue

        # Shape A: pair this doc against each modified code file, keeping only
        # pairs whose diffs talk about the same identifiers.
        doc_changed_text = changed_lines(doc_diff)
        emitted = 0
        for source in code:
            if source.status != "M":
                continue  # an added or deleted file is a feature, not a correction
            if emitted >= cfg.max_pairs_per_commit:
                break
            code_diff = file_diff(
                repo_dir, parent, commit.sha, source.path, old_path=source.old_path
            )
            overlap = identifiers.shared(
                doc_changed_text,
                changed_lines(code_diff),
                drop_urls=cfg.drop_urls,
                drop_code_comments=cfg.drop_code_comments,
                versions=cfg.match_versions,
            )
            if len(overlap) < cfg.min_shared_identifiers:
                continue
            if cfg.require_withdrawn_claim:
                # Compare the two *removed* sides only. A feature commit adds a
                # symbol to the doc and to the code, so it shares tokens without
                # withdrawing any; a correction takes the old claim out of both.
                _, doc_removed_text = changed_sides(doc_diff)
                _, code_removed_text = changed_sides(code_diff)
                if not identifiers.shared(
                    doc_removed_text,
                    code_removed_text,
                    drop_urls=cfg.drop_urls,
                    drop_code_comments=cfg.drop_code_comments,
                    versions=cfg.match_versions,
                ):
                    continue
            positive = Example(
                example_id=_example_id(repo, parent, doc.path, source.path, LABEL_DRIFT),
                repo=repo,
                label=LABEL_DRIFT,
                label_basis=BASIS_COCHANGE,
                shape="A",
                doc_path=doc.path,
                code_path=source.path,
                at_sha=parent,
                fix_sha=commit.sha,
                parent_sha=parent,
                committed_at=commit.committed_at,
                subject=commit.subject,
                doc_lines_added=added,
                doc_lines_removed=removed,
                files_in_commit=len(commit.files),
                shared_identifiers=tuple(overlap[:12]),
            )
            yield positive
            yield _matched_negative(positive)
            emitted += 1


def _path_tokens(path: str) -> frozenset[str]:
    """Meaningful words in a path, as a crude proxy for what a file is about.

    `docs/api/cookies.rst` and `requests/cookies.py` share `cookies`. That is not a
    claim that either describes the other -- it is only enough of a hint to sample a
    negative that is harder than a random one.
    """
    words = re.split(r"[^A-Za-z0-9]+", path.lower())
    return frozenset(
        word for word in words if len(word) >= 3 and word not in _GENERIC_PATH_TOKENS
    )


def _stem(path: str) -> str:
    return PurePosixPath(path).stem.lower()


def _looks_related(doc_path: str, code_path: str) -> bool:
    """Whether two paths suggest, on name alone, that they describe one thing.

    Stem equality counts even when the stem is in `_GENERIC_PATH_TOKENS`, and that
    exception is the whole point. `docs/api.rst` against `src/requests/api.py` is an
    obviously related pair; the stoplist reduces both paths to no tokens at all, so a
    token-only test calls them unrelated and files one of the hardest available
    negatives in the tier reserved for the easiest. That inverts what the number
    means -- a detector firing there would be counted against the arm cited to show
    it does not fire on nonsense.
    """
    if _stem(doc_path) == _stem(code_path):
        return True
    return bool(_path_tokens(doc_path) & _path_tokens(code_path))


# Doc-shaped files that are not documentation *about the code*. `classify` keeps
# them on purpose -- a README at a repo root is prime drift territory, and the
# classifier has no cheap way to tell that one from `tests/certs/README.md`, so it
# errs towards keeping. Sampling negatives can afford the distinction, so it is drawn
# here rather than by widening `classify`: that would change the positive corpus and
# break the byte-identical replay every committed manifest promises, in exchange for
# a contamination measured at 3 rows in 5098.
_EXCLUDED_DOC_LOCATIONS = (*TEST_PATH_MARKERS, ".github/")


def _documents_code(path: str) -> bool:
    lowered = path.lower()
    return not any(marker in lowered for marker in _EXCLUDED_DOC_LOCATIONS)


def _easy_negatives(
    repo_dir: Path,
    repo: str,
    cfg: MineConfig,
    rev: str,
    cochanged: frozenset[tuple[str, str]],
    seen: set[str],
) -> Iterator[Example]:
    """Negatives from doc/code pairs with no history of changing together.

    What this is for, precisely: matched negatives cannot measure a false-positive
    rate. In a matched negative the doc really is about that code -- it was about it
    one commit earlier, wrongly. So a detector that fires on everything scores well
    on them. These pairs are the control: a detector with any specificity must stay
    silent on a pair that has no relationship at all.

    Two flavours are emitted, distinguished by `label_basis`, because a single
    blended specificity number would hide the only interesting part:

    * `BASIS_NEVER_COCHANGED` -- a random pair whose paths suggest no relationship.
      Genuinely easy: `docs/index.rst` against `flask/cli.py` is not a judgement
      call. A detector that fires here is broken, so this measures a floor and little
      else. Pairs that *do* look related are excluded from this arm rather than left
      to land in it by chance, or the easy tier quietly contains hard cases.
    * `BASIS_NEVER_COCHANGED_RELATED_PATH` -- the paths share a distinctive word or a
      filename, so the pair looks related and never was. Much closer to what stage 2
      retrieval will actually hand the detector, and therefore the number that will
      matter.

    Neither is the real production distribution, which is whatever retrieval decides
    to surface, and retrieval does not exist yet. Sampling uniformly over all pairs
    when the deployed system will see pre-filtered plausible pairs would price
    specificity far too cheaply; the related-path arm exists to keep that honest
    until the real distribution can be measured.

    Two further limits, worth restating wherever these numbers are reported:

    * "Never co-changed in the mined window" is weaker than it sounds. The window is
      bounded by `--limit`, so a pair that co-changed just outside it looks unrelated
      here. Widening the window can only shrink this set, never grow it.
    * A never-co-changed pair is *presumed* clean, not confirmed clean. Nobody read
      it. A doc can perfectly well be false about code it was never edited alongside
      -- that is arguably the most interesting kind of drift, and it is exactly what
      this label cannot see. So these support a false-positive rate and must not be
      quoted as accuracy.
    """
    tree = list_files(repo_dir, rev)
    docs = sorted(
        path
        for path in tree
        if classify(path) is Kind.DOC and _documents_code(path)
    )
    code = sorted(path for path in tree if classify(path) is Kind.CODE)
    if not docs or not code:
        return

    at_sha = head_sha(repo_dir, rev)
    when = commit_time(repo_dir, rev)
    # Seeded on the repo so each repo draws independently and reproducibly. Every
    # collection sampled from below is a sorted list rather than a set: set iteration
    # order over strings varies with PYTHONHASHSEED, which would make the draw differ
    # between processes and quietly break the manifest's byte-identical replay.
    rng = random.Random(f"{repo}:{cfg.easy_negative_seed}")

    # Indexes from token and from filename to code files, so a plausible counterpart
    # for a doc can be found without materialising the full docs x code product.
    code_by_token: dict[str, list[str]] = {}
    code_by_stem: dict[str, list[str]] = {}
    for path in code:
        for token in _path_tokens(path):
            code_by_token.setdefault(token, []).append(path)
        code_by_stem.setdefault(_stem(path), []).append(path)

    candidate_cache: dict[str, list[str]] = {}

    def related_candidates(doc_path: str) -> list[str]:
        """Code files this doc looks related to. Sorted, because set iteration order
        over strings varies with PYTHONHASHSEED and the draw has to be replayable."""
        if doc_path not in candidate_cache:
            found = set(code_by_stem.get(_stem(doc_path), ()))
            for token in _path_tokens(doc_path):
                found.update(code_by_token.get(token, ()))
            candidate_cache[doc_path] = sorted(found)
        return candidate_cache[doc_path]

    def emit(doc_path: str, code_path: str, basis: str) -> Example | None:
        if (doc_path, code_path) in cochanged:
            return None
        example_id = _example_id(repo, at_sha, doc_path, code_path, LABEL_CLEAN)
        if example_id in seen:
            return None
        seen.add(example_id)
        return Example(
            example_id=example_id,
            repo=repo,
            label=LABEL_CLEAN,
            label_basis=basis,
            shape=SHAPE_NEGATIVE_EASY,
            doc_path=doc_path,
            code_path=code_path,
            at_sha=at_sha,
            # There is no fixing commit. Empty rather than reusing `at_sha`, so that
            # anything joining on `fix_sha` cannot mistake this for a correction.
            fix_sha="",
            parent_sha="",
            committed_at=when,
            subject=f"(no commit: {doc_path} and {code_path} never co-changed)",
            doc_lines_added=0,
            doc_lines_removed=0,
            files_in_commit=0,
        )

    # Split the request evenly. The related-path arm can come up short in a repo
    # whose plausible pairs have all co-changed -- which is the healthy case -- and
    # the shortfall is left as a shortfall rather than topped up from the easy arm,
    # because silently substituting easier negatives would inflate specificity.
    related_target = cfg.easy_negatives_per_repo // 2
    uniform_target = cfg.easy_negatives_per_repo - related_target

    # Docs with at least one plausible counterpart, precomputed so the sampler is not
    # rejecting on doc choice as well as on co-change.
    related_docs = sorted(path for path in docs if related_candidates(path))

    # Rejection sampling with a hard budget on each arm. Without the cap, a repo
    # whose every plausible pair has co-changed would spin here rather than returning
    # fewer examples, and the mine would hang instead of reporting a small number.
    emitted = 0
    for _ in range(max(related_target * 50, 1000)):
        if emitted >= related_target or not related_docs:
            break
        doc_path = rng.choice(related_docs)
        code_path = rng.choice(related_candidates(doc_path))
        example = emit(doc_path, code_path, BASIS_NEVER_COCHANGED_RELATED_PATH)
        if example is not None:
            emitted += 1
            yield example

    emitted = 0
    for _ in range(max(uniform_target * 50, 1000)):
        if emitted >= uniform_target:
            break
        doc_path = rng.choice(docs)
        code_path = rng.choice(code)
        # A pair that looks related belongs in the other arm. Letting it land here by
        # chance is how an "easy" specificity number comes to contain the hard cases.
        if _looks_related(doc_path, code_path):
            continue
        example = emit(doc_path, code_path, BASIS_NEVER_COCHANGED)
        if example is not None:
            emitted += 1
            yield example


def mine_repo(
    repo_dir: Path,
    repo: str,
    cfg: MineConfig | None = None,
    *,
    limit: int | None = None,
    since: str | None = None,
    rev: str = "HEAD",
) -> Iterator[Example]:
    cfg = cfg or MineConfig()
    # Deduplicate on example_id. An id keys the *state being labelled* -- repo, tree
    # sha, paths, label -- and deliberately omits `fix_sha`, so two different commits
    # sharing a parent and correcting the same doc describe one example, not two.
    # That happens for real: cherry-picked and rebased fixes land twice from the same
    # base, and `pallets/flask` has two such pairs in 4000 commits.
    #
    # Found because a manifest recorded 5314 examples while the scorer, which keys by
    # id, read 5312. Left unfixed the duplicate inflates any precision denominator it
    # falls into, and every dict-keyed consumer drops one row silently -- no error, no
    # warning, just a count that quietly disagrees with the file.
    #
    # Matched negatives are keyed on `fix_sha` instead, so the two post-fix states
    # remain distinct examples and both survive. That is correct: they are genuinely
    # different trees.
    seen: set[str] = set()
    cochanged: set[tuple[str, str]] = set()
    for commit in iter_commits(repo_dir, limit=limit, since=since, rev=rev):
        # Co-occurrence is recorded from EVERY commit walked, including the ones the
        # filters below reject. A pair that changed together in a discarded commit
        # still has a real relationship, and calling it unrelated would drop a
        # genuine drift candidate into the negative set -- a label that is not merely
        # missing but wrong, and wrong in the direction that flatters the detector.
        docs, code, _other = _partition(commit.files)
        for doc in docs:
            for source in code:
                cochanged.add((doc.path, source.path))
                # Renames: a pair is related under its old name too, otherwise the
                # rename makes history look like it never happened.
                if doc.old_path:
                    cochanged.add((doc.old_path, source.path))
                if source.old_path:
                    cochanged.add((doc.path, source.old_path))

        for example in _mine_commit(repo_dir, repo, commit, cfg):
            if example.example_id in seen:
                continue
            seen.add(example.example_id)
            yield example

    if cfg.easy_negatives_per_repo:
        yield from _easy_negatives(
            repo_dir, repo, cfg, rev, frozenset(cochanged), seen
        )
