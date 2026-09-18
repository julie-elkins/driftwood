"""The judges: three that cost nothing, and one that calls a model.

The free ones are not scaffolding. A judge's accuracy means nothing on its own at a
28.6% positive rate, so the number that matters is the *gap* to a floor, and the
floors have to be measured on the same 105 cases rather than quoted from arithmetic:

- `AlwaysJudge("not-false")` -- the majority-class constant. Scores 71.4% accuracy
  and F1 0.00. This is the bar accuracy has to clear to mean anything at all.
- `AlwaysJudge("false")` -- the opposite constant. Scores 28.6% accuracy and F1 0.44,
  which is the bar *F1* has to clear. It is easy to forget that answering "drift"
  every single time is not an F1 of zero, and a judge scoring 0.40 would look
  respectable next to the accuracy floor while being worse than a stuck switch.
- `PriorJudge` -- coin flips at the corpus positive rate, over many trials. Gives a
  noise *range* rather than a point, which is what says whether a gap is readable.
  Same role as the shuffled-ranking arm in stage 2, and it exists for the same
  reason: stage 2's headline gaps all turned out to sit inside their noise range,
  and that was only visible because the control was built before the result.
- `LexicalJudge` -- no model, no credentials: flags a document that marks up an
  identifier which appears in none of the code files shown. This is the thing a
  person writes in an afternoon without an LLM, and it is the honest comparison. If
  the model arm does not beat it, that is the finding, and it would not be visible
  against constants alone.

`AnthropicJudge` is last on purpose. It is the only part of stage 3 that needs money
or a key, and everything above runs without either.

Abstention is a first-class answer. A judge returns `None` when it cannot tell, and
those are scored separately rather than folded into "not false" -- a judge that says
"I can't tell" on the 20 cases Julie also could not tell is behaving well, and
counting its abstentions as negatives would hide that in both directions.
"""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..mining.identifiers import extract, literal_spans
from . import DEFAULT_JUDGE_MODEL
from .context import JudgeContext, context_hash, render

__all__ = [
    "AlwaysJudge",
    "AnthropicJudge",
    "Judge",
    "Judgement",
    "LexicalJudge",
    "PriorJudge",
    "SYSTEM_PROMPT",
]

# The prompt is part of the experiment, so it is versioned with the code and hashed
# into the cache key. Three things in it are load-bearing:
#
# 1. The question is asked about the state on screen, in the present tense. Asking
#    "is this documentation out of date" invites a judge to reason about time it
#    cannot observe.
# 2. Abstention is offered explicitly and described as a legitimate answer. Without
#    that, a model asked a yes/no question answers yes or no, and the 20 held-out
#    cases become unusable as a calibration set.
# 3. It must quote the claim. A verdict with no quoted span cannot be checked by
#    hand, and hand-checking a sample is the only defence against a judge that is
#    right for the wrong reason.
SYSTEM_PROMPT = """\
You are reviewing a repository's documentation against its source code at one \
specific commit. You will be shown one documentation file and one or more code \
files, all as they exist at that commit.

Answer one question: does the documentation make a statement that is FALSE about \
the code as shown?

A statement is false if a reader who trusted it would be wrong about the code: a \
function, parameter, attribute or setting that does not exist or is named \
differently; a described default, type, return value or behaviour that contradicts \
the code; an example that could not run as written.

These are NOT false:
- Prose about design, intent, rationale or history.
- Something described at a higher level than the code, or simplified.
- A statement about code that is not among the files shown. If the relevant code is \
not here, you cannot tell.
- Wording, formatting, typography or links.
- A statement you merely cannot verify.

If the code needed to decide is not in front of you, or the documentation is about \
something the shown files do not cover, answer "unclear". That is a real answer and \
is preferred over a guess.

Reply with JSON only, in this exact shape:

{"verdict": "false" | "not-false" | "unclear",
 "claim": "the sentence or phrase from the documentation, verbatim, or null",
 "code": "the code file and symbol that contradicts it, or null",
 "reason": "one or two sentences"}
"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_VERDICT_TO_BOOL: dict[str, bool | None] = {
    "false": True,
    "not-false": False,
    "unclear": None,
}


@dataclass(frozen=True)
class Judgement:
    """One answer, plus enough to audit it by hand."""

    example_id: str
    arm: str
    judge: str
    # True = the doc was false about the code at this commit. None = abstained.
    answer: bool | None
    claim: str | None = None
    code: str | None = None
    reason: str = ""
    # True when a model was asked but its reply could not be read as a verdict.
    # Scored as an abstention and counted separately: a parse failure silently
    # becoming "not-false" would earn free credit on 75 of 105 cases.
    unparsed: bool = False
    cached: bool = False

    @property
    def abstained(self) -> bool:
        return self.answer is None


class Judge(Protocol):
    name: str

    def judge(self, context: JudgeContext) -> Judgement: ...


@dataclass
class AlwaysJudge:
    """A constant. The floors both metrics are read against."""

    answer: bool | None
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            label = {True: "false", False: "not-false", None: "unclear"}[self.answer]
            self.name = f"always-{label}"

    def judge(self, context: JudgeContext) -> Judgement:
        return Judgement(
            example_id=context.example_id,
            arm=context.arm,
            judge=self.name,
            answer=self.answer,
            reason="constant",
        )


@dataclass
class PriorJudge:
    """Coin flips at a fixed positive rate. One trial; the caller runs many.

    Seeded per trial rather than per call, and the id is mixed into the draw so that
    the same trial gives the same answer for the same case regardless of what order
    the cases arrive in -- otherwise a filtered subset would shift every draw after
    the filter point and two arms' controls would not be comparable.
    """

    rate: float
    seed: int = 0
    name: str = "prior"

    def judge(self, context: JudgeContext) -> Judgement:
        rng = random.Random(f"{self.seed}:{context.example_id}")
        return Judgement(
            example_id=context.example_id,
            arm=context.arm,
            judge=self.name,
            answer=rng.random() < self.rate,
            reason=f"prior p={self.rate:.3f} seed={self.seed}",
        )


@dataclass
class LexicalJudge:
    """Flag a doc that marks up an identifier absent from every code file shown.

    `literal_spans` first, so only backticked and fenced text counts. Bare English
    prose is what drowned the shape-B mining signal -- words like `stability` matched
    everywhere -- and a judge firing on those would be measuring the same noise.

    `min_missing` exists because a doc legitimately names identifiers that live in
    files other than the two or three retrieved: a threshold of 1 makes this fire on
    almost everything. Its default is a guess, and the eval sweeps it rather than
    trusting it, because a baseline tuned worse than it could be flatters whatever it
    is being compared against.
    """

    min_missing: int = 3
    name: str = "lexical-absence"

    def judge(self, context: JudgeContext) -> Judgement:
        marked = extract(literal_spans(context.doc_text), versions=False)
        present: set[str] = set()
        for code in context.code_files:
            present |= extract(code.text, versions=False)
        missing = sorted(marked - present)
        answer = len(missing) >= self.min_missing
        return Judgement(
            example_id=context.example_id,
            arm=context.arm,
            judge=self.name,
            answer=answer,
            claim=", ".join(missing[:6]) or None,
            reason=(
                f"{len(missing)} marked-up identifier(s) absent from the "
                f"{len(context.code_files)} code file(s) shown "
                f"(threshold {self.min_missing})"
            ),
        )


def _parse(text: str) -> tuple[bool | None, str | None, str | None, str, bool]:
    """Read a reply into a verdict. A reply that will not parse abstains loudly."""
    match = _JSON_RE.search(text)
    if not match:
        return None, None, None, text.strip()[:200], True
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, None, None, text.strip()[:200], True
    verdict = str(payload.get("verdict", "")).strip().lower()
    if verdict not in _VERDICT_TO_BOOL:
        return None, None, None, f"unrecognised verdict {verdict!r}", True
    claim = payload.get("claim")
    code = payload.get("code")
    return (
        _VERDICT_TO_BOOL[verdict],
        str(claim) if claim else None,
        str(code) if code else None,
        str(payload.get("reason", "")),
        False,
    )


class AnthropicJudge:
    """The model arm. Temperature 0, and every reply cached to disk.

    The cache is keyed by a hash of the rendered context, the prompt and the model
    rather than by `example_id`, so changing any of them re-asks instead of serving
    an answer from a harness that no longer exists. Temperature 0 does not make the
    API deterministic, which is exactly why the cache is on disk: without it, a
    re-run months later would silently produce a slightly different headline number
    and there would be no way to tell that from a real change.

    The SDK is imported inside `__init__`, so the module imports and the whole
    harness tests with no `anthropic` installed and no key set.
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_JUDGE_MODEL,
        cache_dir: Path | None = None,
        max_tokens: int = 700,
        system: str = SYSTEM_PROMPT,
        client=None,
    ) -> None:
        self.model = model
        self.system = system
        self.max_tokens = max_tokens
        self.name = f"model:{model}"
        self.cache_dir = cache_dir
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
        if client is not None:
            self._client = client
        else:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                # `floors` is a real `--judges` value, and it was not when this message
                # was written: it said to run `--judges floors` while argparse would
                # have rejected it. A false claim about the code, in the error path of a
                # tool for finding false claims about code, pinned by a test that
                # matched the word rather than checking the flag. See
                # `tests/test_judge_cli.py`, which now reads the parser.
                # The command is backticked so it is separable from the sentence around
                # it -- both for the reader pasting it and for the test parsing it. The
                # first attempt at that test read `--judges` to end-of-words and
                # captured "floors to get the" as flag values.
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Every other judge in this module "
                    "runs without it: `driftwood judge-eval --judges floors` gets the "
                    "floors, which is the half of the result that does not cost money, "
                    "and the half that makes the other half readable."
                )
            from anthropic import Anthropic  # imported late: optional dependency

            self._client = Anthropic()

    def _cache_path(self, key: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{key}.json"

    def judge(self, context: JudgeContext) -> Judgement:
        prompt = render(context)
        key = context_hash(context, self.system, self.model)
        path = self._cache_path(key)
        if path is not None and path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))["text"]
            answer, claim, code, reason, unparsed = _parse(raw)
            return Judgement(
                example_id=context.example_id, arm=context.arm, judge=self.name,
                answer=answer, claim=claim, code=code, reason=reason,
                unparsed=unparsed, cached=True,
            )

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0,
            system=self.system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        if path is not None:
            # Written before parsing, so a reply that will not parse is on disk to be
            # read by hand. An unparsed reply is the most informative failure here and
            # the easiest one to lose.
            path.write_text(
                json.dumps({"key": key, "model": self.model, "text": raw}, indent=2),
                encoding="utf-8",
            )
        answer, claim, code, reason, unparsed = _parse(raw)
        return Judgement(
            example_id=context.example_id, arm=context.arm, judge=self.name,
            answer=answer, claim=claim, code=code, reason=reason, unparsed=unparsed,
        )
