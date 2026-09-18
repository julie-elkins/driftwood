"""Score hand-labelled review sheets against the miner's output.

Reads the `VERDICT:` lines a human wrote back into a review sheet and reports
precision per shape and per `label_basis`.

Every proportion here comes with a 95% Wilson interval, and that is not decoration.
6 of 20 reads as "30%", but its interval runs from roughly 15% to 52% -- a
twenty-case sample cannot tell 30% from 45%. Printing the point estimate alone is
how you end up believing a threshold change helped when it did nothing. When the
numerator is zero the interval is one-sided and reported as an upper bound.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Verdict",
    "format_report",
    "format_retention",
    "parse_sheet",
    "retention",
    "score",
    "wilson",
]

# `## Case 3 — \`a90fb09268690fe3\`` -- the id is what joins back to the label file.
_CASE_RE = re.compile(r"^##\s+Case\s+\d+\s+—\s+`([0-9a-f]+)`", re.MULTILINE)
# Accepts `drift`, drift, **drift** -- a human edited this file by hand and the
# parser should not be the reason a labelling session has to be redone.
_VERDICT_RE = re.compile(r"^\*\*VERDICT:\s*`?\*?\*?([A-Za-z?]+)\*?\*?`?\*\*", re.MULTILINE)

VALID_VERDICTS = frozenset({"drift", "new", "cosmetic", "unrelated", "unclear"})

# Only `drift` counts as the miner having been right. `unclear` is deliberately
# counted as a miss rather than dropped: a case a competent reviewer cannot
# adjudicate from the evidence the miner surfaced is a case the miner should not
# have surfaced.
POSITIVE_VERDICT = "drift"


@dataclass(frozen=True)
class Verdict:
    example_id: str
    verdict: str


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Stdlib only, on purpose."""
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    spread = (
        z / denominator * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    )
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def parse_sheet(path: Path) -> list[Verdict]:
    """Pull (example_id, verdict) pairs out of a hand-edited review sheet.

    Pairs positionally: the Nth case heading goes with the Nth verdict. Raises if
    the counts disagree, because a silent off-by-one here would misattribute every
    label after the first missing one -- the sort of error that produces a
    plausible number and no symptom.
    """
    text = path.read_text(encoding="utf-8")
    ids = _CASE_RE.findall(text)
    # The instruction block at the top contains the literal `VERDICT: ?` template.
    verdicts = [v.lower() for v in _VERDICT_RE.findall(text)]

    if len(ids) != len(verdicts):
        raise ValueError(
            f"{path}: {len(ids)} case headings but {len(verdicts)} verdict lines. "
            "A heading or a VERDICT line was edited away."
        )
    return [Verdict(case_id, verdict) for case_id, verdict in zip(ids, verdicts)]


def score(labels_path: Path, sheets: list[Path]) -> dict:
    by_id = {}
    with labels_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                by_id[row["example_id"]] = row

    verdicts: list[Verdict] = []
    for sheet in sheets:
        verdicts.extend(parse_sheet(sheet))

    unlabelled = [v.example_id for v in verdicts if v.verdict not in VALID_VERDICTS]
    unknown = [v.example_id for v in verdicts if v.example_id not in by_id]

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    overall: list[str] = []
    for verdict in verdicts:
        if verdict.verdict not in VALID_VERDICTS or verdict.example_id not in by_id:
            continue
        row = by_id[verdict.example_id]
        groups[("shape", row["shape"])].append(verdict.verdict)
        groups[("basis", row["label_basis"])].append(verdict.verdict)
        overall.append(verdict.verdict)

    def summarise(values: list[str]) -> dict:
        total = len(values)
        hits = sum(1 for value in values if value == POSITIVE_VERDICT)
        low, high = wilson(hits, total)
        result = {
            "n": total,
            "drift": hits,
            "precision": round(hits / total, 4) if total else None,
            "ci95": [round(low, 4), round(high, 4)],
            "verdicts": dict(Counter(values).most_common()),
        }
        if hits == 0 and total:
            # Rule of three: with no successes, the 95% upper bound is ~3/n.
            result["upper_bound_95"] = round(1 - 0.05 ** (1 / total), 4)
        return result

    return {
        "labels_file": str(labels_path),
        "sheets": [str(sheet) for sheet in sheets],
        "reviewed": len(verdicts),
        "skipped_unlabelled": unlabelled,
        "skipped_not_in_label_file": unknown,
        "overall": summarise(overall),
        "by_shape": {
            key[1]: summarise(values) for key, values in sorted(groups.items()) if key[0] == "shape"
        },
        "by_basis": {
            key[1]: summarise(values) for key, values in sorted(groups.items()) if key[0] == "basis"
        },
    }


def retention(old_labels: Path, new_labels: Path, sheets: list[Path]) -> dict:
    """How a rebuilt label set treats cases a human has already judged.

    Valid without relabelling for *subtractive* changes only -- a rule that can
    only remove candidates. For each verdict class it reports how many survived;
    we want `drift` kept and everything else dropped. It says nothing about cases
    the new rules newly admit, so a fresh sample and fresh labels are still
    required before quoting a new precision figure.

    This works at all only because `example_id` is a stable hash of the pair's
    identity rather than a row number.
    """

    def ids(path: Path) -> dict[str, dict]:
        out = {}
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    out[row["example_id"]] = row
        return out

    before, after = ids(old_labels), ids(new_labels)
    verdicts = [v for sheet in sheets for v in parse_sheet(sheet)]

    kept: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    retained_verdicts: list[str] = []
    # A verdict whose case is absent from the *old* file cannot be scored, and the
    # reason is usually not the rules: a different --limit or repo list moves the
    # commit window, so the case was never a candidate in either file. Counting
    # these is not bookkeeping. Silently omitting them shrinks the denominator
    # while the precision figure still looks like it came from 20 cases.
    not_in_old: list[str] = []
    # Per shape as well as blended. A rule that touches one arm of the corpus and
    # not the other moves the blended number in whichever direction the untouched
    # arm dominates -- which can be the opposite direction to the actual effect.
    # Reporting only the aggregate here would hide exactly what the tool is for.
    per_shape: dict[str, dict[str, Counter]] = defaultdict(
        lambda: {"kept": Counter(), "dropped": Counter()}
    )
    lost_positives: list[dict] = []

    for verdict in verdicts:
        if verdict.verdict not in VALID_VERDICTS:
            continue
        if verdict.example_id not in before:
            not_in_old.append(verdict.example_id)
            continue
        row = before[verdict.example_id]
        shape = row["shape"]
        if verdict.example_id in after:
            kept[verdict.verdict] += 1
            per_shape[shape]["kept"][verdict.verdict] += 1
            retained_verdicts.append(verdict.verdict)
        else:
            dropped[verdict.verdict] += 1
            per_shape[shape]["dropped"][verdict.verdict] += 1
            if verdict.verdict == POSITIVE_VERDICT:
                # True positives the rule threw away. The most useful output here:
                # these are the cases to read before tightening anything further.
                lost_positives.append(
                    {
                        "example_id": verdict.example_id,
                        "repo": row["repo"],
                        "shape": shape,
                        "doc_path": row["doc_path"],
                        "code_path": row["code_path"],
                        "fix_sha": row["fix_sha"],
                        "parent_sha": row["parent_sha"],
                        "subject": row["subject"],
                        "shared_identifiers": row["shared_identifiers"],
                    }
                )

    def summarise(kept_counter: Counter, dropped_counter: Counter) -> dict:
        total = sum(kept_counter.values())
        hits = kept_counter.get(POSITIVE_VERDICT, 0)
        positives_before = hits + dropped_counter.get(POSITIVE_VERDICT, 0)
        low, high = wilson(hits, total)
        return {
            "kept": dict(kept_counter.most_common()),
            "dropped": dict(dropped_counter.most_common()),
            "retained_n": total,
            "retained_drift": hits,
            "precision": round(hits / total, 4) if total else None,
            "ci95": [round(low, 4), round(high, 4)],
            "positives_kept": f"{hits}/{positives_before}" if positives_before else None,
        }

    return {
        "old_labels": str(old_labels),
        "new_labels": str(new_labels),
        "corpus_size": {"before": len(before), "after": len(after)},
        "verdicts_read": len(verdicts),
        "verdicts_scored": len(verdicts) - len(not_in_old),
        "not_in_old_labels": not_in_old,
        "blended": summarise(kept, dropped),
        "by_shape": {
            shape: summarise(counters["kept"], counters["dropped"])
            for shape, counters in sorted(per_shape.items())
        },
        "lost_positives": lost_positives,
    }


def format_retention(result: dict) -> str:
    lines = [
        f"corpus: {result['corpus_size']['before']} -> {result['corpus_size']['after']} examples",
        f"verdicts: {result['verdicts_scored']} of {result['verdicts_read']} scorable",
    ]
    if result["not_in_old_labels"]:
        lines.append(
            f"  !! {len(result['not_in_old_labels'])} judged case(s) absent from the OLD "
            "label file, so unscorable here. Usually because the OLD file already "
            "excluded them -- chaining v2->v3 hides what v1->v2 did. Compare against "
            "the file the labels were drawn from to see those."
        )
    lines.append("")

    def block(title: str, summary: dict) -> None:
        lines.append(title)
        classes = sorted(set(summary["kept"]) | set(summary["dropped"]))
        for name in classes:
            kept = summary["kept"].get(name, 0)
            dropped = summary["dropped"].get(name, 0)
            want = "KEEP" if name == POSITIVE_VERDICT else "drop"
            lines.append(
                f"    {name:<10} kept {kept:>3}   dropped {dropped:>3}   (want: {want})"
            )
        if summary["precision"] is None:
            lines.append("    nothing retained")
        else:
            low, high = summary["ci95"]
            lines.append(
                f"    precision on retained: {summary['retained_drift']}/"
                f"{summary['retained_n']} = {summary['precision']:.0%}"
                f"   95% CI [{low:.0%}, {high:.0%}]"
            )
            if summary["positives_kept"]:
                lines.append(f"    true positives kept: {summary['positives_kept']}")
        lines.append("")

    for shape, summary in result["by_shape"].items():
        block(f"  shape {shape}", summary)
    block("  BLENDED (read the per-shape numbers first)", result["blended"])

    if result["lost_positives"]:
        lines.append(f"  true positives thrown away ({len(result['lost_positives'])}):")
        for lost in result["lost_positives"]:
            shared = ", ".join(lost["shared_identifiers"][:6]) or "(none recorded)"
            lines.append(f"    {lost['example_id']}  {lost['doc_path']} <- {lost['code_path']}")
            lines.append(f"      subject: {lost['subject']}")
            lines.append(f"      had shared: {shared}")
    lines.append("")
    lines.append("  (this sample only -- says nothing about cases the new rules newly admit)")
    return "\n".join(lines)


def format_report(result: dict) -> str:
    lines = [f"reviewed {result['reviewed']} cases from {len(result['sheets'])} sheet(s)"]
    if result["skipped_unlabelled"]:
        lines.append(f"  !! {len(result['skipped_unlabelled'])} case(s) still unlabelled")
    if result["skipped_not_in_label_file"]:
        lines.append(
            f"  !! {len(result['skipped_not_in_label_file'])} case(s) not found in label file"
        )
    lines.append("")

    def block(title: str, summary: dict) -> None:
        low, high = summary["ci95"]
        if summary["precision"] is None:
            lines.append(f"{title}: no cases")
            return
        headline = f"{summary['drift']}/{summary['n']} = {summary['precision']:.0%}"
        interval = f"95% CI [{low:.0%}, {high:.0%}]"
        if "upper_bound_95" in summary:
            interval = f"95% upper bound {summary['upper_bound_95']:.0%}"
        lines.append(f"{title}: {headline}   {interval}")
        breakdown = "  ".join(f"{k}={v}" for k, v in summary["verdicts"].items())
        lines.append(f"    {breakdown}")

    block("OVERALL", result["overall"])
    lines.append("")
    lines.append("by shape")
    for name, summary in result["by_shape"].items():
        block(f"  shape {name}", summary)
    lines.append("")
    lines.append("by label_basis")
    for name, summary in result["by_basis"].items():
        block(f"  {name}", summary)
    return "\n".join(lines)
