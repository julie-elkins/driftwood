"""The judges and the scoring, with the floors pinned to arithmetic done by hand.

The floor numbers are asserted as literals rather than computed from the corpus,
because a floor recomputed from whatever the corpus currently is cannot detect the
corpus changing -- which is the one thing that would make a stage-3 result
incomparable to the pre-registration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from driftwood.judge.cases import JudgeCase, load_cases
from driftwood.judge.context import CodeFile, JudgeContext
from driftwood.judge.evaluate import (
    abstention_calibration,
    confusion,
    noise_range,
    score,
    to_json,
)
from driftwood.judge.judge import (
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

        low = score(cases, _judgements(AlwaysJudge(False), cases))
        assert low.n == 105
        assert low.accuracy_all == pytest.approx(0.714, abs=0.001)
        assert low.f1 == 0.0

        high = score(cases, _judgements(AlwaysJudge(True), cases))
        assert high.accuracy_all == pytest.approx(0.286, abs=0.001)
        assert high.f1 == pytest.approx(0.444, abs=0.001)

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
        # it would earn credit on 75 of 105 cases for free.
        answer, _, _, reason, unparsed = _parse('{"verdict": "probably-false"}')
        assert answer is None and unparsed
        assert "probably-false" in reason

    def test_malformed_json_abstains_loudly(self):
        answer, *_, unparsed = _parse('{"verdict": "false",,}')
        assert answer is None and unparsed


class _StubClient:
    """Counts calls, so a cache hit is observable rather than assumed."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)

        class _Block:
            type = "text"
            text = self.reply

        class _Response:
            content = [_Block()]

        return _Response()


class TestTheModelArm:
    def test_it_asks_at_temperature_zero_with_the_versioned_prompt(self, tmp_path):
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        got = judge.judge(_context("c1"))
        assert got.answer is True
        assert client.calls[0]["temperature"] == 0
        assert client.calls[0]["system"] == SYSTEM_PROMPT

    def test_a_second_ask_comes_from_the_cache(self, tmp_path):
        client = _StubClient('{"verdict": "false", "reason": "r"}')
        judge = AnthropicJudge(client=client, cache_dir=tmp_path, model="m")
        judge.judge(_context("c1"))
        again = judge.judge(_context("c1"))
        assert len(client.calls) == 1
        assert again.cached is True

    def test_a_changed_prompt_re_asks(self, tmp_path):
        # Temperature 0 is not determinism, so the cache is what makes a re-run
        # reproducible -- and that is only safe if a changed harness invalidates it.
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
            AnthropicJudge()
        # This used to assert `match="floors"`, which passed while the message named a
        # flag value argparse rejected. Whether the suggested command is runnable is
        # checked against the parser in `tests/test_judge_cli.py`; matching prose
        # against prose is what let the false instruction through.


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
