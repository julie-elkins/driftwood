"""Doc->code relevance judged by a human, with no ranker in the candidate set.

Stage 2c. The retrieval eval's ground truth is mined shape-A pairs, and shape A
proposes a doc and a code file only when they already share an identifier -- so the
corpus is selected for exactly the signal `Lexical` consumes, and the dense arm's
5-of-5 loss is confounded with that selection rule. This module builds ground truth
that rule never touched.

**Two designs were rejected first, and the reasons are the design.**

*Judge ranker output.* Cheap, and useless: showing a human lexical's top 10 measures
whether lexical's suggestions are good, and a pair dense found but lexical missed can
never enter the corpus. Whichever ranker builds the candidate set wins.

*Judge random pairs.* Unbiased and unaffordable. Pools run 22 to 685 files with a
handful relevant, so the positive rate is around 1% -- thirty judgements would return
roughly zero positives and no amount of care fixes that.

So the unit of judgement is the **document**, not the pair: a human reads one doc and
marks which code files it makes claims about, choosing from the whole pool. The
candidate set is the repository tree, which has no opinion. Any pair either ranker
could find is reachable, including pairs neither one ranks.

**The condition this stage was first specified with does not exist.** The plan said
"pairs whose doc prose shares no identifier with its code". Measured across the 2135
existing judged pairs, that population is 2 pairs -- 0.09%. The median pair shares 18
to 65 identifiers, because at file granularity a 10k-character document and a 5k-
character module share something regardless of what either is about. Overlap at file
granularity is therefore not a usable partition, and the honest version of the
question is not "pairs with no overlap" but "pairs no overlap rule selected".

**Nothing here is ablated, and that is correct rather than an omission.** The ablation
arm exists to bound circularity injected by the mining rule: it strikes the tokens
that caused a pair to be proposed. These pairs were proposed by a person reading
prose, so there is no such channel and nothing to strike. A `lexical-ablated` row on
this corpus would be a second copy of `lexical`.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path

from ..mining.gitio import head_sha, list_files, local_name_for, read_blobs
from ..mining.paths import Kind, classify
from .dataset import Query, RepoSplit

__all__ = [
    "MIN_DOC_CHARS",
    "DocCase",
    "SheetSpec",
    "eligible_docs",
    "parse_sheet",
    "render_sheet",
    "sample_cases",
    "splits_from_sheet",
    "write_bundle",
]

# Below this a file cannot make a substantive claim about a module -- badges, a
# one-line pointer, a stub. Recorded as a number rather than a judgement so the
# threshold is visible and arguable.
MIN_DOC_CHARS = 400

# Process documentation that `classify` admits as DOC because it is a technical-looking
# .md outside the excluded stems. A pull-request template makes no claim about any
# module, so it is excluded *here* rather than in `classify`: changing the classifier
# would change what the miner produces and silently break comparability with every
# label set already on disk. See the plan file -- it is an open question for the
# miner, not something to fix as a side effect of building a review sheet.
PROCESS_DOC_MARKERS = (".github/", "docs/_templates/")


@dataclass(frozen=True)
class DocCase:
    """One document to be judged, and the pool it will be judged against."""

    repo: str
    sha: str
    doc_path: str
    doc_chars: int
    pool: tuple[str, ...]


@dataclass(frozen=True)
class SheetSpec:
    repo: str
    sha: str
    cases: tuple[DocCase, ...]


def eligible_docs(paths: list[str], texts: dict[str, str]) -> list[str]:
    """Docs that could plausibly make a claim about a module.

    Two exclusions, both mechanical and both recorded: process documentation, and
    anything too short to assert something. Neither looks at what the doc is *about*,
    so neither can favour a ranker.
    """
    out = []
    for path in sorted(paths):
        if any(marker in path for marker in PROCESS_DOC_MARKERS):
            continue
        if len(texts.get(path, "")) < MIN_DOC_CHARS:
            continue
        out.append(path)
    return out


def sample_cases(
    repo: str,
    clone: Path,
    per_repo: int,
    seed: int,
    sha: str | None = None,
) -> SheetSpec:
    """Sample documents uniformly from the eligible set at one tree.

    Uniform rather than stratified. Stratifying by identifier density was considered
    and dropped: the observed range is compressed (16 to 49 per 1k characters) and the
    top of it is entirely short process files, so the strata would have differed by
    file length more than by prose style. A uniform draw with a recorded seed is
    weaker at targeting the interesting cases and much harder to argue with.

    Drawn by shuffling the whole candidate list once and taking a prefix, rather than
    by `rng.sample(candidates, n)`. The two are equally uniform, but only the prefix
    is **nested**: at the same seed, `per_repo=9` contains every document `per_repo=6`
    chose. Sheets get extended -- a sample where docs making no claim about any module
    turn out to be common yields fewer scoreable queries than cases, and the answer is
    to label more. With `sample`, extending redraws from scratch, so half the finished
    judgements fall outside the new set and the choice becomes keep-the-old-sheet or
    waste-the-work. With a prefix, extending is additive and no completed judgement is
    stranded.

    What this does *not* license: drawing a second sample, seeing which one gives the
    nicer answer, and reporting that one. Extending is only sound because every case
    drawn is labelled and counted -- the stopping rule has to be a query count set in
    advance, never the result.
    """
    at = sha or head_sha(clone)
    files = list_files(clone, at)
    pool = tuple(sorted(p for p in files if classify(p) is Kind.CODE))
    docs = [p for p in files if classify(p) is Kind.DOC]
    texts = read_blobs(clone, at, docs)
    candidates = eligible_docs(docs, texts)

    order = list(candidates)
    random.Random(seed).shuffle(order)
    chosen = sorted(order[:per_repo])
    cases = tuple(
        DocCase(
            repo=repo,
            sha=at,
            doc_path=path,
            doc_chars=len(texts.get(path, "")),
            pool=pool,
        )
        for path in chosen
    )
    return SheetSpec(repo=repo, sha=at, cases=cases)


_HEADER = """# Doc -> code relevance — stage 2c

**The question, for each document:** which code files does this document make claims
about? A claim is any assertion about behaviour, signature, defaults or errors that
could be checked against the code and could one day be wrong about it.

Mark a file by putting an `x` in its box: `- [x] src/flask/app.py`

Rules that matter for the measurement:

- **Mark every file the doc makes claims about, not the best one.** There is no cap.
- **Do not guess.** If you cannot tell without reading the code, read the code — every
  candidate file is written out next to the doc.
- **If the doc makes no claim about any specific file, mark `NONE`.** An install guide
  or a contributing note is a real answer, not a skipped case.
- **The checklist is not a limit.** Anything missing goes on the `EXTRA` line.
- **Leave a case entirely unmarked to skip it.** Partial sheets score fine: results
  are reported per repo and per case count, never pooled into one number.

Nothing here was suggested by a ranker. The candidate list is the repository tree at
one commit, in path order.
"""


def render_sheet(specs: list[SheetSpec], bundle: Path, seed: int) -> str:
    """The sheet, with the pool as a literal checklist.

    A checklist works because these pools are 22 to 35 files. It does not scale --
    fastapi's median pool is 685 -- and rather than paginate it, large-pool repos are
    out of scope for this sheet and the `EXTRA` line is the escape hatch. Stated in
    the plan file as a limitation, since the two repos where the dense loss was
    individually readable are exactly the two excluded.
    """
    total = sum(len(spec.cases) for spec in specs)
    lines = [_HEADER, "", f"{total} documents, seed {seed}.", "", "---", ""]
    number = 0
    for spec in specs:
        for case in spec.cases:
            number += 1
            text_path = bundle / "text" / _flat(case.repo) / "doc" / _flat(case.doc_path)
            lines += [
                f"## Case {number} — `{case.repo}` · `{case.doc_path}`",
                "",
                f"- **read** `{text_path}` ({case.doc_chars} chars)",
                f"- **code** `{bundle / 'text' / _flat(case.repo) / 'code'}`",
                f"- **tree** `{case.sha[:12]}`",
                "",
            ]
            for path in case.pool:
                lines.append(f"- [ ] {path}")
            lines += [
                "",
                "**NONE:** [ ]",
                "",
                "**EXTRA:**",
                "",
                "**NOTES:**",
                "",
                "---",
                "",
            ]
    return "\n".join(lines)


def _flat(path: str) -> str:
    return path.replace("/", "-")


def write_bundle(specs: list[SheetSpec], bundle: Path, seed: int, clone_root: Path) -> Path:
    """Write the sheet plus every document and candidate file it refers to.

    The clones are bare, so there is no working tree to open a file from -- without
    this the reviewer would have to run `git show` per file to answer anything. The
    pool is written out as well as the docs, because "does this doc make a claim about
    this module" is frequently not answerable from the doc alone.
    """
    bundle.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        clone = clone_root / local_name_for(spec.repo)
        base = bundle / "text" / _flat(spec.repo)
        (base / "doc").mkdir(parents=True, exist_ok=True)
        (base / "code").mkdir(parents=True, exist_ok=True)

        docs = read_blobs(clone, spec.sha, [c.doc_path for c in spec.cases])
        for path, text in docs.items():
            (base / "doc" / _flat(path)).write_text(text, encoding="utf-8")

        pool = spec.cases[0].pool if spec.cases else ()
        for path, text in read_blobs(clone, spec.sha, list(pool)).items():
            (base / "code" / _flat(path)).write_text(text, encoding="utf-8")

    sheet = bundle / "SHEET.md"
    sheet.write_text(render_sheet(specs, bundle, seed), encoding="utf-8")
    return sheet


_CASE_RE = re.compile(r"^## Case (\d+) — `([^`]+)` · `([^`]+)`", re.MULTILINE)
_TICK_RE = re.compile(r"^- \[([ xX])\]\s+(\S+)\s*$")
_NONE_RE = re.compile(r"^\*\*NONE:\*\*\s*\[([ xX])\]")
_EXTRA_RE = re.compile(r"^\*\*EXTRA:\*\*\s*(.*)$")
_TREE_RE = re.compile(r"^- \*\*tree\*\* `([0-9a-f]+)`")


@dataclass
class SheetCase:
    repo: str
    doc_path: str
    sha_prefix: str
    marked: list[str]
    extra: list[str]
    none: bool

    @property
    def answered(self) -> bool:
        """Marks, an explicit NONE, or a freehand path. Anything else is a skip.

        The distinction is load-bearing: an unanswered case and a `NONE` case both
        have zero marked files, and treating a skip as "this doc is about nothing"
        would quietly add a query no ranker can win and drag every metric down.
        """
        return bool(self.marked) or bool(self.extra) or self.none


def parse_sheet(text: str) -> list[SheetCase]:
    """Read a filled sheet back. Tolerant of edits, strict about ambiguity."""
    cases: list[SheetCase] = []
    bounds = [(m.start(), m.group(2), m.group(3)) for m in _CASE_RE.finditer(text)]
    for index, (start, repo, doc_path) in enumerate(bounds):
        end = bounds[index + 1][0] if index + 1 < len(bounds) else len(text)
        block = text[start:end]
        marked: list[str] = []
        extra: list[str] = []
        none = False
        sha_prefix = ""
        for line in block.splitlines():
            tree = _TREE_RE.match(line)
            if tree:
                sha_prefix = tree.group(1)
                continue
            tick = _TICK_RE.match(line)
            if tick:
                if tick.group(1) in "xX":
                    marked.append(tick.group(2))
                continue
            nothing = _NONE_RE.match(line)
            if nothing:
                none = nothing.group(1) in "xX"
                continue
            more = _EXTRA_RE.match(line)
            if more:
                extra = [p.strip(" `,") for p in more.group(1).split() if p.strip(" `,")]
        cases.append(
            SheetCase(
                repo=repo,
                doc_path=doc_path,
                sha_prefix=sha_prefix,
                marked=marked,
                extra=extra,
                none=none,
            )
        )
    return cases


def splits_from_sheet(
    cases: list[SheetCase],
    clone_root: Path,
) -> tuple[list[RepoSplit], dict[str, int]]:
    """Turn answered cases into `RepoSplit`s the existing eval can score.

    Reuses `Query` and `RepoSplit` deliberately: the whole point is to run the same
    rankers, the same shuffled floor and the same macro-averaging over a different
    ground truth. A second scoring path would make the two corpora incomparable for
    reasons that had nothing to do with the corpora.

    `evidence` is empty on every query. There is no mining rule behind these labels,
    so there is nothing to ablate, and an ablated row would duplicate its unablated
    one.

    Scored against the tree **the sheet recorded**, resolved from the abbreviated sha
    in each case block, not against the clone's current HEAD. The two are the same
    until a clone is fetched, and after that they are quietly different: a judgement
    made about `src/flask/app.py` would be scored against a tree where that file has
    moved, capping recall for a reason no column of the output mentions. The same
    decision `dataset` makes for mined queries, for the same reason.
    """
    tally = {
        "cases": len(cases),
        "answered": 0,
        "none": 0,
        "skipped": 0,
        "unknown_paths": 0,
        "queries": 0,
        "unpinned": 0,
        "unresolved": 0,
    }
    by_repo: dict[str, list[SheetCase]] = {}
    for case in cases:
        if not case.answered:
            tally["skipped"] += 1
            continue
        tally["answered"] += 1
        if not case.marked and not case.extra:
            tally["none"] += 1
            continue
        by_repo.setdefault(case.repo, []).append(case)

    splits: list[RepoSplit] = []
    for repo in sorted(by_repo):
        clone = clone_root / local_name_for(repo)
        pools: dict[str, list[str]] = {}
        trees: dict[str, set[str]] = {}
        queries: list[Query] = []
        for case in by_repo[repo]:
            if case.sha_prefix:
                try:
                    sha = head_sha(clone, case.sha_prefix)
                except Exception:
                    # A mangled or garbage-collected tree line. The case is dropped
                    # and counted, not re-pointed at HEAD: scoring a judgement against
                    # a tree it was not made on is the exact failure the pinning is
                    # here to prevent, and doing it as *recovery* would be worse
                    # because nothing downstream would look wrong.
                    tally["unresolved"] += 1
                    continue
            else:
                # A case block whose `tree` line was edited away. Scored at HEAD and
                # counted, because an unpinned judgement is a weaker one and the
                # number of them belongs in the output rather than in a comment.
                sha = head_sha(clone)
                tally["unpinned"] += 1
            if sha not in pools:
                present = list_files(clone, sha)
                trees[sha] = set(present)
                pools[sha] = sorted(p for p in present if classify(p) is Kind.CODE)
            named = [*case.marked, *case.extra]
            keep = frozenset(p for p in named if p in trees[sha])
            tally["unknown_paths"] += len(named) - len(keep)
            if not keep:
                continue
            queries.append(
                Query(
                    repo=repo,
                    doc_path=case.doc_path,
                    at_sha=sha,
                    relevant=keep,
                    evidence=frozenset(),
                )
            )
        tally["queries"] += len(queries)
        splits.append(
            RepoSplit(
                repo=repo,
                clone=clone,
                queries=queries,
                pools=pools,
            )
        )
    return splits, tally
