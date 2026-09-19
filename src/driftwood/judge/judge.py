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
from .claims import DEFAULT_BATCH, batch, claim_units
from .context import JudgeContext, context_hash, render, render_claim_batch

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

# The per-claim prompt. The falsity definition, the exclusion list and the invitation to
# abstain are WORD FOR WORD the ones above, and the duplication is deliberate on two
# counts. First, `SYSTEM_PROMPT` is hashed into the cache key, so factoring the shared text
# out into a constant that both prompts interpolate would change its bytes and re-pay every
# reply already bought -- roughly $6 of measurement history, to save twenty lines. Second
# and more important, this arm is supposed to move exactly ONE lever: the unit the question
# is asked about. If the definition of "false" drifted between the two prompts as well, a
# difference in the result could not be attributed to the unit, and the comparison against
# F1 0.364 would measure two changes at once. The two blocks must be kept identical by hand,
# and a test compares them rather than trusting that.
#
# What is genuinely different, and all of it follows from the unit:
#  - The claims are given, numbered, and the reply must carry the number back, so a short
#    reply cannot be silently misaligned against the wrong sentence.
#  - The page is NOT supplied. So the prompt says so, in the exclusion list, because a judge
#    that does not know the surrounding prose is missing is a judge that will guess at it.
#  - "unclear" now also covers "this sentence needs context I was not given", which is a
#    real and expected answer here and was not possible in the per-page arm.
CLAIM_SYSTEM_PROMPT = """\
You are reviewing a repository's documentation against its source code at one \
specific commit. You will be shown one or more code files as they exist at that \
commit, and then a numbered list of statements taken from one documentation file \
at the same commit.

For each numbered statement, answer one question: is it FALSE about the code as \
shown?

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

You are shown the statements only, not the page they came from, so the sentences \
around them are not available to you. A statement that reads as false but would be \
qualified by its surroundings is "unclear", not "false".

If the code needed to decide is not in front of you, answer "unclear". That is a \
real answer and is preferred over a guess.

Reply with a JSON array only, one object per numbered statement, in this exact \
shape and in the same order:

[{"n": 1,
  "verdict": "false" | "not-false" | "unclear",
  "code": "the code file and symbol that contradicts it, or null",
  "reason": "one sentence"}]
"""

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)
_VERDICT_TO_BOOL: dict[str, bool | None] = {
    "false": True,
    "not-false": False,
    "unclear": None,
}


@dataclass(frozen=True)
class ClaimVerdict:
    """One answer about one sentence, carrying the sentence so it can be located.

    `claim` is the unit as it was SENT, not as the model quoted it back. The per-page arm
    had to trust the quote, and 5 of its 7 false negatives quoted no claim at all; here the
    text is known before the call, so a verdict always has a locatable subject even when
    the reply is terse. That is the property the location-strict scoring needs, and it is
    the main thing this arm buys beyond a better number.
    """

    index: int  # 1-based, over the page's units, not within the batch
    claim: str
    answer: bool | None
    code: str | None = None
    reason: str = ""


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
    # The ceiling this reply was actually produced under, and whether that was a raised
    # one. Recorded because a run may legitimately mix ceilings -- a complete reply is
    # unaffected by a ceiling it never reached, so it is reused rather than re-paid --
    # and a mixed run has to be able to SAY it is mixed. Without these two fields the
    # reuse argument would be untestable from the output, which is the same as untrue.
    max_tokens_used: int | None = None
    retried: bool = False
    # Per-claim detail, empty for every judge that asks one question about a whole page.
    # The aggregate `answer` above is derived from these and is what gets scored, so this
    # is not a debug field: it is the evidence for the aggregate, and the only thing that
    # can say WHICH sentence a `false` was about.
    claim_verdicts: tuple[ClaimVerdict, ...] = ()
    # Calls actually made or read for this one case. 1 everywhere except the per-claim
    # arm, where a page of 85 units at 8 to a call is 11. Recorded because the run's cost
    # scales with this rather than with the number of cases, and a cost that is not
    # recorded is a cost that gets re-estimated wrongly later.
    calls: int = 1

    @property
    def abstained(self) -> bool:
        return self.answer is None

    @property
    def flagged(self) -> tuple[ClaimVerdict, ...]:
        """The claims this judgement says are false. Empty unless it is a per-claim one."""
        return tuple(v for v in self.claim_verdicts if v.answer is True)


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


@dataclass(frozen=True)
class _Reply:
    """One raw model reply, before anything decides what verdict it carries.

    Internal, and the boundary is chosen rather than incidental: everything here is a fact
    about the CALL -- what came back, at what ceiling, from cache or from the wire, and
    what it billed. Nothing here is a fact about documentation. That is what lets one
    implementation serve both a judge that asks about a page and a judge that asks about
    eight claims, without either one reimplementing the token ladder.
    """

    text: str
    stop_reason: str | None
    truncated: bool
    cached: bool
    ceiling: int
    retried: bool
    input_tokens: int | None
    output_tokens: int | None
    blocks: tuple[str, ...] = ()

    @property
    def truncation_reason(self) -> str:
        """What to put in a `reason` field when this reply never finished.

        Two wordings, because they are two different situations for the reader and were
        two separate messages before this class existed. A cached truncation at the top
        rung means the ladder is exhausted and the flag has to go higher; a fresh one
        means the flag has not been tried yet. Telling a reader to raise a flag they
        already raised is the kind of small lie that costs an hour.
        """
        blocks = ", ".join(self.blocks) or "none"
        if self.cached:
            return (
                f"TRUNCATED at {self.ceiling} tokens, the highest ceiling on the ladder "
                f"(blocks: {blocks}). Still a harness failure, not an abstention -- raise "
                "--retry-max-tokens further."
            )
        return (
            f"TRUNCATED: the reply hit the {self.ceiling}-token ceiling "
            f"(blocks: {blocks}). This is a harness failure, "
            "not an abstention -- raise --retry-max-tokens and re-run; only the "
            "truncated replies are re-paid for."
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
        retry_max_tokens: int | None = None,
        effort: str | None = None,
        system: str = SYSTEM_PROMPT,
        client=None,
    ) -> None:
        self.model = model
        self.system = system
        self.max_tokens = max_tokens
        # The ceiling a TRUNCATED reply is retried at, and the reason it exists is
        # arithmetic. `max_tokens` is inside the cache key, so raising it invalidates
        # every reply already paid for: fixing the 4 replies that hit the ceiling on the
        # 45-case seeded run would have re-paid the other 41 as well, ~$3 to repair
        # ~$0.25 of damage. On the 125-case retrieved arm the same mistake costs ~$6.
        #
        # What makes retrying only the truncated ones sound rather than a fudge is that
        # `max_tokens` is NOT a behavioural setting -- it is a ceiling. A reply that
        # stopped on `end_turn` after 1,800 tokens is byte-identical whether the ceiling
        # it never approached was 6,000 or 12,000, so reusing it alongside a retried
        # reply is not mixing two instruments. That holds only while every reply that DID
        # hit its ceiling gets re-requested, which is why `judge()` escalates rather than
        # reporting the truncated reply, and why the CLI counts both numbers out loud.
        self.retry_max_tokens = retry_max_tokens
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
        # Stored, not constructed. The client is built on the first cache MISS, which is
        # the first moment a key is actually needed, so a fully-cached run reads back
        # without credentials. That is not a convenience: the cache is the record of what
        # a paid run returned, this repository is public, and a result nobody can re-read
        # without a key of their own is a result on trust. It also makes the free
        # diagnostics in `scripts/` free in fact rather than just in intent.
        #
        # What this gives up is fail-fast. A keyless run now builds every context before
        # it discovers there is no key, instead of refusing at construction. That costs
        # seconds -- the builder's three caches make the whole 45-case build near
        # instant -- and `preflight()` is there for any caller that would rather know up
        # front. The CLI deliberately does not call it, because re-scoring a cached arm
        # is a thing to be able to do on a plane.
        self._client = client

    def preflight(self) -> None:
        """Construct the client now, so a missing key fails before any work is done."""
        self._ensure_client()

    def _ensure_client(self):
        if self._client is None:
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
        return self._client

    def _cache_path(self, key: str) -> Path | None:
        if self.cache_dir is None:
            return None
        return self.cache_dir / f"{key}.json"

    def _request(self, max_tokens: int | None = None) -> dict:
        """The call, minus the per-case parts. Also what goes into the cache key.

        Built in one place and used twice, so the request that was sent and the request
        the key was computed from cannot disagree. `effort` is omitted rather than sent
        as None, so that an unset effort hashes to the same key it did before the option
        existed and does not invalidate a cache for a setting nobody chose.

        `max_tokens` defaults to this judge's own ceiling. It is a parameter so the retry
        ladder can key and send a raised ceiling without building a second judge, and so
        that an unset argument reproduces the pre-retry key exactly.
        """
        request: dict = {"max_tokens": self.max_tokens if max_tokens is None else max_tokens}
        if self.effort is not None:
            request["output_config"] = {"effort": self.effort}
        return request

    def _ceilings(self) -> list[int]:
        """Token ceilings to consider, cheapest-cached first.

        Ascending, and deduplicated: a `--retry-max-tokens` at or below `--max-tokens`
        would otherwise add a second identical key and a second identical call.
        """
        ladder = [self.max_tokens]
        if self.retry_max_tokens and self.retry_max_tokens > self.max_tokens:
            ladder.append(self.retry_max_tokens)
        return ladder

    def _reply(self, context: JudgeContext, rendered: str) -> _Reply:
        """One reply for one rendered user turn: cache walk, escalation, send, record.

        Split out of `judge` so the per-claim judge can reuse every part of it that is
        about the API and the cache rather than about a verdict -- the ladder, the key, the
        write-before-parse, the usage accounting. It takes `rendered` rather than deriving
        it, because a per-claim call's user turn is a batch of claims and not the page.

        Everything below the parse is unchanged from when this was inline, deliberately:
        the ladder's correctness argument depends on the details (send at the HIGHEST
        ceiling, reuse a complete reply from any rung, never re-send a reply that already
        died at the top rung) and re-deriving them in a second place is how the two copies
        drift.
        """
        # Walk the ladder cheapest-first and reuse the first COMPLETE cached reply. A
        # truncated one is not a usable answer, so it does not stop the walk -- it is the
        # thing the next rung exists to replace.
        ceilings = self._ceilings()
        # Every rung whose cached reply died at its ceiling, not just the last one seen.
        # `retried` is then "a LOWER ceiling was tried and died", which is what the word
        # means and is not the same as "served above the base rung": a fresh case is sent
        # at the top rung and was never re-asked at all. Keyed by rung rather than kept as
        # a single value because both rungs can hold a truncation at once, and collapsing
        # them made a first-ever run at a raised ceiling report itself as a retry.
        truncated_cached: dict[int, dict] = {}

        def was_retried(at: int) -> bool:
            return any(rung < at for rung in truncated_cached)

        for ceiling in ceilings:
            key = context_hash(
                context, self.system, self.model,
                request=self._request(ceiling), rendered=rendered,
            )
            path = self._cache_path(key)
            if path is None or not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("stop_reason") == "max_tokens":
                truncated_cached[ceiling] = payload
                continue
            return _Reply(
                text=payload["text"],
                stop_reason=payload.get("stop_reason"),
                truncated=False, cached=True,
                ceiling=ceiling, retried=was_retried(ceiling),
                # `.get`, because entries written before usage was recorded have no
                # such key. Absent is reported as unknown, never as zero -- a missing
                # count summed as zero would make a cached run look free.
                input_tokens=payload.get("input_tokens"),
                output_tokens=payload.get("output_tokens"),
                blocks=tuple(payload.get("blocks") or ()),
            )

        # Nothing complete on disk. Send at the HIGHEST ceiling rather than the lowest,
        # and this is free rather than generous: output tokens are billed on what the
        # model actually produces, not on the ceiling it was allowed. A raised ceiling
        # costs nothing on a reply that stops early, so trying the low rung first would
        # only buy a second call for the hard cases.
        ceiling = ceilings[-1]
        request = self._request(ceiling)
        key = context_hash(
            context, self.system, self.model, request=request, rendered=rendered
        )
        path = self._cache_path(key)
        if ceiling in truncated_cached:
            # The top of the ladder is on disk and died there. Return it as truncated
            # rather than calling again: a second identical request would be paid for and
            # would hit the same ceiling. Raise --retry-max-tokens further.
            payload = truncated_cached[ceiling]
            return _Reply(
                text=payload["text"], stop_reason="max_tokens",
                truncated=True, cached=True,
                ceiling=ceiling, retried=was_retried(ceiling),
                input_tokens=payload.get("input_tokens"),
                output_tokens=payload.get("output_tokens"),
                blocks=tuple(payload.get("blocks") or ()),
            )

        # Every argument here is accepted by the installed SDK's signature, asserted
        # against it in the tests, because a stub client accepts arguments the API does
        # not. Nothing sampling-related is sent; see the class docstring.
        response = self._ensure_client().messages.create(
            model=self.model,
            system=self.system,
            messages=[{"role": "user", "content": rendered}],
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
        return _Reply(
            text=raw, stop_reason=stop_reason,
            truncated=stop_reason == "max_tokens", cached=False,
            ceiling=ceiling, retried=was_retried(ceiling),
            input_tokens=billed_in, output_tokens=billed_out,
            blocks=tuple(kinds),
        )

    def judge_page(self, context: JudgeContext) -> Judgement:
        """The per-page question. Named so the subclass can keep `judge` for its own."""
        reply = self._reply(context, render(context))
        answer, claim, code, reason, unparsed = _parse(reply.text)
        if reply.truncated:
            # Said in the reason field too, not just counted, because this is the line a
            # reader sees next to the case when they go looking for why it abstained.
            # Names the ceiling that was actually sent, not `self.max_tokens`, which is
            # the lowest rung and is not what this call used when the ladder escalated.
            reason = reply.truncation_reason
        return Judgement(
            example_id=context.example_id, arm=context.arm, judge=self.name,
            answer=answer, claim=claim, code=code, reason=reason, unparsed=unparsed,
            truncated=reply.truncated, stop_reason=reply.stop_reason,
            cached=reply.cached,
            max_tokens_used=reply.ceiling, retried=reply.retried,
            input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
        )

    # `judge` is the Judge protocol's method and stays the per-page one, so every existing
    # caller and every cached reply is untouched by the arrival of the subclass below.
    judge = judge_page


def _parse_claims(text: str, count: int) -> tuple[list[tuple[int, bool | None, str | None, str]], bool]:
    """Read a batch reply into `(n, answer, code, reason)` rows. Second value = unparsed.

    Two failures are possible here that the single-verdict parser cannot have, and both are
    handled by dropping rather than by guessing:

    - An item whose `n` is missing, not an integer, or outside 1..count is dropped. It
      cannot be aligned to a claim, and aligning it by position would attach a verdict to
      whichever sentence happened to be next -- a silent mislabel, which is worse than a
      missing one because every downstream number still computes.
    - A duplicate `n` keeps the FIRST and drops the rest, so a reply that answers claim 3
      twice cannot have its second answer overwrite its first depending on dict ordering.

    A reply short of `count` items is not an error here. The claims it did not answer become
    abstentions, counted and visible, which is the honest reading of a model that stopped.
    """
    match = _JSON_ARRAY_RE.search(text)
    if not match:
        return [], True
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], True
    if not isinstance(payload, list):
        return [], True
    rows: list[tuple[int, bool | None, str | None, str]] = []
    seen: set[int] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("n"))
        except (TypeError, ValueError):
            continue
        if not 1 <= number <= count or number in seen:
            continue
        verdict = str(item.get("verdict", "")).strip().lower()
        if verdict not in _VERDICT_TO_BOOL:
            continue
        seen.add(number)
        code = item.get("code")
        rows.append(
            (
                number,
                _VERDICT_TO_BOOL[verdict],
                str(code) if code else None,
                str(item.get("reason", "")),
            )
        )
    # Nothing alignable came back, from a reply that was valid JSON. That is a parse
    # failure in every sense that matters -- there is no verdict in it -- and calling it
    # anything else would score it as agreement with the page.
    return rows, not rows


class PerClaimJudge(AnthropicJudge):
    """Asks about the page's claims a batch at a time, instead of the page all at once.

    The measured reason this exists: the per-page judge returned `not-false` on a
    38,830-character page having reasoned only about its opening, with an empty `claim`
    field, and putting the cut sentence on screen flipped 0 of 3 such cases. More page did
    not get the claim read, so the question had to get smaller.

    Three properties worth stating before the number arrives, because they are what the
    arm is for rather than side effects:

    1. Every verdict has a located subject, known before the call rather than quoted back.
       The per-page arm's 7 false negatives include 5 that quoted no claim at all, which
       makes them unauditable; none of these can be.
    2. The page's tail is reachable. Units are enumerated from `doc_full`, so a claim at
       character 22,461 is asked about on equal terms with one at character 200.
    3. It can be scored two ways off the same replies -- aggregate, and restricted to the
       claims the fixing commit was actually about. The second is the construct-validity
       measurement this project has carried as an open problem since stage 3 began, and it
       needs a located verdict to exist at all.

    Costs and risks, stated with them: the page body is not in the prompt, so a sentence
    qualified by its neighbours can read as false, and precision should be expected to
    fall. A page with no marked-up prose sentence yields no units and abstains by
    construction. And the batch is a shared reply budget -- eight claims answered in one
    6,000-token ceiling -- so truncation here loses up to eight verdicts rather than one,
    which is why `calls` and the truncation count are reported per case.
    """

    def __init__(self, *, batch_size: int = DEFAULT_BATCH, **kwargs) -> None:
        kwargs.setdefault("system", CLAIM_SYSTEM_PROMPT)
        super().__init__(**kwargs)
        if batch_size < 1:
            raise ValueError(f"batch size must be at least 1, got {batch_size}")
        self.batch_size = batch_size
        # The batch size is in the name because it is part of the experiment and two
        # settings must not collide in one results file -- the same reason the lexical
        # judge carries its threshold. It is NOT separately in the cache key and does not
        # need to be: it decides which claims share a user turn, so it is already visible
        # in the rendered text the key is computed over.
        self.name = f"per-claim/{batch_size}:{self.model}" + (
            f"({self.effort})" if self.effort else ""
        )

    def judge(self, context: JudgeContext) -> Judgement:
        # From the UNTRUNCATED page. Enumerating from `doc_text` would reinstate the exact
        # failure this arm exists to fix; see `JudgeContext.doc_full`.
        units = claim_units(context.doc_full or context.doc_text)
        if not units:
            return Judgement(
                example_id=context.example_id, arm=context.arm, judge=self.name,
                answer=None, calls=0,
                reason=(
                    f"no claim unit on this page ({len(context.doc_full)} chars): no prose "
                    "sentence marks up an identifier, so there was nothing to ask about. "
                    "An abstention by construction, not by judgement -- the per-page judge "
                    "would at least have been shown this page."
                ),
            )

        verdicts: list[ClaimVerdict] = []
        truncated = False
        unparsed_batches = 0
        billed_in = billed_out = 0
        usage_seen = False
        cached_all = True
        retried_any = False
        ceiling_used: int | None = None
        calls = 0

        for offset, group in enumerate(batch(units, self.batch_size)):
            rendered = render_claim_batch(context, group)
            reply = self._reply(context, rendered)
            calls += 1
            cached_all = cached_all and reply.cached
            retried_any = retried_any or reply.retried
            ceiling_used = reply.ceiling
            if reply.input_tokens is not None:
                billed_in += reply.input_tokens
                usage_seen = True
            if reply.output_tokens is not None:
                billed_out += reply.output_tokens
                usage_seen = True
            rows, failed = _parse_claims(reply.text, len(group))
            if reply.truncated:
                truncated = True
            if failed:
                unparsed_batches += 1
            answered = {number: (answer, code, why) for number, answer, code, why in rows}
            base = offset * self.batch_size
            for position, claim in enumerate(group, start=1):
                answer, code, why = answered.get(
                    position,
                    (
                        None,
                        None,
                        reply.truncation_reason if reply.truncated
                        else "no verdict for this claim in the batch reply",
                    ),
                )
                verdicts.append(
                    ClaimVerdict(
                        index=base + position, claim=claim,
                        answer=answer, code=code, reason=why,
                    )
                )

        flagged = [v for v in verdicts if v.answer is True]
        decided = [v for v in verdicts if v.answer is not None]
        # Any-claim-false. One false sentence makes the page false about the code, which is
        # what the corpus label means: the fixing commit corrected something. The
        # alternative -- a majority, or a count threshold -- would be a second lever moving
        # at the same time as the unit, and there is no measurement to justify one.
        if flagged:
            answer: bool | None = True
        elif decided:
            answer = False
        else:
            answer = None
        return Judgement(
            example_id=context.example_id, arm=context.arm, judge=self.name,
            answer=answer,
            claim=flagged[0].claim if flagged else None,
            code=flagged[0].code if flagged else None,
            reason=(
                f"{len(flagged)} of {len(verdicts)} claim(s) false, "
                f"{len(decided) - len(flagged)} not-false, "
                f"{len(verdicts) - len(decided)} undecided, over {calls} call(s)"
                + (f"; {unparsed_batches} batch reply/replies unreadable" if unparsed_batches else "")
                + (f". {flagged[0].reason}" if flagged else "")
            ),
            # A batch that would not parse is an abstention on its claims, and the run has
            # to be able to say so -- but it is only reported as an unparsed JUDGEMENT when
            # it cost the case its whole answer. A page where 1 of 11 batches failed still
            # has an answer, and flagging the case as unparsed would overstate the damage.
            unparsed=unparsed_batches > 0 and answer is None,
            truncated=truncated,
            stop_reason="max_tokens" if truncated else None,
            cached=cached_all,
            max_tokens_used=ceiling_used, retried=retried_any,
            input_tokens=billed_in if usage_seen else None,
            output_tokens=billed_out if usage_seen else None,
            claim_verdicts=tuple(verdicts),
            calls=calls,
        )
