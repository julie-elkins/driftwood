"""Score somebody else's staleness detector against this corpus, and gate the result.

WHAT THIS IS FOR. Everything else in this repository measures one judge: mine. This
module lets a third party submit predictions and find out whether their detector cleared
the bars this corpus establishes -- without needing an API key, the 543MB of clones, or
any of the model machinery. They submit `example_id -> answer` and get a verdict.

WHY A BENCH RATHER THAN A TOOL. The claim "a model can spot documentation that stopped
being true" is made constantly and almost never priced. What makes it checkable is not
another detector; it is a corpus with hand labels, a floor that costs nothing to beat,
and a measured noise width below which no difference is a difference. Those three already
exist here. This is the front door to them.

THE GATE IS THE PRODUCT, and it is three separate bars rather than a leaderboard:

  1. Beat the best FREE floor on F1 **by more than the measured run-to-run width.** A
     detector that edges out a keyword rule by less than the harness moves on its own has
     demonstrated nothing, and sorting by F1 would rank it above the rule anyway.
  2. Beat the CONSTANT on accuracy. `always-not-false` -- answer "not stale" every single
     time -- scores about 69% here, because most changes invalidate nothing. That constant
     is the real competitor and it is the one most published detectors are never shown
     against.
  3. Clear the CHANCE range's upper bound on F1. Scoring inside the range a random
     answerer occupies is not evidence of signal.

A submission failing any of the three is NOT ADMISSIBLE, which is a different statement
from "worse". It means the result does not survive this corpus's own error bars, and the
honest next step is more labels rather than a better prompt.

TWO REFUSALS THAT COME BEFORE ANY SCORING, both of which this project learned the hard way:

  - **The recorded floors must come from the corpus that is on disk now.** Floors here
    move every time a sheet is labelled -- `always-false` F1 went 0.444 -> 0.415 -> 0.458
    across three corpus sizes -- so pairing a submission with a floor measured on a
    different number of cases flatters or punishes it for free. The mismatch is checked,
    not warned about.
  - **A submission that abstains is not scored on the same denominator as the floors.**
    `score()` skips cases with no judgement, so an abstaining detector gets a smaller `n`
    and its F1 stops being comparable to a floor computed on all of them. That is
    reported as NOT COMPARABLE rather than quietly scored.

Neither refusal exits zero. "Could not compare" must never read like "did not win".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from driftwood.judge.cases import JudgeCase
from driftwood.judge.evaluate import Scores, score
from driftwood.judge.judge import Judgement

# The arm these floors were measured on. Shape-A cases carrying a code path -- the 95 the
# stage-4 null run was bought on. Named rather than inferred, because scoring a submission
# against one arm's floors on another arm's cases is the mismatch above wearing a disguise.
SEEDED_ARM = "seeded"

ANSWER_WORDS = {
    "false": True,      # the doc WAS false about the code at this commit
    "stale": True,
    "true": True,
    "not-false": False,
    "not_false": False,
    "fresh": False,
    "false_positive": False,
    "abstain": None,
    "unknown": None,
    "": None,
}


class BenchRefused(Exception):
    """A refusal that must not be reported as a score."""

    def __init__(self, state: str, message: str, guidance: str) -> None:
        super().__init__(message)
        self.state = state
        self.message = message
        self.guidance = guidance


@dataclass(frozen=True)
class Bars:
    """The three bars, read from recorded measurements rather than recomputed."""

    corpus: dict
    best_free_name: str
    best_free_f1: float
    constant_name: str
    constant_accuracy: float
    chance_f1_p95: float
    width_f1: float
    floors_path: str
    width_path: str


def _corpus_of(payload: dict, path: Path) -> dict:
    corpus = payload.get("provenance", {}).get("corpus")
    if not corpus:
        raise BenchRefused(
            "UNUSABLE_MEASUREMENT",
            f"{path} carries no provenance.corpus block.",
            "Without it there is no way to tell which corpus the numbers were measured "
            "on, and a floor from a different corpus size is worse than no floor. "
            "Re-generate the file with the current harness.",
        )
    return corpus


def load_bars(floors_path: Path, width_path: Path, live_corpus: dict) -> Bars:
    """Read the floors and the width, and refuse if either is about a different corpus."""
    floors = json.loads(floors_path.read_text(encoding="utf-8"))
    width = json.loads(width_path.read_text(encoding="utf-8"))

    floors_corpus = _corpus_of(floors, floors_path)
    width_corpus = _corpus_of(width, width_path)

    # Compare on the fields that decide comparability. `scoreable` is the denominator and
    # `with_code_path` is the seeded arm's n; a difference in either makes the numbers
    # about a different measurement regardless of how close they look.
    keys = ("scoreable", "with_code_path", "verdicts")
    for name, recorded in (("floors", floors_corpus), ("width", width_corpus)):
        mismatched = {
            key: (recorded.get(key), live_corpus.get(key))
            for key in keys
            if recorded.get(key) != live_corpus.get(key)
        }
        if mismatched:
            raise BenchRefused(
                "CORPUS_MISMATCH",
                f"The recorded {name} were measured on a different corpus: "
                + ", ".join(
                    f"{key} was {was} and is now {now}"
                    for key, (was, now) in mismatched.items()
                ),
                "NOTHING WAS SCORED. Floors here move every time a sheet is labelled, so "
                "pairing a submission with a floor from another corpus size hands it free "
                "credit in one direction or free blame in the other. Re-run "
                "`driftwood judge-eval --judges floors --arms seeded` against the current "
                "labels and pass the new file.",
            )

    arm = floors.get("arms", {}).get(SEEDED_ARM)
    if not arm:
        raise BenchRefused(
            "UNUSABLE_MEASUREMENT",
            f"{floors_path} has no '{SEEDED_ARM}' arm.",
            f"This bench scores the {SEEDED_ARM} arm. Generate floors with "
            f"`--arms {SEEDED_ARM}`.",
        )

    judges = arm.get("judges", {})
    # The best FREE floor, chosen by F1 among the cost-nothing judges. Picked from the
    # file rather than named in code: the winner has changed as the corpus grew, and a
    # hardcoded name is a floor chosen to lose.
    free = {
        name: payload
        for name, payload in judges.items()
        if name.startswith(("always-", "lexical-absence"))
    }
    if not free:
        raise BenchRefused(
            "UNUSABLE_MEASUREMENT",
            f"{floors_path} records no free floors.",
            "Generate it with `--judges floors`.",
        )
    best_free_name = max(free, key=lambda name: free[name]["f1"])

    constant_name = "always-not-false"
    if constant_name not in judges:
        raise BenchRefused(
            "UNUSABLE_MEASUREMENT",
            f"{floors_path} does not include '{constant_name}'.",
            "That constant is the bar most detectors actually fail, so a run without it "
            "cannot produce a verdict here. Generate floors with `--judges floors`.",
        )

    width_judges = width.get("judges", {})
    if not width_judges:
        raise BenchRefused(
            "UNUSABLE_MEASUREMENT",
            f"{width_path} records no judges.",
            "Pass the output of `driftwood judge-null-run`.",
        )
    measured = next(iter(width_judges.values()))
    mde = measured.get("minimum_detectable_effect_f1")
    if mde is None:
        raise BenchRefused(
            "UNUSABLE_MEASUREMENT",
            f"{width_path} has no minimum_detectable_effect_f1.",
            "Without a measured run-to-run width there is no way to tell a real gap from "
            "a rerun, and this bench will not issue a verdict without one.",
        )

    return Bars(
        corpus=live_corpus,
        best_free_name=best_free_name,
        best_free_f1=float(free[best_free_name]["f1"]),
        constant_name=constant_name,
        constant_accuracy=float(judges[constant_name]["accuracy_all"]),
        chance_f1_p95=float(measured["chance_range"]["f1"][2]),
        width_f1=float(mde),
        floors_path=str(floors_path),
        width_path=str(width_path),
    )


def parse_predictions(text: str, *, source: str) -> dict[str, bool | None]:
    """One JSON object per line: {"example_id": "...", "answer": false}.

    `answer` is true when the detector says the documentation WAS false about the code,
    false when it says it was not, and null when it declines. The words in `ANSWER_WORDS`
    are accepted too, because "false" meaning "the doc is false" reads backwards to most
    people and a submission that got it inverted should fail on its predictions rather
    than on its vocabulary.
    """
    answers: dict[str, bool | None] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BenchRefused(
                "UNPARSEABLE_SUBMISSION",
                f"{source} line {number} is not JSON: {exc}",
                "One JSON object per line. Nothing was scored -- a partially read "
                "submission would be scored on a subset nobody chose.",
            ) from exc

        example_id = record.get("example_id")
        if not example_id:
            raise BenchRefused(
                "UNPARSEABLE_SUBMISSION",
                f"{source} line {number} has no example_id.",
                "Every prediction must name the case it is about.",
            )
        if example_id in answers:
            raise BenchRefused(
                "DUPLICATE_PREDICTION",
                f"{source} predicts {example_id} more than once.",
                "Two answers for one case means the submission has no single verdict "
                "for it. Nothing was scored; de-duplicate and resubmit.",
            )

        raw = record.get("answer")
        if isinstance(raw, bool) or raw is None:
            answers[example_id] = raw
        elif isinstance(raw, str) and raw.strip().lower() in ANSWER_WORDS:
            answers[example_id] = ANSWER_WORDS[raw.strip().lower()]
        else:
            raise BenchRefused(
                "UNPARSEABLE_SUBMISSION",
                f"{source} line {number} has an unreadable answer: {raw!r}",
                "Use true (the doc was false about the code), false (it was not), or "
                "null (abstain).",
            )
    if not answers:
        raise BenchRefused(
            "EMPTY_SUBMISSION",
            f"{source} contains no predictions.",
            "An empty submission is not a detector that flagged nothing -- that would be "
            "`always-not-false`, which is already in the floors. Nothing was scored.",
        )
    return answers


def arm_cases(cases: list[JudgeCase]) -> list[JudgeCase]:
    """The seeded arm: scoreable cases carrying a code path."""
    return [case for case in cases if case.scoreable and case.code_path]


@dataclass(frozen=True)
class Verdict:
    name: str
    scores: Scores
    bars: Bars
    comparable: bool
    reasons: list[str]
    unknown_ids: list[str]
    missing_ids: list[str]

    @property
    def false_flag_rate(self) -> float | None:
        """Share of the no-fault cases that got flagged anyway.

        The standard false positive rate, reported because of what this corpus looks
        like: roughly seven in ten cases invalidate nothing, so a detector's cost in
        practice is dominated by how often it interrupts somebody over a change that was
        fine. F1 hides that -- it is computed over the positives and says nothing about
        how much noise the negatives absorbed. This is not a bar and does not decide
        admissibility; it is the figure to quote next to one.
        """
        negatives = self.scores.fp + self.scores.tn
        return (self.scores.fp / negatives) if negatives else None

    @property
    def admissible(self) -> bool:
        return self.comparable and not self.reasons


def judge_submission(
    name: str, answers: dict[str, bool | None], cases: list[JudgeCase], bars: Bars
) -> Verdict:
    selected = arm_cases(cases)
    known = {case.example_id for case in selected}

    unknown = sorted(set(answers) - known)
    missing = sorted(known - set(answers))

    judgements = {
        example_id: Judgement(
            example_id=example_id, arm=SEEDED_ARM, judge=name, answer=answer
        )
        for example_id, answer in answers.items()
        if example_id in known
    }
    scores = score(selected, judgements)

    reasons: list[str] = []

    # Comparability first. An abstaining detector is scored on fewer cases than the
    # floors were, so its F1 is not on the same axis -- which is the trap this project
    # spent a whole stage on ("do not pair a 70-case judge number with a 95-case floor").
    comparable = scores.n == len(selected) and scores.abstained == 0
    if not comparable:
        reasons.append(
            f"NOT COMPARABLE: answered {scores.answered} of {len(selected)} cases "
            f"({scores.abstained} abstained, {len(selected) - scores.n} unscored). The "
            f"floors are measured on all {len(selected)}, so this F1 is computed on a "
            "different denominator and is not on the same axis. A detector that abstains "
            "on the hard cases and is right about the easy ones scores near-perfectly "
            "here, which is why this is a refusal rather than a footnote."
        )

    gap = scores.f1 - bars.best_free_f1
    if gap <= bars.width_f1:
        reasons.append(
            f"INSIDE THE NOISE: F1 {scores.f1:.3f} against the best free floor "
            f"{bars.best_free_name} at {bars.best_free_f1:.3f} is a gap of {gap:+.3f}, "
            f"and this harness moves {bars.width_f1:.3f} on its own between identical "
            "runs. A gap smaller than the width is not a result in either direction."
        )
    if scores.accuracy_all <= bars.constant_accuracy:
        reasons.append(
            f"LOSES TO A CONSTANT: accuracy {scores.accuracy_all:.3f} against "
            f"{bars.constant_name} at {bars.constant_accuracy:.3f}. Answering "
            '"not stale" every time scores higher.'
        )
    if scores.f1 <= bars.chance_f1_p95:
        reasons.append(
            f"INSIDE CHANCE: F1 {scores.f1:.3f} is at or below the chance range's 95th "
            f"percentile of {bars.chance_f1_p95:.3f} on this class balance."
        )

    return Verdict(
        name=name, scores=scores, bars=bars, comparable=comparable,
        reasons=reasons, unknown_ids=unknown, missing_ids=missing,
    )


def format_verdict(verdict: Verdict) -> str:
    scores = verdict.scores
    bars = verdict.bars
    lines = [
        f"SUBMISSION: {verdict.name}",
        f"  corpus        {bars.corpus.get('verdicts')} verdicts, "
        f"{bars.corpus.get('scoreable')} scoreable, "
        f"{bars.corpus.get('with_code_path')} on the {SEEDED_ARM} arm",
        f"  scored        {scores.n} case(s), {scores.answered} answered, "
        f"{scores.abstained} abstained",
        f"  confusion     tp {scores.tp}  fp {scores.fp}  fn {scores.fn}  tn {scores.tn}",
        f"  F1            {scores.f1:.3f}",
        f"  accuracy      {scores.accuracy_all:.3f}",
    ]
    rate = verdict.false_flag_rate
    if rate is not None:
        lines.append(
            f"  false flags   {rate:.3f} of the {scores.fp + scores.tn} no-fault case(s)"
        )

    lines += [
        "",
        "THE BARS, from recorded measurements on this same corpus:",
        f"  best free floor   {bars.best_free_name} at F1 {bars.best_free_f1:.3f}",
        f"  constant          {bars.constant_name} at accuracy {bars.constant_accuracy:.3f}",
        f"  chance F1 p95     {bars.chance_f1_p95:.3f}",
        f"  run-to-run width  {bars.width_f1:.3f}  (nothing smaller is a result)",
        f"  floors            {bars.floors_path}",
        f"  width             {bars.width_path}",
        "",
    ]

    if verdict.unknown_ids:
        lines.append(
            f"  {len(verdict.unknown_ids)} prediction(s) name cases not in this corpus "
            "and were ignored: " + ", ".join(verdict.unknown_ids[:5])
            + (" ..." if len(verdict.unknown_ids) > 5 else "")
        )
    if verdict.missing_ids:
        lines.append(
            f"  {len(verdict.missing_ids)} case(s) had no prediction. They are NOT "
            "counted as correct and NOT counted as wrong -- they are simply unscored, "
            "which is why the comparability check above exists."
        )
    if verdict.unknown_ids or verdict.missing_ids:
        lines.append("")

    if verdict.admissible:
        lines += [
            "ADMISSIBLE.",
            "  The submission clears the free floor by more than this harness's own",
            "  run-to-run width, beats the constant on accuracy, and sits above the",
            "  chance range. That is the strongest statement this corpus can support.",
            "",
            "  WHAT IT STILL DOES NOT SHOW. 155 scoreable cases is a small corpus and its",
            "  positive class is thin; a result here is not a claim about documentation in",
            "  general. Read VERIFICATION of the labels themselves in the README before",
            "  quoting any figure, including this one.",
        ]
    else:
        lines.append("NOT ADMISSIBLE.")
        for reason in verdict.reasons:
            lines.append(f"  - {reason}")
        lines += [
            "",
            "  'Not admissible' is not 'worse'. It means the result does not survive this",
            "  corpus's own error bars, and the honest next step is more labelled cases",
            "  rather than a better prompt.",
        ]
    return "\n".join(lines)
