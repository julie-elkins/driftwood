"""Stage 4: the same input, judged more than once, with the reply cache bypassed.

Every number this project reports is phrased as inside or outside a noise width, and
until this module existed every one of those widths was a control over the DATA -- a
shuffled ranking in stage 2, a coin weighted to the corpus positive rate in stage 3.
None of them measures the thing a reader assumes has already been measured: run the
same command twice, change nothing, and how far does the headline move?

That number is not optional here. Stage 3's largest reported margin over a constant is
0.015 F1, and stage 2's one readable gain was a tenth of a point wide. A run-to-run
width of 0.05 would make both of them unreadable, and nothing in the repository could
have said so either way.

Three decisions below are what make this honest, and each one is a place where the
comfortable version reports a NARROWER width than the truth:

**The reply cache has to be bypassed, and it is bypassed by giving every trial its
own.** `.cache/judgements` is keyed on the rendered prompt, the system prompt and the
model, deliberately, because that is what makes a published result re-readable without
a key. Run a null run over it and every trial after the first is served byte-identically
off disk: width 0.000, from a run that made no calls -- a perfectly clean null run and a
perfectly wrong one. `cache_dir=None` would fix the wrongness and throw the replies
away, which loses the audit trail and makes re-reading the analysis cost the whole bill
again. So each trial gets a directory of its own under `.cache/null-run/`, and the
historical cache is never read, never written and never counted.

That buys two things beyond correctness. A dead run resumes, because replies land on
disk as they arrive -- the same argument the reranker's pair cache rests on. And
`--trials` can be RAISED later for the price of the new trials alone, which matters
because the honest trial count is higher than the affordable one.

**Trials run one after another, not interleaved case by case.** Asking one case K times
back to back would put its K draws within seconds of each other, which narrows anything
varying over minutes or hours: a model snapshot rolling mid-run, load-dependent routing,
a cache warming somewhere upstream. Sequential trials are the conservative order. They
can only widen what this reports, and a noise measurement must not be wrong in the
narrow direction.

**A width from K trials is a LOWER BOUND, not a range.** min-max over 3 draws under-reads
the true spread, and it under-reads it in exactly the direction that makes every other
result in the project look more readable than it is. Every line here that prints a width
says so, and the JSON records the trial count next to it.

Two more properties, stated because they are what the report rests on. The contexts are
built ONCE and shared by every trial, so the only thing differing between trials is the
model's reply. And the free judges are this harness's own control: `always-false` and
`lexical-absence` are pure functions of the context, so their width must come out at
exactly 0.000. If it does not, the variance is in this file rather than in the judge,
and no paid trial should be bought until that is found. Calibrate the instrument before
quoting it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .cases import JudgeCase, class_balance
from .evaluate import MIN_CELL, Scores, score
from .judge import Judgement, is_paid

__all__ = [
    "DEFAULT_TRIALS",
    "METRICS",
    "CaseStability",
    "Trial",
    "detectable_effect",
    "format_null_run",
    "is_deterministic",
    "null_run_json",
    "spread",
    "stability",
    "summarise_trial",
    "trial_cache",
]

# Two trials give one comparison, and one comparison cannot tell a narrow width from a
# lucky pair -- the two draws either differ or they do not, and "they did not" is exactly
# what an under-powered null run says on its way to being wrong. Three is the smallest
# count where a third draw can contradict the first two.
#
# It is a FLOOR and not a recommendation. Every trial is a full priced arm of the eval, so
# the useful number here is bounded by money rather than by statistics, and the width this
# produces is reported as a lower bound for that reason. If a run-to-run width matters
# enough to act on, buy more trials: `--trials` reuses what is already banked.
DEFAULT_TRIALS = 3

# The four metrics a trial can move. `f1` is the primary one, and it is first here so it
# is first in every report and every JSON block. `recall` is included even though the
# chance control does not produce a range for it: an F1 that holds still while precision
# and recall trade off against each other is a different finding from one that holds still
# because nothing moved, and only the pair can tell them apart.
METRICS = ("f1", "precision", "recall", "accuracy_all")

# Directory name per trial. Zero-padded so `ls` sorts them in run order at up to 100
# trials, which is more than this will ever be run at and costs nothing to get right.
TRIAL_DIR = "trial-{:02d}"


def trial_cache(root: Path, trial: int) -> Path:
    """Where trial `n`'s replies live. One directory per trial, and that IS the bypass.

    Deliberately derived rather than passed in, so that two trials cannot be handed the
    same directory by a caller that meant well. A shared directory is not a slow null run
    or a noisy one; it is a null run that reports 0.000 and cannot be distinguished from a
    judge that is perfectly stable.
    """
    return root / TRIAL_DIR.format(trial)


def is_deterministic(judge_name: str) -> bool:
    """Is this judge a pure function of its context, so its width must be 0.000?

    Defined as the complement of `is_paid`, and imported from `judge` rather than
    re-listing the prefixes here: the two questions have the same answer today because
    every judge that calls a model is sampled and every judge that does not is a
    constant or a token comparison. A test pins the agreement rather than this comment,
    because if a free sampled judge is ever added the two will part company and the
    harness control is the thing that must not quietly start passing.
    """
    return not is_paid(judge_name)


@dataclass(frozen=True)
class Trial:
    """One whole pass over the corpus by one judge, and what it cost to get.

    `answers` is kept per case rather than only the aggregate `scores`, because the
    aggregate is the number that can be stable for the wrong reason: eight cases flipping
    to false and eight flipping to not-false leave F1 almost exactly where it was. The
    per-case matrix is what separates a stable judge from a judge whose instability
    happens to cancel, and it is small enough to put in the score file.
    """

    index: int
    answers: dict[str, bool | None]
    scores: Scores
    # Calls made or read for this trial, summed over cases. Differs from the case count
    # only for the per-claim judge, where one case is a batch of calls.
    calls: int = 0
    # Replies served off this trial's OWN cache directory. On a first run this is 0 by
    # construction and a non-zero value is the run resuming; on a re-read it is every
    # reply, which is what makes re-analysing a null run free. Reported rather than
    # assumed, because a trial that is quietly all-cached is a trial that measured
    # nothing.
    cached: int = 0
    truncated: int = 0
    unparsed: int = 0


@dataclass(frozen=True)
class CaseStability:
    """One case's answers across the trials, and which kind of instability it shows.

    The two kinds are separated because they are not equally bad. A case that answers
    `false` in one trial and `not-false` in another is a contradiction, and either answer
    is being counted as a judgement when it is a coin. A case that answers `false` in one
    trial and abstains in another is a judge whose confidence moves but whose direction
    does not -- worse than stable, better than contradictory, and it moves precision and
    the abstention rate rather than flipping a cell of the confusion matrix.
    """

    example_id: str
    verdict: str
    target: bool
    answers: tuple[bool | None, ...]

    @property
    def decided(self) -> tuple[bool, ...]:
        return tuple(a for a in self.answers if a is not None)

    @property
    def contradiction(self) -> bool:
        """Answered both ways across trials, ignoring abstentions."""
        return len(set(self.decided)) > 1

    @property
    def abstention_flip(self) -> bool:
        """Answered in one trial and abstained in another."""
        return any(a is None for a in self.answers) and bool(self.decided)

    @property
    def stable(self) -> bool:
        return not (self.contradiction or self.abstention_flip)


def spread(trials: Sequence[Trial]) -> dict[str, dict]:
    """Per-metric min, max, width and median over the trials.

    min-max rather than a percentile range, and that is a choice about which way to be
    wrong at three trials. A p5-p95 over three values is arithmetic on nothing -- it
    returns the extremes with a label that claims they are not the extremes. min-max says
    what it is: the widest gap actually observed, which is a lower bound on the real
    spread and is reported as one everywhere.
    """
    out: dict[str, dict] = {}
    for metric in METRICS:
        values = [float(getattr(t.scores, metric)) for t in trials]
        if not values:
            out[metric] = {"per_trial": [], "lo": 0.0, "hi": 0.0, "width": 0.0,
                           "median": 0.0}
            continue
        ordered = sorted(values)
        out[metric] = {
            "per_trial": values,
            "lo": ordered[0],
            "hi": ordered[-1],
            "width": ordered[-1] - ordered[0],
            "median": ordered[len(ordered) // 2],
        }
    return out


def stability(
    cases: Sequence[JudgeCase], trials: Sequence[Trial]
) -> tuple[list[CaseStability], dict]:
    """Per-case answers across trials, plus the summary that says where flips land.

    Only cases every trial answered are included, and the ones that are not are counted
    and returned rather than dropped quietly. A case missing from one trial should be
    impossible -- the contexts are built once and shared -- so a non-zero `partial` is a
    fault in the run and not a property of the judge.

    The `by_verdict` breakdown is the part worth having. A flip rate of 15% spread evenly
    over the five verdict classes is noise; the same 15% concentrated on `drift` is an
    instrument whose variance sits entirely on the 34 cases the metric is computed from,
    and F1 will then move several times further than the flat rate predicts.
    """
    scoreable = [c for c in cases if c.scoreable]
    per_case: list[CaseStability] = []
    partial = 0
    for case in scoreable:
        if not all(case.example_id in t.answers for t in trials):
            partial += 1
            continue
        per_case.append(
            CaseStability(
                example_id=case.example_id,
                verdict=case.verdict,
                target=bool(case.target),
                answers=tuple(t.answers[case.example_id] for t in trials),
            )
        )

    contradictions = [c for c in per_case if c.contradiction]
    abstention_flips = [c for c in per_case if c.abstention_flip and not c.contradiction]
    unstable = [c for c in per_case if not c.stable]

    by_verdict: dict[str, dict[str, int]] = {}
    for case in per_case:
        row = by_verdict.setdefault(case.verdict, {"n": 0, "unstable": 0})
        row["n"] += 1
        if not case.stable:
            row["unstable"] += 1

    positives = [c for c in per_case if c.target]
    negatives = [c for c in per_case if not c.target]

    def rate(chosen: list[CaseStability]) -> float:
        hits = sum(1 for c in chosen if not c.stable)
        return hits / len(chosen) if chosen else 0.0

    return per_case, {
        "n": len(per_case),
        "partial": partial,
        "stable": len(per_case) - len(unstable),
        "unstable": len(unstable),
        "contradictions": len(contradictions),
        "abstention_flips": len(abstention_flips),
        "unstable_rate": len(unstable) / len(per_case) if per_case else 0.0,
        "by_verdict": by_verdict,
        "positive_unstable_rate": rate(positives),
        "negative_unstable_rate": rate(negatives),
        "positives": len(positives),
        "negatives": len(negatives),
    }


def detectable_effect(widths: dict[str, dict], metric: str = "f1") -> float:
    """The smallest change in `metric` this judge could show. Which is its own width.

    Named as a function rather than left as a subtraction in the report, because it is
    the output of the whole stage: a difference smaller than this is not a difference,
    whatever else is true about it, and it belongs in the score file under a name a later
    session can grep for.
    """
    return float(widths.get(metric, {}).get("width", 0.0))


def _trial_row(trial: Trial) -> str:
    s = trial.scores
    return (
        f"  trial {trial.index:<5}{s.n:>6}{s.f1:>8.3f}{s.precision:>8.3f}"
        f"{s.recall:>8.3f}{s.accuracy_all:>8.1%}{s.abstention_rate:>8.1%}"
        f"{trial.calls:>8}{trial.cached:>8}{trial.truncated:>7}"
    )


_TRIAL_HEADER = (
    f"  {'':<11}{'n':>6}{'F1':>8}{'prec':>8}{'rec':>8}{'acc':>8}{'abst':>8}"
    f"{'calls':>8}{'cached':>8}{'trunc':>7}"
)


def format_null_run(
    cases: Sequence[JudgeCase],
    per_judge: dict[str, list[Trial]],
    *,
    arm: str,
    chance: dict[str, tuple[float, float, float]] | None = None,
    cache_root: Path | None = None,
    duplicate_prompts: int | None = None,
) -> str:
    """The whole null run: per trial, per metric, per case, and against the chance range.

    Ordered so the two sentences a reader needs come before the tables rather than after
    them. What was held constant is first, because a null run that accidentally varied
    something is not a wide null run, it is a different measurement. The comparison
    against the chance range is last, because it is the only part that can change how
    every other result in the project has to be read.
    """
    balance = class_balance(list(cases))
    trial_counts = {len(t) for t in per_judge.values()}
    lines = [
        f"NULL RUN -- the same input judged more than once, arm `{arm}`",
        "",
        "WHAT THIS MEASURES, and what it does not. Every other width in this project is a",
        "control over the DATA: a shuffled ranking, a coin at the corpus positive rate.",
        "This one is a control over the RUN. It says how far the headline moves when",
        "nothing changes at all, which is the floor under every gap quoted anywhere else.",
        "",
        f"{balance['scoreable']} scoreable cases, {balance['positive']} positive "
        f"({balance['positive_rate']:.1%}), {balance['held_out_unclear']} held out as "
        "unclear",
        "held constant across trials: the cases, the contexts (built once and shared),",
        "  the prompts, the model, the reply budget and the effort setting.",
        "varying: only the model's reply. Each trial reads and writes a cache directory of",
        f"  its own{f' under {cache_root}' if cache_root else ''}, so no trial can be "
        "served another trial's answer --",
        "  which is the one mistake that reports width 0.000 from a run that made no calls.",
    ]
    if duplicate_prompts:
        # Two cases whose rendered prompt is byte-identical collide on one cache key, so
        # within a trial the second is served the first's reply. Correct -- one prompt is
        # one purchase -- and it makes those cases perfectly correlated by construction,
        # which suppresses measured variance. Counted rather than fixed, because the fix
        # would be to pay twice for the same question.
        lines.append(
            f"  NOTE: {duplicate_prompts} case(s) share a rendered prompt with another "
            "case, so within a trial they are served one reply between them and cannot "
            "disagree. That narrows every width below."
        )
    elif duplicate_prompts is None:
        lines.append(
            "  NOT CHECKED: whether two cases share a rendered prompt. Only the per-page "
            "judge renders one prompt per case, so the check is unavailable for a "
            "per-claim arm rather than passing on it."
        )
    if len(trial_counts) == 1:
        trials = trial_counts.pop()
        lines.append("")
        lines.append(f"{trials} trial(s) per judge.")
    lines.append("")
    # Two columns below that are read wrongly on the first look, both times in the
    # direction of thinking something is missing. `n` and `calls` differ because the
    # held-out `unclear` cases are judged and not scored -- they are what the abstention
    # calibration needs -- so `calls` counts every context and `n` counts the scoreable
    # ones. And `cached` is 0 for a free judge because it makes no request to cache, which
    # is not the same fact as a trial that failed to bank its replies.
    lines.append(
        "columns: `n` is the SCOREABLE cases; `calls` counts every context judged, "
        "including the"
    )
    lines.append(
        "  held-out unclear ones. `cached` is replies served from this trial's own "
        "directory, and is"
    )
    lines.append("  0 by construction for a judge that makes no request.")
    lines.append("")

    controls: list[tuple[str, float]] = []
    for name in sorted(per_judge):
        trials = per_judge[name]
        widths = spread(trials)
        lines.append(f"--- {name} ---")
        if not trials:
            lines.append("  no trials ran")
            lines.append("")
            continue

        worst_truncated = max(t.truncated for t in trials)
        if worst_truncated:
            # Same gate the eval applies, for the same reason and with more force here: a
            # null run whose replies were cut off measures the ceiling's interaction with
            # prompt length, and truncation tracks the hard cases rather than a random
            # sample. The width it produces is not a noise floor, it is an artefact.
            lines.append(
                f"  NOT A RESULT: up to {worst_truncated} reply/replies per trial hit the "
                "token ceiling. Truncation follows prompt length, so the damage is on the "
                "hard cases; raise --retry-max-tokens and re-run before reading any width "
                "below."
            )
        total_unparsed = sum(t.unparsed for t in trials)
        if total_unparsed:
            lines.append(
                f"  WARNING: {total_unparsed} reply/replies across all trials could not be "
                "parsed as a verdict, each scored as an abstention. An unparsed reply is "
                "itself run-to-run variance and is counted as instability below, not "
                "dropped."
            )

        lines.append(_TRIAL_HEADER)
        for trial in trials:
            lines.append(_trial_row(trial))

        lines.append("")
        lines.append(f"  spread over {len(trials)} trial(s), min .. max:")
        for metric in METRICS:
            row = widths[metric]
            lines.append(
                f"    {metric:<14}{row['lo']:.3f} .. {row['hi']:.3f}   "
                f"width {row['width']:.3f}   (median {row['median']:.3f})"
            )
        lines.append(
            f"    A LOWER BOUND. {len(trials)} draws cannot show a spread wider than the "
            "widest pair they contain, and the error runs in the direction that makes "
            "everything else look readable."
        )

        if is_deterministic(name):
            # The harness's control on itself, and it is not a formality: case ordering,
            # a shared cache, a context rebuilt per trial, or a judge holding state would
            # all show up here and nowhere else, on a judge that cannot vary.
            worst = max(widths[m]["width"] for m in METRICS)
            if worst == 0.0:
                controls.append((name, worst))
                lines.append(
                    "    HARNESS CONTROL: this judge is a pure function of its context, "
                    "and every width above is exactly 0.000 as it must be. The harness "
                    "adds no variance of its own."
                )
            else:
                lines.append(
                    f"    HARNESS FAULT: this judge is a pure function of its context and "
                    f"cannot vary, yet a metric moved by {worst:.3f} across trials. The "
                    "variance is in the harness -- case ordering, context building, or a "
                    "cache shared between trials -- not in the judge. Do not buy a paid "
                    "trial until this reads 0.000."
                )
        else:
            mde = detectable_effect(widths)
            lines.append(
                f"    MINIMUM DETECTABLE EFFECT: {mde:.3f} F1. A change smaller than that "
                "cannot be told apart from running the same command twice, however it was "
                "produced and whatever else is true about it."
            )

        per_case, summary = stability(cases, trials)
        lines.append("")
        if summary["partial"]:
            lines.append(
                f"  {summary['partial']} case(s) were not answered by every trial and are "
                "excluded from the stability figures. The contexts are shared, so this "
                "should be 0: a non-zero count is a fault in the run."
            )
        if summary["n"]:
            lines.append(
                f"  per-case stability: {summary['stable']} of {summary['n']} case(s) "
                f"answered the same way every time "
                f"({1 - summary['unstable_rate']:.1%}); {summary['unstable']} did not "
                f"({summary['contradictions']} answered both ways, "
                f"{summary['abstention_flips']} flipped only between an answer and an "
                "abstention)"
            )
            lines.append(
                "  a stable headline is not a stable judge: flips in opposite directions"
                " cancel in F1 and are still coin flips, which is why this is counted per"
                " case."
            )
            if summary["positives"] and summary["negatives"]:
                lines.append(
                    f"  on the {summary['positives']} positive case(s): "
                    f"{summary['positive_unstable_rate']:.1%} unstable, against "
                    f"{summary['negative_unstable_rate']:.1%} on the "
                    f"{summary['negatives']} negative(s)"
                )
                if summary["positive_unstable_rate"] > 2 * max(
                    summary["negative_unstable_rate"], 1e-9
                ):
                    lines.append(
                        "    the instability is CONCENTRATED ON THE POSITIVES, which is "
                        "the half F1 is computed from -- so F1 will move further than the "
                        "overall flip rate suggests"
                    )
            lines.append("  by the verdict Julie wrote:")
            for verdict in ("drift", "new", "cosmetic", "unrelated"):
                row = summary["by_verdict"].get(verdict)
                if not row:
                    continue
                mark = "" if row["n"] >= MIN_CELL else f"  (n<{MIN_CELL}: not readable)"
                lines.append(
                    f"    {verdict:<12}{row['unstable']:>4} of {row['n']:>4} unstable"
                    f"{mark}"
                )
            flippers = [c for c in per_case if c.contradiction]
            if flippers:
                shown = sorted(c.example_id for c in flippers)[:8]
                lines.append(
                    "  answered both ways: "
                    + ", ".join(shown)
                    + (f" ... and {len(flippers) - len(shown)} more" if
                       len(flippers) > len(shown) else "")
                )
        lines.append("")

    # Only judges that CAN vary. A deterministic judge's 0.000 against the chance range is
    # arithmetic on a control, not a comparison, and printing the heading over an empty
    # list read as a comparison that had failed to produce anything.
    comparable = [
        name for name in sorted(per_judge)
        if per_judge[name] and not is_deterministic(name)
    ]
    if chance and comparable:
        lines.append("READ AGAINST THE CHANCE RANGE, which is the control this replaces as")
        lines.append("the binding one if it turns out to be wider:")
        for name in comparable:
            trials = per_judge[name]
            widths = spread(trials)
            for metric in ("f1", "accuracy_all", "precision"):
                if metric not in chance:
                    continue
                low, _mid, high = chance[metric]
                chance_width = high - low
                run_width = widths[metric]["width"]
                lines.append(
                    f"  {name} {metric}: chance {low:.3f} .. {high:.3f} "
                    f"(width {chance_width:.3f}) vs run-to-run width {run_width:.3f}"
                )
                if run_width == 0.0:
                    lines.append(
                        "    run-to-run width is 0.000, so the chance range remains the "
                        "binding floor -- but check `cached` above before believing it"
                    )
                elif chance_width >= run_width:
                    lines.append(
                        f"    the chance range is {chance_width / run_width:.1f}x wider, "
                        "so it stays the binding floor and nothing quoted against it "
                        "needs revisiting"
                    )
                else:
                    lines.append(
                        f"    RUN-TO-RUN NOISE IS {run_width / chance_width:.1f}x WIDER "
                        "THAN THE CHANCE RANGE. Every gap in this project quoted as "
                        "outside the chance range was quoted against the weaker of two "
                        "controls, and has to be re-read against this width."
                    )
        lines.append("")

    if controls:
        lines.append(
            "harness control(s) passed at exactly 0.000: "
            + ", ".join(name for name, _ in controls)
        )
    return "\n".join(lines).rstrip() + "\n"


def null_run_json(
    cases: Sequence[JudgeCase],
    per_judge: dict[str, list[Trial]],
    *,
    arm: str,
    tally: dict[str, int],
    chance: dict[str, tuple[float, float, float]] | None = None,
    extra: dict | None = None,
) -> dict:
    """Machine-readable null run. The per-case answer matrix is in it on purpose.

    A width without the matrix behind it cannot be re-derived, and the matrix is the only
    thing that can answer a question this stage will certainly be asked later: were the
    same cases unstable the second time. It is `trials x cases` booleans, which for this
    corpus is smaller than one cached reply.
    """
    # Every case, not only the scoreable ones, the same way the eval's provenance block
    # does it: `class_balance` computes its rates over the scoreable set itself and counts
    # the held-out `unclear` cases separately. Pre-filtering here wrote
    # `held_out_unclear: 0` into the file while 20 cases were in fact held out and judged
    # -- a zero that reads as "none were" rather than as "not counted".
    balance = class_balance(list(cases))
    out: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provenance": {
            "measurement": "run_to_run_noise",
            "arm": arm,
            "corpus": dict(tally),
            "balance": balance,
            "primary_metric": "f1_positive_class",
            # Named in the file, not just described in a docstring: a later reader
            # comparing two null runs has to know that a 3-trial width and a 10-trial
            # width are not the same quantity.
            "width_is": "min-max over trials, a LOWER BOUND on the true spread",
            "held_constant": [
                "cases", "contexts", "prompt", "model", "max_tokens", "effort",
            ],
            "cache_bypass": "one cache directory per trial; the shared reply cache is "
                            "neither read nor written",
            "trial_order": "sequential, not interleaved per case, so any variation over "
                           "minutes or hours is inside the measurement rather than "
                           "averaged out of it",
        },
        "judges": {},
    }
    if extra:
        out["provenance"].update(extra)
    for name, trials in sorted(per_judge.items()):
        widths = spread(trials)
        per_case, summary = stability(cases, trials)
        out["judges"][name] = {
            "trials": len(trials),
            "deterministic_by_construction": is_deterministic(name),
            "spread": widths,
            "minimum_detectable_effect_f1": detectable_effect(widths),
            "stability": summary,
            "per_trial": [
                {
                    "trial": t.index,
                    "n": t.scores.n,
                    "f1": t.scores.f1,
                    "precision": t.scores.precision,
                    "recall": t.scores.recall,
                    "accuracy_all": t.scores.accuracy_all,
                    "abstained": t.scores.abstained,
                    "unparsed": t.scores.unparsed,
                    "truncated": t.scores.truncated,
                    "calls": t.calls,
                    "cached": t.cached,
                    "confusion": {
                        "tp": t.scores.tp, "fp": t.scores.fp,
                        "fn": t.scores.fn, "tn": t.scores.tn,
                    },
                }
                for t in trials
            ],
            "answers": {
                c.example_id: {
                    "verdict": c.verdict,
                    "target": c.target,
                    # Strings rather than booleans-and-null, because `null` in a JSON
                    # answer list reads as a missing value and this one is a verdict:
                    # the judge said it could not tell.
                    "answers": [
                        "abstain" if a is None else ("false" if a else "not-false")
                        for a in c.answers
                    ],
                    "contradiction": c.contradiction,
                    "abstention_flip": c.abstention_flip,
                }
                for c in per_case
            },
        }
        if chance:
            out["judges"][name]["chance_range"] = {
                k: list(v) for k, v in chance.items()
            }
    return out


def summarise_trial(
    index: int,
    cases: Sequence[JudgeCase],
    judgements: dict[str, Judgement],
) -> Trial:
    """One trial's judgements, reduced to what the report and the score file need."""
    got = score(list(cases), judgements)
    return Trial(
        index=index,
        answers={k: v.answer for k, v in judgements.items()},
        scores=got,
        calls=sum(j.calls for j in judgements.values()),
        cached=sum(1 for j in judgements.values() if j.cached),
        truncated=got.truncated,
        unparsed=got.unparsed,
    )
