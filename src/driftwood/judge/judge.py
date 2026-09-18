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
    "DEFAULT_MAX_TOKENS",
    "AlwaysJudge",
    "AnthropicJudge",
    "Judge",
    "Judgement",
    "LexicalJudge",
    "PriorJudge",
    "SYSTEM_PROMPT",
]

# The reply budget, and it is NOT the size of the answer. It was 700, sized by reading
# the prompt -- a verdict, a quoted claim, two sentences -- and 700 is about four times
# what the answer actually needs. It still truncated 16 of 45 replies, because reasoning
# tokens are billed and budgeted as output: on the largest prompt the model spent 4,169
# tokens thinking before writing 471 characters of answer, and a response can come back
# as a single `thinking` block with no answer in it at all.
#
# Worse, the truncation was not random. Reasoning scales with how hard the case is, so
# the 16 that died were the 16 LARGEST prompts, and 11 of the 13 real drift cases were
# among them. An instrument that fails on the hard cases and succeeds on the easy ones
# does not add noise, it manufactures a result -- the model arm scored F1 0.00 with a
# 71% abstention rate, which read as a judge with no signal rather than as a budget.
#
# 6000 is the measured 4,640-token worst case plus headroom, not a guess. The floor
# under it is the observation that the 29 replies that did fit averaged 329 tokens:
# reasoning is adaptive, so a ceiling this high is paid for only on the cases that
# need it.
DEFAULT_MAX_TOKENS = 6000

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
    # The reply hit the token ceiling, so there was no answer to parse. A DIFFERENT
    # failure from `unparsed` and separated from it on purpose: `unparsed` says the
    # model answered something unreadable, `truncated` says the harness did not let it
    # answer. Folding the second into the first is how a budget mistake gets reported
    # as a judge with no signal. Counted, warned about, and never silent.
    truncated: bool = False
    stop_reason: str | None = None
    cached: bool = False
    # What the provider said it billed, when there was a provider. None for the free
    # judges, and None for a reply cached before this field existed. Kept so the
    # pre-run estimate can be checked against the outcome rather than believed.
    input_tokens: int | None = None
    output_tokens: int | None = None

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
    """The model arm. Every reply cached to disk, and no sampling controls at all.

    There is no `temperature=0` here, and that is not an oversight. This first ran
    against `anthropic` 1.7.0, whose `Messages.create` does not accept `temperature`:
    that generation of the API dropped the sampling knobs, and what replaced them
    (`output_config`) governs effort and response format rather than randomness. The
    call carried `temperature=0` for as long as it did only because every test here
    drove it through a stub whose `create(**kwargs)` accepted anything -- so the one
    argument the real SDK would reject was the one nothing checked. A fake more
    permissive than the interface it stands in for cannot fail. See
    `TestTheCallMatchesTheInstalledSDK` in `tests/test_judge_scoring.py`.

    Losing temperature costs this harness nothing, because it never had determinism
    to lose: temperature 0 was never a promise of an identical reply. The disk cache
    was always the reproducibility mechanism rather than a speed-up, and it is now
    the only one. Without it a re-run months later would quietly produce a slightly
    different headline number, indistinguishable from a real change.

    The cache is keyed by a hash of the rendered context, the prompt and the model
    rather than by `example_id`, so changing any of those re-asks instead of serving
    an answer from a harness that no longer exists. The key does NOT cover the rest
    of the request, so a later change to the call shape -- an `output_config.format`
    that forces valid JSON, say -- would serve pre-change replies until the key grows
    to include it. Not a problem today because the cache was empty when temperature
    came out, and recorded here so that stays a decision rather than a surprise.

    The SDK is imported inside `__init__`, so the module imports and the whole
    harness tests with no `anthropic` installed and no key set.
    """

    def __init__(
        self,
        *,
        model: str = DEFAULT_JUDGE_MODEL,
        cache_dir: Path | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        effort: str | None = None,
        system: str = SYSTEM_PROMPT,
        client=None,
    ) -> None:
        self.model = model
        self.system = system
        self.max_tokens = max_tokens
        # None means "whatever the API does by default", which is what the first run
        # measured. Left unset rather than pinned to a value, because a default is the
        # honest thing to report a judge's behaviour at -- and because the one
        # measurement of `low` came back with a generic answer where the default named
        # the two specific symbols it had checked. That is a real dimension to sweep,
        # not a setting to quietly choose: see the plan file.
        self.effort = effort
        self.name = f"model:{model}" + (f"({effort})" if effort else "")
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
            try:
                from anthropic import Anthropic  # imported late: optional dependency
            except ImportError as exc:  # pragma: no cover - exercised via the message test
                # A bare ModuleNotFoundError here is a dead end for the reader, and it
                # arrives at the worst moment: key set, run started, nothing said about
                # the one command that fixes it. The extra name is asserted against
                # pyproject.toml in tests, so this cannot name an extra that does not
                # exist -- the mistake the no-key message made with --judges floors.
                raise RuntimeError(
                    "the anthropic SDK is not installed. It is an optional extra, "
                    "because the floors deliberately need neither it nor a key: run "
                    "`uv sync --extra judge` and try again."
                ) from exc

            self._client = Anthropic()

    def _cache_path(self, key: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{key}.json"

    def _request(self) -> dict:
        """The call, minus the per-case parts. Also what goes into the cache key.

        Built in one place and used twice, so the request that was sent and the request
        the key was computed from cannot disagree. `effort` is omitted rather than sent
        as None, so that an unset effort hashes to the same key it did before the option
        existed and does not invalidate a cache for a setting nobody chose.
        """
        request: dict = {"max_tokens": self.max_tokens}
        if self.effort is not None:
            request["output_config"] = {"effort": self.effort}
        return request

    def judge(self, context: JudgeContext) -> Judgement:
        prompt = render(context)
        request = self._request()
        key = context_hash(context, self.system, self.model, request=request)
        path = self._cache_path(key)
        if path is not None and path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw = payload["text"]
            answer, claim, code, reason, unparsed = _parse(raw)
            stop_reason = payload.get("stop_reason")
            return Judgement(
                example_id=context.example_id, arm=context.arm, judge=self.name,
                answer=answer, claim=claim, code=code, reason=reason,
                unparsed=unparsed, cached=True,
                truncated=stop_reason == "max_tokens", stop_reason=stop_reason,
                # `.get`, because entries written before usage was recorded have no
                # such key. Absent is reported as unknown, never as zero -- a missing
                # count summed as zero would make a cached run look free.
                input_tokens=payload.get("input_tokens"),
                output_tokens=payload.get("output_tokens"),
            )

        # Every argument here is accepted by the installed SDK's signature, asserted
        # against it in the tests, because a stub client accepts arguments the API does
        # not. Nothing sampling-related is sent; see the class docstring.
        response = self._client.messages.create(
            model=self.model,
            system=self.system,
            messages=[{"role": "user", "content": prompt}],
            **request,
        )
        blocks = list(getattr(response, "content", []) or [])
        kinds = [getattr(block, "type", "?") for block in blocks]
        raw = "".join(
            block.text for block in blocks if getattr(block, "type", "") == "text"
        )
        stop_reason = getattr(response, "stop_reason", None)
        usage = getattr(response, "usage", None)
        billed_in = getattr(usage, "input_tokens", None)
        billed_out = getattr(usage, "output_tokens", None)
        if path is not None:
            # Written before parsing, so a reply that will not parse is on disk to be
            # read by hand -- the most informative failure here and the easiest to lose.
            #
            # `stop_reason` and `blocks` are recorded because for 16 replies this file
            # held `"text": ""` and nothing else, and an empty string is the one value
            # that explains nothing: a refusal, a network oddity and a budget exhausted
            # by reasoning all look identical. They were in fact a single `thinking`
            # block and `stop_reason: max_tokens`, which is diagnosable in one glance
            # and was thrown away by filtering the response before recording it. The
            # raw reply is what gets kept; `text` is a view of it.
            path.write_text(
                json.dumps(
                    {
                        "key": key, "model": self.model, "text": raw,
                        "blocks": kinds, "stop_reason": stop_reason,
                        "request": request,
                        "input_tokens": billed_in, "output_tokens": billed_out,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        answer, claim, code, reason, unparsed = _parse(raw)
        if stop_reason == "max_tokens":
            # Said in the reason field too, not just counted, because this is the line a
            # reader sees next to the case when they go looking for why it abstained.
            reason = (
                f"TRUNCATED: the reply hit the {self.max_tokens}-token ceiling "
                f"(blocks: {', '.join(kinds) or 'none'}). This is a harness failure, "
                "not an abstention -- raise --max-tokens and re-run."
            )
        return Judgement(
            example_id=context.example_id, arm=context.arm, judge=self.name,
            answer=answer, claim=claim, code=code, reason=reason, unparsed=unparsed,
            truncated=stop_reason == "max_tokens", stop_reason=stop_reason,
            input_tokens=billed_in, output_tokens=billed_out,
        )
