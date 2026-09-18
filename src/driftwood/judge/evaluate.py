"""Score judgements against Julie's verdicts, against floors, and against noise.

The headline is F1 on the positive class, not accuracy. At a 28.6% positive rate a
constant "not false" scores 71.4% accuracy, so accuracy near 70% is consistent with a
judge that has learned nothing; F1 for that same constant is 0.00. Accuracy is still
reported, because a judge can buy F1 by flagging everything -- `always-false` scores
F1 0.44 -- and the pair of numbers is what separates the two failure modes.

Three things are deliberately awkward here, each because the comfortable version
would overstate:

**Abstentions are reported two ways and folded into neither.** `accuracy_answered`
divides by the cases a judge actually answered; `accuracy_all` counts an abstention
as wrong. A judge can reach perfect precision by abstaining on everything, so a
precision quoted without its abstention rate is not a result. Both appear on every
row.

**The noise range comes from trials, not from a formula.** `PriorJudge` is run
`NULL_TRIALS` times at the corpus positive rate and the spread of its F1 and accuracy
is reported. Stage 2's lesson was that gaps look large until the control is drawn on
the same axis: every headline retrieval gap there sat inside its noise range. A gap
smaller than this spread has not been shown.

**Per-repo and per-shape cells are printed with their n, and small cells are marked.**
105 cases across several repos means some cells hold single digits, where an F1 swings
by a third on one case. They are shown rather than pooled away, and shown as too small
to read rather than quietly averaged into something that looks stable.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from .cases import JudgeCase, class_balance
from .judge import Judgement, PriorJudge

__all__ = [
    "CHARS_PER_TOKEN",
    "MIN_CELL",
    "NULL_TRIALS",
    "Scores",
    "confusion",
    "estimate_spend",
    "format_results",
    "format_spend",
    "measured_spend",
    "noise_range",
    "score",
    "to_json",
]

# Matches stage 2's control-arm trial count, so the two stages' noise ranges are
# built the same way and can be described in one sentence in the README.
NULL_TRIALS = 200

# Below this many scoreable cases a cell's F1 is reported but marked unreadable. Ten
# is not principled; it is the point at which one case moves F1 by more than the
# largest effect stage 3 is looking for.
MIN_CELL = 10

# Characters per token, for estimating a run's size before paying for it. A heuristic
# and labelled as one everywhere it surfaces: the true count depends on a tokeniser
# this package does not ship, and these prompts are source code and reStructuredText
# rather than English, which tokenises worse than the usual 4.0 rule of thumb.
#
# The estimate is deliberately reported in TOKENS and not in dollars. A price is a
# claim about the world that goes stale silently and would sit in this file being wrong
# -- which is the failure mode the whole project is about, so hardcoding a rate here
# would be embarrassing. Token counts are a measurement of the prompts on disk.
CHARS_PER_TOKEN = 3.6


def estimate_spend(
    rendered: list[str], *, system: str, max_tokens: int
) -> dict[str, int | float]:
    """What an arm will cost, in tokens, from the prompts actually built.

    Measured from the rendered strings rather than from the case count, because the
    two differ by 20x here: a doc at the character budget is a 45,000-character prompt
    and a one-line README is not.

    `system` is required rather than defaulting to empty, and that is the whole reason
    it is keyword-only. The first version of this function omitted it and under-read
    the oracle arm by 11% -- the system prompt is 1,395 characters resent on every one
    of the 45 calls. An estimate wrong in the cheap-looking direction is worse than no
    estimate, so the signature refuses to let a caller forget it.

    `output_tokens_high` is `max_tokens` per case -- an upper bound, not a guess.
    Replies are a few hundred tokens of JSON in practice, so a run that approaches this
    bound is one where the model is not answering in the requested shape.
    """
    per_call_overhead = len(system)
    chars = sum(len(text) + per_call_overhead for text in rendered)
    return {
        "calls": len(rendered),
        "input_chars": chars,
        "system_chars_per_call": per_call_overhead,
        "input_tokens_approx": round(chars / CHARS_PER_TOKEN),
        "output_tokens_high": len(rendered) * max_tokens,
        "longest_prompt_chars": max((len(t) + per_call_overhead for t in rendered), default=0),
    }


def measured_spend(judgements: dict[str, Judgement]) -> dict[str, int]:
    """What the provider said it billed, summed over the judgements that know.

    `unknown` counts judgements with no usage attached -- free judges, and replies
    cached before usage was recorded. Reported rather than folded into zero, because a
    zero would make a fully cached run look free instead of looking unmeasured.
    """
    known = [j for j in judgements.values() if j.input_tokens is not None]
    return {
        "calls_measured": len(known),
        "unknown": len(judgements) - len(known),
        "input_tokens": sum(j.input_tokens or 0 for j in known),
        "output_tokens": sum(j.output_tokens or 0 for j in known),
        "cached": sum(1 for j in judgements.values() if j.cached),
    }


def format_spend(
    estimate: dict[str, int | float], measured: dict[str, int] | None = None
) -> str:
    """The estimate, and -- once a run has happened -- how wrong it was."""
    lines = [
        f"{estimate['calls']} call(s) at most: ~{estimate['input_tokens_approx']:,} input "
        f"tokens (approx, {CHARS_PER_TOKEN} chars/token over "
        f"{estimate['input_chars']:,} characters, including the "
        f"{estimate['system_chars_per_call']:,}-character system prompt resent every call),",
        f"  up to {estimate['output_tokens_high']:,} output tokens; longest single "
        f"prompt {estimate['longest_prompt_chars']:,} characters.",
        "  Reported in tokens, not dollars: a hardcoded price is exactly the kind of "
        "stale claim this tool looks for.",
    ]
    if not measured or not measured["calls_measured"]:
        return "\n".join(lines)

    actual = measured["input_tokens"]
    approx = estimate["input_tokens_approx"]
    lines.append(
        f"  billed: {actual:,} input + {measured['output_tokens']:,} output tokens over "
        f"{measured['calls_measured']} call(s)"
        + (f", {measured['unknown']} with no usage recorded" if measured["unknown"] else "")
        + (f", {measured['cached']} served from cache" if measured["cached"] else "")
    )
    if approx:
        # The estimate checked against the outcome. An estimate nobody ever compares to
        # the bill is not an estimate, it is a reassurance.
        lines.append(
            f"  the {CHARS_PER_TOKEN} chars/token heuristic was off by "
            f"{(approx - actual) / actual:+.1%} on this arm"
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class Scores:
    n: int  # scoreable cases in this cell
    answered: int
    abstained: int
    unparsed: int
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        got = self.tp + self.fp
        return self.tp / got if got else 0.0

    @property
    def recall(self) -> float:
        real = self.tp + self.fn
        return self.tp / real if real else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy_answered(self) -> float:
        """Over the cases the judge answered. Flattering, and labelled as such."""
        return (self.tp + self.tn) / self.answered if self.answered else 0.0

    @property
    def accuracy_all(self) -> float:
        """Abstention counted as wrong. The number that cannot be gamed by silence."""
        return (self.tp + self.tn) / self.n if self.n else 0.0

    @property
    def abstention_rate(self) -> float:
        return self.abstained / self.n if self.n else 0.0

    @property
    def readable(self) -> bool:
        return self.n >= MIN_CELL


def score(cases: list[JudgeCase], judgements: dict[str, Judgement]) -> Scores:
    """Confusion counts over the scoreable cases a judgement exists for.

    A case with no judgement is skipped and does not enter `n`. That is the right
    denominator for "how good is this judge on what it saw", and it is the wrong one
    for "how good is this judge", which is why the case report prints the corpus size
    separately and the results JSON records both.
    """
    tp = fp = fn = tn = answered = abstained = unparsed = 0
    n = 0
    for case in cases:
        if not case.scoreable:
            continue
        found = judgements.get(case.example_id)
        if found is None:
            continue
        n += 1
        if found.unparsed:
            unparsed += 1
        if found.answer is None:
            abstained += 1
            continue
        answered += 1
        if found.answer and case.target:
            tp += 1
        elif found.answer and not case.target:
            fp += 1
        elif not found.answer and case.target:
            fn += 1
        else:
            tn += 1
    return Scores(
        n=n, answered=answered, abstained=abstained, unparsed=unparsed,
        tp=tp, fp=fp, fn=fn, tn=tn,
    )


def confusion(
    cases: list[JudgeCase], judgements: dict[str, Judgement]
) -> dict[str, Counter]:
    """What the judge answered, broken out by the verdict Julie actually wrote.

    The five-class view the binary target collapses, put back for diagnosis only. It
    is where a systematic error shows up as a pattern rather than a rate: if the false
    positives are nearly all `new`, the judge is flagging features that arrived with
    their documentation, which is a fixable prompt problem. If they are spread evenly
    across `cosmetic` and `unrelated`, it is not.
    """
    out: dict[str, Counter] = defaultdict(Counter)
    for case in cases:
        found = judgements.get(case.example_id)
        if found is None:
            continue
        said = "abstain" if found.answer is None else ("false" if found.answer else "not-false")
        out[case.verdict][said] += 1
    return dict(out)


def noise_range(
    cases: list[JudgeCase],
    contexts_available: set[str],
    *,
    trials: int = NULL_TRIALS,
    rate: float | None = None,
) -> dict[str, tuple[float, float, float]]:
    """(p5, median, p95) for F1, accuracy and precision under chance answering.

    `rate` defaults to the corpus positive rate, which is the strongest form of the
    control: a coin weighted to the true base rate is the best a judge can do knowing
    the distribution and nothing about any individual case. A 50/50 coin would be a
    weaker control and would make every real number look better.
    """
    scoreable = [c for c in cases if c.scoreable and c.example_id in contexts_available]
    if rate is None:
        rate = class_balance(scoreable)["positive_rate"]

    collected: dict[str, list[float]] = {"f1": [], "accuracy_all": [], "precision": []}
    for trial in range(trials):
        judge = PriorJudge(rate=float(rate), seed=trial)
        drawn = {
            case.example_id: judge.judge(
                # A bare stand-in: PriorJudge reads only `example_id` and `arm`, and
                # building 200 x 105 real contexts to feed a coin flip would make the
                # control cost more than the arm it is controlling.
                _IdOnly(case.example_id)  # type: ignore[arg-type]
            )
            for case in scoreable
        }
        got = score(scoreable, drawn)
        collected["f1"].append(got.f1)
        collected["accuracy_all"].append(got.accuracy_all)
        collected["precision"].append(got.precision)

    out: dict[str, tuple[float, float, float]] = {}
    for metric, values in collected.items():
        values.sort()
        if not values:
            out[metric] = (0.0, 0.0, 0.0)
            continue
        low = values[int(0.05 * (len(values) - 1))]
        mid = values[len(values) // 2]
        high = values[int(0.95 * (len(values) - 1))]
        out[metric] = (low, mid, high)
    return out


@dataclass(frozen=True)
class _IdOnly:
    """The two fields `PriorJudge` and `AlwaysJudge` read, and nothing else."""

    example_id: str
    arm: str = "control"


def _cells(
    cases: list[JudgeCase], judgements: dict[str, Judgement], key
) -> dict[str, Scores]:
    grouped: dict[str, list[JudgeCase]] = defaultdict(list)
    for case in cases:
        grouped[key(case)].append(case)
    return {name: score(group, judgements) for name, group in sorted(grouped.items())}


def abstention_calibration(
    cases: list[JudgeCase], judgements: dict[str, Judgement]
) -> dict[str, float | int]:
    """Does the judge abstain where Julie could not tell?

    The 20 `unclear` cases are the only ones with no defensible answer -- she had both
    diffs and still could not decide, and a judge has strictly less. So the test is
    not "does it abstain often" but "does it abstain *differentially*": an abstention
    rate that is the same on the 20 as on the 105 carries no information, however high
    it is. `lift` is the ratio, and 1.0 means the abstentions are noise.
    """
    held = [c for c in cases if c.verdict == "unclear" and c.example_id in judgements]
    scoreable = [c for c in cases if c.scoreable and c.example_id in judgements]
    on_held = sum(1 for c in held if judgements[c.example_id].answer is None)
    on_scoreable = sum(1 for c in scoreable if judgements[c.example_id].answer is None)
    held_rate = on_held / len(held) if held else 0.0
    scoreable_rate = on_scoreable / len(scoreable) if scoreable else 0.0
    return {
        "held_out": len(held),
        "abstained_on_held_out": on_held,
        "held_out_rate": held_rate,
        "scoreable_rate": scoreable_rate,
        "lift": held_rate / scoreable_rate if scoreable_rate else 0.0,
    }


def _row(name: str, s: Scores) -> str:
    mark = "" if s.readable else "  (n<%d: not readable)" % MIN_CELL
    return (
        f"{name:<26}{s.n:>5}{s.f1:>8.2f}{s.precision:>7.2f}{s.recall:>7.2f}"
        f"{s.accuracy_all:>8.1%}{s.accuracy_answered:>8.1%}{s.abstention_rate:>7.1%}{mark}"
    )


_HEADER = (
    f"{'':<26}{'n':>5}{'F1':>8}{'prec':>7}{'rec':>7}{'acc':>8}{'acc|ans':>8}{'abst':>7}"
)


def format_results(
    cases: list[JudgeCase],
    by_judge: dict[str, dict[str, Judgement]],
    *,
    arm: str,
    noise: dict[str, tuple[float, float, float]] | None = None,
) -> str:
    """The whole result for one arm, with the floors on the same axis as the judges."""
    # Over every case, not just the scoreable ones: `class_balance` counts the held-out
    # `unclear` cases itself, and pre-filtering them out made the header report "0 held
    # out" on a corpus with 20 of them -- which read as though the abstention
    # calibration had nothing to calibrate against.
    balance = class_balance(cases)
    lines = [
        f"ARM: {arm}",
        f"{balance['scoreable']} scoreable cases, {balance['positive']} positive "
        f"({balance['positive_rate']:.1%}), {balance['held_out_unclear']} held out as "
        "unclear",
        "",
        "PRIMARY METRIC is F1 on the positive class. acc = abstention counted wrong;",
        "acc|ans = over answered cases only, which a judge can inflate by abstaining.",
        "",
        _HEADER,
    ]
    for name in sorted(by_judge):
        lines.append(_row(name, score(cases, by_judge[name])))

    if noise:
        lines.append("")
        lines.append("CHANCE RANGE (coin weighted to the corpus positive rate, "
                     f"{NULL_TRIALS} trials, p5-p95):")
        for metric in ("f1", "accuracy_all", "precision"):
            low, mid, high = noise[metric]
            lines.append(f"  {metric:<14}{low:.2f} .. {high:.2f}   (median {mid:.2f})")
        lines.append(
            "  A judge-to-floor gap narrower than this spread has not been shown."
        )

    for name in sorted(by_judge):
        judgements = by_judge[name]
        lines.append("")
        lines.append(f"--- {name} ---")

        got = score(cases, judgements)
        if got.unparsed:
            lines.append(
                f"  WARNING: {got.unparsed} reply/replies could not be parsed as a "
                "verdict; each was scored as an abstention, not as not-false"
            )

        matrix = confusion(cases, judgements)
        lines.append(f"  {'Julie said':<12}{'-> false':>10}{'not-false':>11}{'abstain':>9}")
        for verdict in ("drift", "new", "cosmetic", "unrelated", "unclear"):
            row = matrix.get(verdict)
            if not row:
                continue
            note = "  <- the positives" if verdict == "drift" else (
                "  <- held out, not scored" if verdict == "unclear" else ""
            )
            lines.append(
                f"  {verdict:<12}{row['false']:>10}{row['not-false']:>11}"
                f"{row['abstain']:>9}{note}"
            )

        calibration = abstention_calibration(cases, judgements)
        if calibration["held_out"]:
            if not calibration["held_out_rate"] and not calibration["scoreable_rate"]:
                # A lift of 0.00x printed here read as a catastrophic calibration
                # failure when the truth is that the judge never abstains at all, so
                # there is nothing to calibrate. Different fact, different sentence.
                lines.append(
                    f"  never abstained, on the {calibration['held_out']} unclear cases "
                    "or anywhere else -- abstention is uncalibrated rather than poorly "
                    "calibrated"
                )
            else:
                lines.append(
                    f"  abstention on the {calibration['held_out']} unclear cases: "
                    f"{calibration['held_out_rate']:.1%} vs "
                    f"{calibration['scoreable_rate']:.1%} on scoreable ones -- lift "
                    f"{calibration['lift']:.2f}x"
                    + ("  (1.0x = the abstentions carry no information)"
                       if abs(calibration["lift"] - 1.0) < 0.15 else "")
                )

        for label, key in (("shape", lambda c: c.shape), ("repo", lambda c: c.repo)):
            cells = _cells(cases, judgements, key)
            if len(cells) < 2:
                continue
            lines.append(f"  by {label}:")
            for cell_name, cell in cells.items():
                lines.append("  " + _row(f"  {cell_name}", cell))
    return "\n".join(lines)


def to_json(
    cases: list[JudgeCase],
    by_arm: dict[str, dict[str, dict[str, Judgement]]],
    *,
    tally: dict[str, int],
    noise: dict[str, dict[str, tuple[float, float, float]]],
    extra: dict | None = None,
) -> dict:
    """Machine-readable results, provenance first.

    The provenance block is not decoration. A stage-3 number is only interpretable
    against which label versions resolved the cases and how many were dropped, and
    those are exactly the fields that stop being obvious once the file is a month old.
    """
    balance = class_balance([c for c in cases if c.scoreable])
    out: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provenance": {
            "corpus": dict(tally),
            "balance": balance,
            "primary_metric": "f1_positive_class",
            "majority_class_floor_accuracy": balance["majority_accuracy"],
            "null_trials": NULL_TRIALS,
            "min_readable_cell": MIN_CELL,
        },
        "arms": {},
    }
    if extra:
        out["provenance"].update(extra)
    for arm, judges in sorted(by_arm.items()):
        out["arms"][arm] = {
            "noise_range": {k: list(v) for k, v in noise.get(arm, {}).items()},
            "judges": {},
        }
        for name, judgements in sorted(judges.items()):
            got = score(cases, judgements)
            out["arms"][arm]["judges"][name] = {
                "n": got.n,
                "f1": got.f1,
                "precision": got.precision,
                "recall": got.recall,
                "accuracy_all": got.accuracy_all,
                "accuracy_answered": got.accuracy_answered,
                "abstained": got.abstained,
                "unparsed": got.unparsed,
                "confusion": {"tp": got.tp, "fp": got.fp, "fn": got.fn, "tn": got.tn},
                "by_verdict": {
                    k: dict(v) for k, v in confusion(cases, judgements).items()
                },
                "abstention_calibration": abstention_calibration(cases, judgements),
                "by_shape": {
                    k: {"n": v.n, "f1": v.f1, "readable": v.readable}
                    for k, v in _cells(cases, judgements, lambda c: c.shape).items()
                },
                "by_repo": {
                    k: {"n": v.n, "f1": v.f1, "readable": v.readable}
                    for k, v in _cells(cases, judgements, lambda c: c.repo).items()
                },
            }
    return out


def dump_json(path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
