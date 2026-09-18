"""Join hand-written verdicts to the mined records they were made on.

The review sheets carry Julie's judgement and almost nothing else -- a case id, a
verdict, and enough context for a person to answer. Everything needed to *rebuild*
the case for a judge (which tree to read, which document, which code file) lives in
the mined label files, joined by `example_id`. That join is the whole module.

Three things here are not obvious and each one is a way to get a wrong number:

**`new` is a negative.** See `FALSE_AT_PARENT`.

**A case can resolve from several label versions, and they are checked rather than
picked.** Mining is deterministic, so a case present in v3 and v5 should carry
identical fields; if it does not, something about the corpus moved and a silent
choice of version would bury it. Disagreements are counted and reported.

**A verdict with no record is dropped and counted, never dropped quietly.** This is
not hypothetical. 79 of the 125 verdicts join to records that live only in
`labels-v3` and `labels-v10`, both of which are *gitignored* as derived data. A clean
checkout of this repository therefore rebuilds 46 cases, not 125, and reports a
different class balance and a different floor with nothing raising -- it prints a
warning and then computes every number correctly against the wrong corpus.

`data/judged-records.jsonl` is the fix: the 125 records the hand labels actually join
to, frozen and tracked, written by `driftwood judge-freeze`. It is derived data that
gets versioned anyway, for the same reason `data/labels.jsonl` is -- it is what makes
irreplaceable hand labels attributable, and regenerable-in-principle is not the same
as present. When it exists it is the preferred source, so `resolved_from` is the same
on every machine; live label versions are still read, and a live version that
disagrees with the frozen record means the freeze is stale.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "FALSE_AT_PARENT",
    "FROZEN_NAME",
    "JudgeCase",
    "VERDICTS",
    "class_balance",
    "format_case_report",
    "freeze_records",
    "load_cases",
    "parse_verdicts",
]

VERDICTS = ("drift", "new", "cosmetic", "unrelated", "unclear")

# The tracked join table. Named here rather than passed in, because a caller free to
# point this somewhere else is a caller free to run the eval against a corpus nobody
# else has -- and the whole point of the file is that everyone has the same one.
FROZEN_NAME = "judged-records.jsonl"

# The prospective target, and the reason the five classes collapse to two.
#
# The sheets ask one question: "at the parent commit, was this documentation false
# about the code?" Only `drift` answers yes. The other three scoreable verdicts are
# different *reasons* the answer is no, and they are distinguishable only by looking
# at the correcting commit -- which the product never gets to do.
#
# `new` is the trap. Its legend text ("documenting something that did not exist
# yet") reads like a doc that ran ahead of its code, which would be a positive. The
# cases are not that: they are "Added support for signals" -- the feature and its
# documentation landing in one commit. At the parent neither existed, so nothing was
# false, and the miner proposing the pair at all is the false positive. Ten of the
# 105 scoreable cases turn on this.
#
# `unclear` maps to None rather than to a class. Julie could not tell *with both
# diffs in front of her*; a judge working from strictly less information has no
# defensible answer either, so these are held out as an abstention set instead of
# being scored against a verdict that does not exist.
FALSE_AT_PARENT: dict[str, bool | None] = {
    "drift": True,
    "new": False,
    "cosmetic": False,
    "unrelated": False,
    "unclear": None,
}

# Anchored at line start and requiring the bold form, so the legend at the top of
# every sheet -- which names all five verdicts in prose, and shows the unfilled
# `VERDICT: ?` placeholder -- cannot be read as a judgement.
#
# The id pattern is deliberately ANY backticked token rather than `[0-9a-f]+`, even
# though every real id is a hex digest. A stricter pattern makes an id format change
# silently unparseable: `parse_verdicts` would return an empty dict, the eval would
# report zero cases, and nothing would raise. Letting a bogus id through instead
# makes it fail loudly at the join, where it is counted as unresolvable.
_CASE_RE = re.compile(r"(?m)^## Case \d+ — `([^`]+)`")
_VERDICT_RE = re.compile(r"(?m)^\*\*VERDICT: `([a-z]+)`\*\*")

# Fields that must agree when a case resolves from more than one label version.
# `label` is excluded on purpose: it is the miner's own proposed verdict, it moved
# between versions as the filters changed, and it is not used here -- the ground
# truth is Julie's, and reading the miner's guess would be circular.
_MUST_AGREE = ("repo", "shape", "doc_path", "at_sha", "label_basis")


@dataclass(frozen=True)
class JudgeCase:
    """One hand-labelled case, rebuilt well enough to hand to a judge."""

    example_id: str
    repo: str
    shape: str
    basis: str
    doc_path: str
    code_path: str | None
    at_sha: str
    fix_sha: str
    subject: str
    shared_identifiers: tuple[str, ...]
    verdict: str
    sheet: str
    resolved_from: str

    @property
    def target(self) -> bool | None:
        """True if the doc was false about the code at `at_sha`; None if unclear."""
        return FALSE_AT_PARENT[self.verdict]

    @property
    def scoreable(self) -> bool:
        return self.target is not None


def parse_verdicts(text: str) -> dict[str, str]:
    """`{example_id: verdict}` for one review sheet.

    Splits on case headers before looking for verdicts, so a verdict can only ever
    bind to the case it appears under. Searching the whole document for verdict
    lines and zipping against case ids would produce a silent off-by-one the moment
    one case is left unlabelled -- and shifted labels are worse than missing ones,
    because every downstream number still computes.
    """
    out: dict[str, str] = {}
    parts = _CASE_RE.split(text)
    # parts[0] is the preamble; then (id, body) pairs.
    body_iter = iter(parts[1:])
    for example_id, body in zip(body_iter, body_iter):
        match = _VERDICT_RE.search(body)
        if match and match.group(1) in VERDICTS:
            out[example_id] = match.group(1)
    return out


def _index_label_files(data_dir: Path) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """`{example_id: {filename: record}}` over the frozen file and every label file.

    Every version is read rather than the newest, because the labelled cases were
    drawn from several: 79 of the 125 come from v10 and three from v3, both of which
    a later filter removed. Resolving against `labels.jsonl` alone returns 46.
    """
    index: dict[str, dict[str, dict]] = {}
    names: list[str] = []
    sources = sorted(data_dir.glob("labels*.jsonl"))
    frozen = data_dir / FROZEN_NAME
    if frozen.exists():
        sources.append(frozen)
    for path in sources:
        names.append(path.name)
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                index.setdefault(record["example_id"], {})[path.name] = record
    return index, names


def _verdicts_from_sheets(
    review_dir: Path,
) -> tuple[dict[str, tuple[str, str]], Counter]:
    """`{example_id: (verdict, sheet)}` across every sheet, plus a tally."""
    tally: Counter = Counter()
    verdicts: dict[str, tuple[str, str]] = {}
    for sheet in sorted(review_dir.glob("*.md")):
        found = parse_verdicts(sheet.read_text(encoding="utf-8"))
        tally["sheets"] += 1
        for example_id, verdict in found.items():
            if example_id in verdicts:
                # The same case judged in two sheets. Not currently the case, and
                # if it ever is, a second verdict is a re-label rather than a
                # duplicate row -- it needs deciding, not averaging.
                tally["duplicate_verdicts"] += 1
                continue
            verdicts[example_id] = (verdict, sheet.name)
    tally["verdicts"] = len(verdicts)
    return verdicts, tally


def load_cases(
    review_dir: Path, data_dir: Path
) -> tuple[list[JudgeCase], dict[str, int]]:
    """Every labelled case, plus a tally of what did not make it.

    The tally is returned rather than logged because each of its counts is a way the
    eval could be quietly wrong about its own denominator.
    """
    verdicts, tally = _verdicts_from_sheets(review_dir)

    index, _ = _index_label_files(data_dir)
    cases: list[JudgeCase] = []
    for example_id, (verdict, sheet_name) in sorted(verdicts.items()):
        found = index.get(example_id)
        if not found:
            tally["unresolvable"] += 1
            continue

        # The frozen file first, then the tracked v1 file, then ascending versions.
        # Frozen wins so that `resolved_from` is identical on a machine that still has
        # every mined version and on a clean checkout that has none of them --
        # otherwise the provenance block in the results JSON differs by machine, and
        # two people comparing results would be comparing their checkouts.
        if FROZEN_NAME in found:
            preferred = FROZEN_NAME
        elif "labels.jsonl" in found:
            preferred = "labels.jsonl"
        else:
            preferred = sorted(found)[0]
        record = found[preferred]

        if len(found) > 1:
            disagreed = [
                field
                for field in _MUST_AGREE
                if len({json.dumps(r.get(field)) for r in found.values()}) > 1
            ]
            if disagreed:
                tally["version_disagreements"] += 1

        cases.append(
            JudgeCase(
                example_id=example_id,
                repo=record["repo"],
                shape=record["shape"],
                basis=record["label_basis"],
                doc_path=record["doc_path"],
                code_path=record.get("code_path"),
                at_sha=record["at_sha"],
                fix_sha=record["fix_sha"],
                subject=record.get("subject", ""),
                shared_identifiers=tuple(record.get("shared_identifiers") or ()),
                verdict=verdict,
                sheet=sheet_name,
                resolved_from=preferred,
            )
        )
    tally["cases"] = len(cases)
    # How many cases a clean checkout could rebuild. Reported because the answer was
    # 46 of 125 before the frozen file existed, and the only symptom was a warning
    # nobody had a reason to read: every other number computed fine, against a corpus
    # two thirds smaller than the one the pre-registration describes.
    tally["from_frozen"] = sum(1 for c in cases if c.resolved_from == FROZEN_NAME)
    tally["from_ignored_versions"] = sum(
        1
        for c in cases
        if c.resolved_from not in (FROZEN_NAME, "labels.jsonl")
    )
    tally["scoreable"] = sum(1 for c in cases if c.scoreable)
    tally["held_out_unclear"] = sum(1 for c in cases if c.verdict == "unclear")
    tally["with_code_path"] = sum(1 for c in cases if c.code_path)
    return cases, dict(tally)


def freeze_records(review_dir: Path, data_dir: Path, out: Path) -> tuple[int, int]:
    """Write the records the hand labels join to, as a tracked file.

    Returns `(written, unresolvable)`. Run on a machine that still has the mined
    versions; the output is what a clean checkout resolves against.

    Each record keeps a `frozen_from` naming the file it came from, so the freeze
    does not erase which mining run produced a case -- that is the field that would
    be needed to explain a case, and it is the one a naive concatenation drops.
    """
    verdicts = _verdicts_from_sheets(review_dir)[0]
    index, _ = _index_label_files(data_dir)
    written = 0
    unresolvable = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for example_id in sorted(verdicts):
            found = index.get(example_id)
            if not found:
                unresolvable += 1
                continue
            source = (
                "labels.jsonl" if "labels.jsonl" in found
                else next(n for n in sorted(found) if n != FROZEN_NAME)
                if any(n != FROZEN_NAME for n in found)
                else FROZEN_NAME
            )
            record = dict(found[source])
            record["frozen_from"] = record.get("frozen_from", source)
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            written += 1
    return written, unresolvable


def class_balance(cases: list[JudgeCase]) -> dict[str, float | int]:
    """The floors, computed from the labels rather than assumed.

    `majority_accuracy` is the number a constant "not false" predictor scores, and
    it is the bar. At a positive rate near 28% it sits above 70%, so accuracy alone
    cannot distinguish a working judge from a broken one -- which is why the primary
    metric is F1 on the positive class, where that same constant scores 0.00.
    """
    scoreable = [c for c in cases if c.scoreable]
    positives = sum(1 for c in scoreable if c.target)
    total = len(scoreable)
    negatives = total - positives
    return {
        "scoreable": total,
        "positive": positives,
        "negative": negatives,
        "positive_rate": positives / total if total else 0.0,
        "majority_accuracy": max(positives, negatives) / total if total else 0.0,
        "majority_class": "not-false" if negatives >= positives else "false",
        "held_out_unclear": sum(1 for c in cases if c.verdict == "unclear"),
    }


def format_case_report(cases: list[JudgeCase], tally: dict[str, int]) -> str:
    """What the eval is about to be run on, before it is run."""
    balance = class_balance(cases)
    lines = [
        f"{tally['verdicts']} verdicts in {tally['sheets']} sheets -> "
        f"{tally['cases']} cases rebuilt"
    ]
    if tally.get("unresolvable"):
        lines.append(
            f"  WARNING: {tally['unresolvable']} verdict(s) match no mined record in "
            "any label version and were dropped"
        )
    if tally.get("version_disagreements"):
        lines.append(
            f"  WARNING: {tally['version_disagreements']} case(s) differ between the "
            "label versions that contain them -- the corpus moved under a judgement"
        )
    if tally.get("duplicate_verdicts"):
        lines.append(
            f"  WARNING: {tally['duplicate_verdicts']} case(s) judged in two sheets; "
            "the later sheet was ignored rather than merged"
        )
    if tally.get("from_ignored_versions"):
        lines.append(
            f"  WARNING: {tally['from_ignored_versions']} case(s) resolved only from a "
            f"gitignored label version -- run `driftwood judge-freeze` so a clean "
            "checkout rebuilds the same corpus"
        )
    lines.append("")

    counts = Counter(c.verdict for c in cases)
    lines.append(f"{'verdict':<12}{'n':>5}  target")
    for verdict in VERDICTS:
        target = FALSE_AT_PARENT[verdict]
        shown = "held out" if target is None else ("FALSE-AT-PARENT" if target else "not false")
        lines.append(f"{verdict:<12}{counts.get(verdict, 0):>5}  {shown}")
    lines.append("")
    lines.append(
        f"scoreable {balance['scoreable']}  positive {balance['positive']} "
        f"({balance['positive_rate']:.1%})  negative {balance['negative']}  "
        f"held out {balance['held_out_unclear']}"
    )
    lines.append(
        f"majority-class floor: {balance['majority_accuracy']:.1%} accuracy by always "
        f"answering \"{balance['majority_class']}\", at F1 0.00"
    )
    lines.append("")

    by_shape = Counter(c.shape for c in cases)
    with_code = tally.get("with_code_path", 0)
    lines.append(f"{'shape':<8}{'n':>5}{'code_path':>11}")
    for shape in sorted(by_shape):
        n_code = sum(1 for c in cases if c.shape == shape and c.code_path)
        lines.append(f"{shape:<8}{by_shape[shape]:>5}{n_code:>11}")
    lines.append(
        f"{with_code} of {len(cases)} cases carry a code file. Shape B is doc-only "
        "commits, so for"
    )
    lines.append(
        "those the code side must be RETRIEVED -- stage 2 is load-bearing here, not "
        "an add-on."
    )
    return "\n".join(lines)
