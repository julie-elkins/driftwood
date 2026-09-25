"""The judges and the scoring, with the floors pinned to arithmetic done by hand.

The floor numbers are asserted as literals rather than computed from the corpus,
because a floor recomputed from whatever the corpus currently is cannot detect the
corpus changing -- which is the one thing that would make a stage-3 result
incomparable to the pre-registration.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

from driftwood.judge.cases import JudgeCase, load_cases
from driftwood.judge.context import CodeFile, JudgeContext, context_hash
from driftwood.judge.evaluate import (
    abstention_calibration,
    confusion,
    format_results,
    noise_range,
    score,
    to_json,
)
from driftwood.judge.judge import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_TOKENS,
    MAX_NONSTREAMING_MAX_TOKENS,
    SYSTEM_PROMPT,
    AlwaysJudge,
    AnthropicJudge,
    Judgement,
    LexicalJudge,
    PriorJudge,
    _parse,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _case(example_id: str, verdict: str, **overrides) -> JudgeCase:
    base = dict(
        example_id=example_id, repo="acme/widget", shape="B", basis="b",
        doc_path="docs/x.rst", code_path=None, at_sha="a", fix_sha="f",
        subject="s", shared_identifiers=(), verdict=verdict, sheet="s.md",
        resolved_from="labels.jsonl",
    )
    base.update(overrides)
    return JudgeCase(**base)  # type: ignore[arg-type]


def _context(example_id: str = "x", doc: str = "docs", code: str = "code") -> JudgeContext:
    return JudgeContext(
        example_id=example_id, repo="acme/widget", arm="oracle", doc_path="docs/x.rst",
        doc_text=doc, doc_truncated=False, at_sha="a",
        code_files=(CodeFile("src/c.py", code, False, None),), pool_size=1,
    )


def _judgements(judge, cases) -> dict[str, Judgement]:
    return {c.example_id: judge.judge(_context(c.example_id)) for c in cases}


class TestTheConstantFloors:
    """Both constants, because each one is the floor for a different metric."""

    def test_always_not_false_scores_the_majority_rate_at_zero_f1(self):
        cases = [_case(f"p{i}", "drift") for i in range(30)] + [
            _case(f"n{i}", "cosmetic") for i in range(70)
        ]
        got = score(cases, _judgements(AlwaysJudge(False), cases))
        assert got.accuracy_all == pytest.approx(0.70)
        assert got.f1 == 0.0
        assert got.recall == 0.0

    def test_always_false_scores_a_respectable_looking_f1(self):
        # 0.44 is the number that makes an unqualified "our judge scores F1 0.40"
        # meaningless. A stuck switch beats it.
        cases = [_case(f"p{i}", "drift") for i in range(30)] + [
            _case(f"n{i}", "cosmetic") for i in range(70)
        ]
        got = score(cases, _judgements(AlwaysJudge(True), cases))
        assert got.accuracy_all == pytest.approx(0.30)
        assert got.recall == 1.0
        assert got.f1 == pytest.approx(0.4615, abs=0.001)

    def test_the_preregistered_floors_on_the_real_corpus(self):
        data = REPO_ROOT / "data"
        if not (data / "labels.jsonl").exists():
            pytest.skip("mined labels not present")
        cases, _ = load_cases(REPO_ROOT / "review", data)

        # Both floors MOVED when `shape-A-batch-03.md` was labelled, and again when
        # `shape-A-batch-04-v11.md` was: the always-drift F1 went 0.444 -> 0.415 -> 0.458 on
        # 105 -> 130 -> 155 scoreable. Every stage-3 F1 in the README was quoted against
        # 0.444. A judge that scored 0.43 was below the first floor, above the second, and is
        # below the third, so this is not bookkeeping -- the scores in
        # `data/scores/judge-*.json` were measured on the 105-case corpus and are not
        # comparable to anything run from here on without re-scoring.
        #
        # AND THE FLOOR DOES NOT MOVE MONOTONICALLY. It fell, then rose past where it
        # started. A reader who extrapolated the first move would have been wrong about the
        # second, which is why the literal is pinned here rather than derived from the corpus.
        low = score(cases, _judgements(AlwaysJudge(False), cases))
        assert low.n == 155
        assert low.accuracy_all == pytest.approx(0.703, abs=0.001)
        assert low.f1 == 0.0

        high = score(cases, _judgements(AlwaysJudge(True), cases))
        assert high.accuracy_all == pytest.approx(0.297, abs=0.001)
        assert high.f1 == pytest.approx(0.458, abs=0.001)

    def test_a_held_out_case_is_never_scored(self):
        cases = [_case("u1", "unclear"), _case("p1", "drift")]
        got = score(cases, _judgements(AlwaysJudge(True), cases))
        assert got.n == 1


class TestAbstentionIsNotAQuietNegative:
    def test_an_abstention_is_counted_as_neither_right_nor_wrong(self):
        cases = [_case("p1", "drift"), _case("n1", "cosmetic")]
        got = score(cases, _judgements(AlwaysJudge(None), cases))
        assert (got.tp, got.fp, got.fn, got.tn) == (0, 0, 0, 0)
        assert got.abstained == 2
        assert got.answered == 0

    def test_abstaining_inflates_accuracy_on_answered_and_not_overall(self):
        # The whole reason both are printed. A judge that abstains on everything it
        # would get wrong looks perfect on one column and terrible on the other.
        cases = [_case("p1", "drift"), _case("n1", "cosmetic"), _case("n2", "cosmetic")]
        judgements = {
            "p1": Judgement("p1", "oracle", "j", True),
            "n1": Judgement("n1", "oracle", "j", None),
            "n2": Judgement("n2", "oracle", "j", None),
        }
        got = score(cases, judgements)
        assert got.accuracy_answered == pytest.approx(1.0)
        assert got.accuracy_all == pytest.approx(1 / 3)

    def test_an_unparsed_reply_is_an_abstention_and_is_counted_separately(self):
        cases = [_case("n1", "cosmetic")]
        judgements = {"n1": Judgement("n1", "oracle", "j", None, unparsed=True)}
        got = score(cases, judgements)
        assert got.unparsed == 1
        assert got.tn == 0  # free credit on a negative is exactly what this prevents

    def test_a_case_with_no_judgement_leaves_the_denominator(self):
        cases = [_case("p1", "drift"), _case("p2", "drift")]
        got = score(cases, {"p1": Judgement("p1", "oracle", "j", True)})
        assert got.n == 1


class TestAbstentionCalibration:
    def test_abstaining_equally_everywhere_has_no_lift(self):
        cases = [_case(f"u{i}", "unclear") for i in range(4)] + [
            _case(f"n{i}", "cosmetic") for i in range(4)
        ]
        judgements = {c.example_id: Judgement(c.example_id, "o", "j", None) for c in cases}
        got = abstention_calibration(cases, judgements)
        assert got["lift"] == pytest.approx(1.0)

    def test_abstaining_only_where_julie_could_not_tell_shows_lift(self):
        cases = [_case(f"u{i}", "unclear") for i in range(4)] + [
            _case(f"n{i}", "cosmetic") for i in range(4)
        ]
        judgements = {
            c.example_id: Judgement(
                c.example_id, "o", "j", None if c.verdict == "unclear" else False
            )
            for c in cases
        }
        got = abstention_calibration(cases, judgements)
        assert got["held_out_rate"] == 1.0
        assert got["scoreable_rate"] == 0.0
        assert got["lift"] == 0.0  # undefined denominator, reported as 0 not as inf

    def test_no_held_out_cases_does_not_divide_by_zero(self):
        cases = [_case("n1", "cosmetic")]
        got = abstention_calibration(cases, {"n1": Judgement("n1", "o", "j", False)})
        assert got["held_out"] == 0


class TestThePriorControl:
    def test_the_same_seed_and_id_give_the_same_draw(self):
        a = PriorJudge(rate=0.3, seed=7).judge(_context("abc"))
        b = PriorJudge(rate=0.3, seed=7).judge(_context("abc"))
        assert a.answer == b.answer

    def test_a_draw_does_not_depend_on_what_came_before_it(self):
        # Seeding a single RNG and drawing in sequence would make a filtered subset
        # shift every draw after the filter point, so two arms scored on different
        # case sets would not share a control.
        judge = PriorJudge(rate=0.5, seed=1)
        alone = judge.judge(_context("target")).answer
        for other in ("a", "b", "c"):
            judge.judge(_context(other))
        assert judge.judge(_context("target")).answer == alone

    def test_the_noise_range_brackets_the_chance_f1_and_has_width(self):
        cases = [_case(f"p{i}", "drift") for i in range(30)] + [
            _case(f"n{i}", "cosmetic") for i in range(75)
        ]
        available = {c.example_id for c in cases}
        got = noise_range(cases, available, trials=60)
        low, mid, high = got["f1"]
        # A coin at the base rate gets precision ~= the base rate and recall ~= the
        # base rate, so F1 lands near 0.286 -- well above the 0.00 of the majority
        # constant. Any judge claiming a win has to clear this, not that.
        assert 0.15 < mid < 0.45
        assert high > low, "a control with no width is not a control"

    def test_the_default_rate_is_the_corpus_rate_not_a_coin(self):
        cases = [_case("p1", "drift")] + [_case(f"n{i}", "cosmetic") for i in range(9)]
        available = {c.example_id for c in cases}
        weighted = noise_range(cases, available, trials=60)
        fair = noise_range(cases, available, trials=60, rate=0.5)
        # At a 10% positive rate a fair coin flags five times too often, so its
        # accuracy is much worse. Using it would flatter every real judge.
        assert weighted["accuracy_all"][1] > fair["accuracy_all"][1]


class TestTheLexicalBaseline:
    def test_it_fires_when_the_doc_marks_up_absent_identifiers(self):
        doc = "Call ``connect_widget`` and ``flush_widget`` and ``reset_widget``."
        judge = LexicalJudge(min_missing=3)
        got = judge.judge(_context(doc=doc, code="def unrelated():\n    pass\n"))
        assert got.answer is True
        assert got.claim

    def test_it_stays_quiet_when_the_identifiers_are_present(self):
        doc = "Call ``connect_widget`` and ``flush_widget`` and ``reset_widget``."
        code = "def connect_widget(): ...\ndef flush_widget(): ...\ndef reset_widget(): ...\n"
        assert LexicalJudge(min_missing=3).judge(_context(doc=doc, code=code)).answer is False

    def test_unmarked_prose_is_not_read_as_an_identifier(self):
        # English prose is what drowned the shape-B mining signal. A baseline firing
        # on it would be measuring the same noise the miner had to be taught to
        # ignore, and it would look like a strong baseline while doing so.
        doc = "This guarantees stability and reliability across every supported release."
        assert LexicalJudge(min_missing=1).judge(_context(doc=doc, code="x = 1\n")).answer is False

    def test_the_threshold_changes_the_answer(self):
        doc = "See ``only_one_absent_thing``."
        low = LexicalJudge(min_missing=1).judge(_context(doc=doc, code="y = 2\n"))
        high = LexicalJudge(min_missing=6).judge(_context(doc=doc, code="y = 2\n"))
        assert low.answer is True and high.answer is False


class TestReadingAModelsReply:
    def test_a_clean_json_reply(self):
        answer, claim, code, reason, unparsed = _parse(
            '{"verdict": "false", "claim": "timeout is 5", "code": "c.py:DEFAULT",'
            ' "reason": "it is 30"}'
        )
        assert answer is True and not unparsed
        assert claim == "timeout is 5" and code == "c.py:DEFAULT"
        assert reason == "it is 30"

    def test_json_wrapped_in_prose_or_a_fence(self):
        answer, *_ , unparsed = _parse(
            'Here is my answer:\n```json\n{"verdict": "not-false", "claim": null,'
            ' "code": null, "reason": "matches"}\n```\nHope that helps.'
        )
        assert answer is False and not unparsed

    def test_unclear_parses_to_an_abstention_not_to_a_negative(self):
        answer, *_, unparsed = _parse('{"verdict": "unclear", "reason": "no code"}')
        assert answer is None and not unparsed

    def test_prose_with_no_json_abstains_loudly(self):
        answer, claim, code, reason, unparsed = _parse("I think the docs look fine.")
        assert answer is None and unparsed
        assert "docs look fine" in reason  # the raw reply is kept, to read by hand

    def test_a_verdict_outside_the_vocabulary_abstains_loudly(self):
        # "probably-false" becoming "not-false" would be the worst available default:
        # it would earn credit on 96 of 130 cases for free.
        answer, _, _, reason, unparsed = _parse('{"verdict": "probably-false"}')
        assert answer is None and unparsed
        assert "probably-false" in reason

    def test_malformed_json_abstains_loudly(self):
        answer, *_, unparsed = _parse('{"verdict": "false",,}')
        assert answer is None and unparsed


class _StubClient:
    """Counts calls, so a cache hit is observable rather than assumed.

    `stop_reason` and `block_type` exist so the truncated-reply path can be exercised
    without spending anything. The real shape of that failure, observed: one block of
    type `thinking` whose content is empty, and `stop_reason: max_tokens`.
    """

    def __init__(
        self, reply: str, *, stop_reason: str = "end_turn", block_type: str = "text"
    ) -> None:
        self.reply = reply
        self.calls: list[dict] = []
        self.messages = self
        self._stop_reason = stop_reason
        self._block_type = block_type

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outer = self

        class _Block:
            type = outer._block_type
            text = outer.reply if outer._block_type == "text" else ""

        class _Response:
            content = [_Block()]
            stop_reason = outer._stop_reason

        return _Response()


class TestTheModelArm:
    def test_it_asks_with_the_versioned_prompt(self, tmp_path):
        # This used to assert `calls[0]["temperature"] == 0`, and passed, against an
        # SDK with no such parameter. What the request may contain is now checked
        # against the real signature in `TestTheCallMatchesTheInstalledSDK`; what it
        # must contain is checked here.
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        got = judge.judge(_context("c1"))
        assert got.answer is True
        assert client.calls[0]["system"] == SYSTEM_PROMPT

    def test_a_second_ask_comes_from_the_cache(self, tmp_path):
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        judge.judge(_context("c1"))
        again = judge.judge(_context("c1"))
        assert len(client.calls) == 1
        assert again.cached is True

    def test_a_changed_prompt_re_asks(self, tmp_path):
        # There is no temperature to pin, so the disk cache is the only thing making a
        # re-run reproducible -- and that is only safe if a changed harness invalidates
        # it, which is what this checks.
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        AnthropicJudge(client=client, cache_dir=tmp_path, model="m").judge(_context("c1"))
        AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", system="a different prompt"
        ).judge(_context("c1"))
        assert len(client.calls) == 2

    def test_a_changed_document_re_asks(self, tmp_path):
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        judge.judge(_context("c1", doc="one"))
        judge.judge(_context("c1", doc="two"))
        assert len(client.calls) == 2

    def test_an_unparsed_reply_is_still_written_to_disk(self, tmp_path):
        # The most informative failure and the easiest one to lose: without this the
        # only record of what the model actually said is a count.
        client = _StubClient("I am not going to answer in JSON.")
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        got = judge.judge(_context("c1"))
        assert got.unparsed
        written = list(tmp_path.glob("*.json"))
        assert len(written) == 1
        assert "not going to answer" in json.loads(written[0].read_text())["text"]

    def test_no_key_and_no_client_refuses_rather_than_scoring_nothing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError):
            AnthropicJudge().judge(_context("c1"))
        # This used to assert `match="floors"`, which passed while the message named a
        # flag value argparse rejected. Whether the suggested command is runnable is
        # checked against the parser in `tests/test_judge_cli.py`; matching prose
        # against prose is what let the false instruction through.

    def test_a_cached_reply_is_readable_with_no_key_at_all(self, tmp_path, monkeypatch):
        """The record of a paid run must be re-readable by someone who has no key.

        This repository is public and the replies are what every stage-3 number is
        computed from, so a cache that can only be read by the person who paid for it
        makes the result something you take on trust. It is also what lets the free
        diagnostics in `scripts/` be free in fact: the abstention audit reads 45 replies
        off disk, and it could not be run without a key while the client was built in
        `__init__`.
        """
        # Populate the cache with a client, exactly as a paid run would.
        warm = AnthropicJudge(client=_StubClient('{"verdict": "false", "claim": "c", '
                                                '"code": "d", "reason": "r"}'),
                              cache_dir=tmp_path, model="m")
        first = warm.judge(_context("c1"))
        assert first.answer is True and not first.cached

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cold = AnthropicJudge(cache_dir=tmp_path, model="m")
        again = cold.judge(_context("c1"))
        assert again.cached is True
        assert again.answer is True

    def test_a_miss_with_no_key_still_refuses_rather_than_answering(self, tmp_path,
                                                                   monkeypatch):
        # The other half of the same change, and the one that would be a silent hole:
        # laziness must not turn a missing key into a quiet abstention on every case.
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cold = AnthropicJudge(cache_dir=tmp_path, model="m")
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            cold.judge(_context("never-cached"))


class TestARunOutOfBudgetIsNotAnAbstention:
    """The failure that made the first real model arm unreadable, pinned.

    A 700-token reply budget covered the answer four times over and still truncated 16
    of 45 replies, because reasoning tokens come out of the same budget: the response
    arrived as a single empty `thinking` block with `stop_reason: max_tokens`. Every one
    was scored as an abstention, so the arm reported F1 0.00 at a 71% abstention rate --
    which reads as a judge with no signal, and was a harness with no room.

    What makes it worth a test class rather than a bigger number: truncation scales with
    prompt length, prompt length scales with document size, and the hard cases are the
    long ones. 11 of the 13 real drift cases were among the 16. An instrument that fails
    on the positives and succeeds on the negatives does not add noise to a result, it
    manufactures one.
    """

    def _truncated(self, tmp_path):
        client = _StubClient("", stop_reason="max_tokens", block_type="thinking")
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        return judge.judge(_context("c1"))

    def test_it_is_flagged_as_truncated_and_says_so_in_the_reason(self, tmp_path):
        got = self._truncated(tmp_path)
        assert got.truncated is True
        assert got.answer is None
        assert got.stop_reason == "max_tokens"
        # The reason field, not just a counter: this is the line a reader sees next to
        # the case when they go looking for why it abstained.
        assert "TRUNCATED" in got.reason
        # It used to say "raise --max-tokens and re-run", which was true and expensive:
        # `max_tokens` is inside the cache key, so that advice re-pays every reply already
        # bought to repair the few that truncated. The advice now names the retry ceiling.
        assert "--retry-max-tokens" in got.reason

        # And the flag it names has to exist, which is this project's own recurring bug:
        # the no-key message told readers to run `--judges floors` while argparse rejected
        # it, and the test covering that message asserted the word rather than the flag.
        # Read the parser instead of trusting the sentence.
        import argparse

        from driftwood.judge.cli import add_parser

        parser = argparse.ArgumentParser(prog="driftwood")
        add_parser(parser.add_subparsers(dest="command"))
        for flag in re.findall(r"--[a-z-]+", got.reason):
            parser.parse_args(["judge-eval", flag, "1"])

    def test_the_evidence_survives_on_disk(self, tmp_path):
        # The cache held `"text": ""` and nothing else for all 16, and an empty string is
        # the one value that explains nothing -- a refusal, a network oddity and an
        # exhausted budget all look identical. The block types and the stop reason are
        # what turn it into a one-glance diagnosis.
        self._truncated(tmp_path)
        written = json.loads(next(iter(tmp_path.glob("*.json"))).read_text())
        assert written["stop_reason"] == "max_tokens"
        assert written["blocks"] == ["thinking"]
        assert written["request"]["max_tokens"] == DEFAULT_MAX_TOKENS

    def test_a_cached_truncation_is_still_flagged(self, tmp_path):
        # Otherwise the flag lasts exactly one run and the second one silently reports
        # 16 clean abstentions.
        self._truncated(tmp_path)
        again = AnthropicJudge(
            client=_StubClient("never reached"), cache_dir=tmp_path, model="m"
        ).judge(_context("c1"))
        assert again.cached and again.truncated

    def test_the_scores_count_it_apart_from_other_unparsed_replies(self):
        cases = [_case("p1", "drift"), _case("p2", "drift")]
        judgements = {
            "p1": Judgement(
                example_id="p1", arm="oracle", judge="model:m", answer=None,
                unparsed=True, truncated=True, stop_reason="max_tokens",
            ),
            "p2": Judgement(
                example_id="p2", arm="oracle", judge="model:m", answer=None,
                unparsed=True, reason="answered in prose",
            ),
        }
        got = score(cases, judgements)
        assert got.unparsed == 2
        assert got.truncated == 1  # the harness's fault, separated from the model's

    def test_the_report_refuses_to_present_it_as_a_result(self):
        cases = [_case("p1", "drift")]
        judgements = {
            "p1": Judgement(
                example_id="p1", arm="oracle", judge="model:m", answer=None,
                unparsed=True, truncated=True, stop_reason="max_tokens",
            )
        }
        rendered = format_results(cases, {"model:m": judgements}, arm="oracle")
        assert "NOT A RESULT" in rendered
        # And it says why the damage is not random, because "1 of 1 truncated" invites
        # the reader to treat it as missing data rather than as biased data.
        assert "hard cases" in rendered


class TestTheTruncationRetryLadder:
    """Re-ask ONLY the replies that hit the ceiling, and pin the arithmetic that says so.

    `max_tokens` is inside the cache key, so the obvious fix for a truncated reply --
    raise `--max-tokens` and re-run -- invalidates every reply already paid for. On the
    45-case seeded run that was 4 truncated replies out of 45: about $3 of re-purchase to
    repair about $0.25 of damage, and about $6 on the 125-case retrieved arm.

    What makes the cheap fix sound rather than a fudge is that `max_tokens` is a
    CEILING, not a behavioural setting. A reply that stopped on `end_turn` at 1,800
    tokens is byte-identical whether the ceiling it never approached was 6,000 or 12,000,
    so serving it next to a retried reply is not mixing two instruments. That argument
    holds only while every reply that DID hit its ceiling is re-requested, which is the
    property this class exists to keep true -- and it is exactly the kind of claim that
    rots silently, because a ladder that quietly stopped escalating would look like a
    cheaper run rather than like a broken one.
    """

    _ANSWER = '{"verdict": "false", "claim": "c", "code": "d", "reason": "r"}'

    def _warm(self, tmp_path, *, truncated: bool, retry: int | None = None):
        """Populate the cache the way a prior run would have, and return the client."""
        client = (
            _StubClient("", stop_reason="max_tokens", block_type="thinking")
            if truncated
            else _StubClient(self._ANSWER)
        )
        AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=retry,
        ).judge(_context("c1"))
        return client

    def test_a_complete_reply_at_the_low_ceiling_is_reused_rather_than_re_paid(
        self, tmp_path
    ):
        # The whole point. Turning the retry on must not re-ask the 41 replies that were
        # fine, and it must not shift their key -- `_request()` with no argument has to
        # hash exactly the way it did before the option existed.
        self._warm(tmp_path, truncated=False)
        client = _StubClient(self._ANSWER)
        got = AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=12000,
        ).judge(_context("c1"))
        assert client.calls == []
        assert got.cached is True and got.answer is True
        assert got.max_tokens_used == 6000
        assert got.retried is False

    def test_a_truncated_reply_is_re_asked_at_the_raised_ceiling(self, tmp_path):
        self._warm(tmp_path, truncated=True)
        client = _StubClient(self._ANSWER)
        got = AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=12000,
        ).judge(_context("c1"))
        assert len(client.calls) == 1
        assert client.calls[0]["max_tokens"] == 12000
        assert got.answer is True and got.truncated is False
        # Both fields, because the CLI reports "how many were re-asked" off `retried` and
        # "under what ceiling" off `max_tokens_used`. A mixed run has to be able to say it
        # is mixed, or the reuse argument above is untestable from the output.
        assert got.retried is True
        assert got.max_tokens_used == 12000

    def test_a_fresh_case_goes_straight_to_the_highest_ceiling(self, tmp_path):
        # Once, at the top rung, rather than a cheap attempt followed by an escalation.
        # Output tokens are billed on what the model actually produces, not on the
        # ceiling it was allowed, so the low rung buys nothing on an unseen case and
        # costs a second call on every hard one.
        client = _StubClient(self._ANSWER)
        got = AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=12000,
        ).judge(_context("fresh"))
        assert len(client.calls) == 1
        assert client.calls[0]["max_tokens"] == 12000
        assert got.max_tokens_used == 12000
        # NOT retried, and this is the assertion that caught the bug. `retried` was first
        # written as "served above the base rung", which is true here and means nothing:
        # a fresh case is sent at the top rung by design. Under that reading a first-ever
        # run with --retry-max-tokens set would report all 125 replies as re-asked, and
        # the CLI would print "125 reply/replies re-asked" about a run that re-asked
        # nothing -- a false claim about the run, from the tool whose subject is false
        # claims. It now means "a LOWER ceiling was tried and died".
        assert got.retried is False

    def test_a_reply_truncated_at_the_top_rung_is_not_paid_for_twice(self, tmp_path):
        # The ladder has to terminate. A second identical request would be charged for
        # and would hit the identical ceiling, so the answer is to say so and stop.
        self._warm(tmp_path, truncated=True, retry=12000)
        client = _StubClient(self._ANSWER)
        got = AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=12000,
        ).judge(_context("c1"))
        assert client.calls == []
        assert got.truncated is True and got.cached is True
        assert got.max_tokens_used == 12000
        # Warmed straight at the top rung, so nothing lower was ever tried: this reply
        # died at a high ceiling rather than surviving a retry, and saying "re-asked"
        # about it would misreport the run in the opposite direction.
        assert got.retried is False
        # It must say which ceiling it died at, because "raise --retry-max-tokens" is not
        # actionable advice when the reader cannot see what it is already set to.
        assert "12000" in got.reason and "--retry-max-tokens" in got.reason

    def test_a_case_that_died_low_and_survived_high_is_the_one_called_retried(
        self, tmp_path
    ):
        # The only shape that earns the word, and the shape the seeded arm is actually in:
        # 6,000 on disk and truncated, 12,000 bought to replace it. Asserted through the
        # cache rather than through the live call, because the number the CLI prints is
        # read back on every later re-score of the same arm, not only on the paid run.
        self._warm(tmp_path, truncated=True)
        self._warm(tmp_path, truncated=False, retry=12000)
        client = _StubClient("never reached")
        got = AnthropicJudge(
            client=client, cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=12000,
        ).judge(_context("c1"))
        assert client.calls == []
        assert got.cached is True and got.answer is True and got.truncated is False
        assert got.max_tokens_used == 12000 and got.retried is True

    @pytest.mark.parametrize("retry", [None, 0, 1, 6000])
    def test_a_retry_ceiling_at_or_below_the_base_adds_no_rung(self, tmp_path, retry):
        # Otherwise `--retry-max-tokens 6000` against `--max-tokens 6000` would add a
        # second identical key and a second identical call -- paying twice for the same
        # request and then reporting the run as "1 reply re-asked".
        judge = AnthropicJudge(
            client=_StubClient(self._ANSWER), cache_dir=tmp_path, model="m",
            max_tokens=6000, retry_max_tokens=retry,
        )
        assert judge._ceilings() == [6000]
        got = judge.judge(_context("c1"))
        assert got.retried is False and got.max_tokens_used == 6000

    def test_enabling_the_retry_does_not_move_the_base_key(self, tmp_path):
        """The cache-key trap, stated as an equality rather than as a comment.

        26 paid replies were orphaned once already by a change to how the context is
        rendered, and that was a change nobody thought of as touching the cache. The
        retry option is a much easier version of the same mistake: if `_request()` grew
        a `retry_max_tokens` entry, or if the base rung were keyed off the ladder rather
        than off `max_tokens` alone, then merely *offering* the retry would re-pay for
        every reply on disk.
        """
        plain = AnthropicJudge(cache_dir=tmp_path, model="m", max_tokens=6000)
        with_retry = AnthropicJudge(
            cache_dir=tmp_path, model="m", max_tokens=6000, retry_max_tokens=12000
        )
        assert plain._request() == with_retry._request() == {"max_tokens": 6000}
        context = _context("c1")
        assert context_hash(
            context, SYSTEM_PROMPT, "m", request=plain._request()
        ) == context_hash(
            context, SYSTEM_PROMPT, "m", request=with_retry._request(6000)
        )


class TestTheCallMatchesTheInstalledSDK:
    """`_StubClient.create` takes `**kwargs`; the real one does not. Pin the gap.

    This class exists because `temperature=0` sat in the request for as long as it did
    while every test above passed: the only thing the call shape was ever checked
    against was a double written to accept anything. The first real run died on
    `TypeError: Messages.create() got an unexpected keyword argument 'temperature'`
    -- after printing the spend estimate, at the exact moment money was about to be
    spent, which is the worst available time to learn it.

    `bind_partial` against the real signature reproduces that failure with no request,
    no key and no cost. Skipped rather than failed when the SDK is absent, because the
    floors are meant to run with no optional extras installed at all.
    """

    def _sent(self, tmp_path) -> dict:
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        AnthropicJudge(client=client, cache_dir=tmp_path, model="m").judge(_context("c1"))
        return client.calls[0]

    def test_every_argument_is_one_the_real_sdk_accepts(self, tmp_path):
        messages = pytest.importorskip("anthropic.resources.messages")
        signature = inspect.signature(messages.Messages.create)
        # `None` stands in for `self`: the signature is read off the unbound function.
        # If a future SDK grows a `**kwargs`, this stops proving anything -- so assert
        # that it has not, rather than letting the test go quietly vacuous.
        kinds = {p.kind for p in signature.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "Messages.create now absorbs arbitrary keywords, so binding no longer "
            "rejects a bad argument; this test needs a different check"
        )
        signature.bind_partial(None, **self._sent(tmp_path))

    def test_no_sampling_controls_are_sent(self, tmp_path):
        # Absent from the request, not merely absent from the signature. If a later SDK
        # reintroduces `temperature`, putting it back has to be a decision -- and the
        # docstring's claim that this harness has no determinism to lose has to be
        # revisited rather than quietly becoming false.
        assert not {"temperature", "top_p", "top_k"} & set(self._sent(tmp_path))


class TestTheCeilingTheTransportWillActuallyAccept:
    """`--retry-max-tokens 24000` parsed, laddered, and then died inside the SDK.

    `ValueError: Streaming is required for operations that may take longer than 10
    minutes`, raised from `messages.create` at the first truncated reply -- which on a
    fresh run is partway through, after every earlier case has been paid for. Refusing at
    construction costs nothing and turns that into a message.

    The bound is asserted against the SDK's own function rather than against the
    arithmetic in the comment, because the comment cannot notice the SDK changing its
    default timeout and a re-derived number cannot be checked by reading it.
    """

    def _client(self):
        anthropic = pytest.importorskip("anthropic")
        return anthropic.Anthropic(api_key="not-a-real-key")

    def test_the_constant_is_the_largest_ceiling_the_sdk_accepts(self):
        client = self._client()
        # Accepted at the constant, refused one token above it. Two assertions, because
        # an off-by-one in either direction is invisible from one of them: too low and the
        # harness refuses ceilings that would have worked, too high and it does not refuse
        # the one that crashed.
        client._calculate_nonstreaming_timeout(MAX_NONSTREAMING_MAX_TOKENS, None)
        with pytest.raises(ValueError, match="Streaming is required"):
            client._calculate_nonstreaming_timeout(MAX_NONSTREAMING_MAX_TOKENS + 1, None)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_tokens": MAX_NONSTREAMING_MAX_TOKENS + 1},
            {"max_tokens": 6000, "retry_max_tokens": 24_000},
        ],
        ids=["base rung", "retry rung"],
    )
    def test_a_ceiling_above_it_refuses_before_any_call(self, tmp_path, kwargs):
        # Either flag reaches `messages.create` unchanged, so checking only the base rung
        # would leave the exact failure that prompted this in place.
        with pytest.raises(ValueError, match="non-streaming"):
            AnthropicJudge(cache_dir=tmp_path, model="m", **kwargs)

    def test_the_reachable_top_rung_is_still_allowed(self, tmp_path):
        judge = AnthropicJudge(
            cache_dir=tmp_path, model="m", max_tokens=6000,
            retry_max_tokens=MAX_NONSTREAMING_MAX_TOKENS,
        )
        assert judge._ceilings() == [6000, MAX_NONSTREAMING_MAX_TOKENS]


class TestTheRetryCountIsTransportAndNotExperiment:
    """`max_retries` reaches the SDK client and nothing else. Pin both halves.

    Two failures this guards, and they fail in opposite directions:

    1. A constructor keyword the installed SDK does not accept. `_StubClient` is passed
       in ready-made by every test above, so `_ensure_client()` -- the only place this
       argument is used -- is never exercised by them. That is exactly the hole
       `temperature` went through: the run died after the spend estimate printed.
    2. The keyword leaking into the cache key. It is a transport setting; a reply is
       byte-identical however many attempts delivered it. If it reached `_request()` or
       the judge's name, raising the default would re-pay every reply on disk -- about
       $12 of measurement history -- for nothing.
    """

    def test_max_retries_is_an_argument_the_real_sdk_constructor_accepts(self):
        anthropic = pytest.importorskip("anthropic")
        signature = inspect.signature(anthropic.Anthropic.__init__)
        kinds = {p.kind for p in signature.parameters.values()}
        assert inspect.Parameter.VAR_KEYWORD not in kinds, (
            "Anthropic.__init__ now absorbs arbitrary keywords, so binding no longer "
            "rejects a bad argument; this test needs a different check"
        )
        # `None` stands in for `self`, as above: the signature is read off the unbound
        # function. Binding the value the judge would actually send, not a literal.
        signature.bind_partial(None, max_retries=DEFAULT_MAX_RETRIES)

    def test_the_client_is_built_with_the_configured_count(self, tmp_path, monkeypatch):
        anthropic = pytest.importorskip("anthropic")
        # A key is required to construct the client and is never sent anywhere: no
        # request is made here, so this stays free and works offline.
        monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
        judge = AnthropicJudge(cache_dir=tmp_path, model="m", max_retries=5)
        client = judge._ensure_client()
        assert isinstance(client, anthropic.Anthropic)
        assert client.max_retries == 5

    def test_changing_it_does_not_move_the_cache_key(self, tmp_path):
        default = AnthropicJudge(cache_dir=tmp_path, model="m", max_tokens=6000)
        patient = AnthropicJudge(
            cache_dir=tmp_path, model="m", max_tokens=6000, max_retries=64
        )
        assert default._request() == patient._request() == {"max_tokens": 6000}
        context = _context("c1")
        assert context_hash(
            context, SYSTEM_PROMPT, "m", request=default._request()
        ) == context_hash(
            context, SYSTEM_PROMPT, "m", request=patient._request()
        )
        # And not in the judge's name either, which is the results file's key: two
        # retry counts are the same experiment and must land in the same row.
        assert default.name == patient.name


class TestTheResultsFile:
    def test_the_provenance_block_carries_the_corpus_and_the_floor(self):
        cases = [_case("p1", "drift"), _case("n1", "cosmetic"), _case("u1", "unclear")]
        judgements = _judgements(AlwaysJudge(False), cases)
        payload = to_json(
            cases, {"retrieved": {"always-not-false": judgements}},
            tally={"verdicts": 3, "cases": 3},
            noise={"retrieved": {"f1": (0.1, 0.2, 0.3)}},
        )
        provenance = payload["provenance"]
        assert provenance["primary_metric"] == "f1_positive_class"
        assert provenance["corpus"]["cases"] == 3
        assert provenance["majority_class_floor_accuracy"] == pytest.approx(0.5)
        judge = payload["arms"]["retrieved"]["judges"]["always-not-false"]
        assert judge["f1"] == 0.0
        assert judge["by_verdict"]["unclear"] == {"not-false": 1}
        assert payload["arms"]["retrieved"]["noise_range"]["f1"] == [0.1, 0.2, 0.3]

    def test_the_five_class_confusion_survives_the_binary_collapse(self):
        # The diagnostic that tells a fixable prompt problem from an unfixable one:
        # false positives concentrated on `new` mean the judge is flagging features
        # that shipped with their docs.
        cases = [_case("a", "new"), _case("b", "cosmetic"), _case("c", "drift")]
        matrix = confusion(cases, _judgements(AlwaysJudge(True), cases))
        assert matrix["new"]["false"] == 1
        assert matrix["cosmetic"]["false"] == 1
        assert matrix["drift"]["false"] == 1
