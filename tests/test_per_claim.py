"""The per-claim arm: the unit it asks about, and the two ways it is scored.

Why this file exists separately from `test_judge_scoring.py`: the per-page judge asks one
question and reads one answer, so a mis-parse there is visible as a missing verdict. This
judge asks about eight sentences in one reply and reads eight answers out of it, and the
failure that costs nothing on screen is MISALIGNMENT -- a reply whose second item is scored
against the third sentence. Every downstream number still computes, the abstention rate
looks normal, and the arm measures nothing. Most of what is pinned here is that alignment,
and the rest is the property the arm was built for: a verdict that can be located on the
page without trusting the model to quote it back.
"""

from __future__ import annotations

import json

import pytest

from driftwood.judge.cases import JudgeCase
from driftwood.judge.claims import DEFAULT_BATCH, batch, claim_units, locates
from driftwood.judge.context import (
    CodeFile,
    JudgeContext,
    context_hash,
    render,
    render_claim_batch,
)
from driftwood.judge.evaluate import restrict_to_located, score
from driftwood.judge.judge import (
    CLAIM_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    AnthropicJudge,
    ClaimVerdict,
    Judgement,
    PerClaimJudge,
    _parse_claims,
)


def _context(**overrides) -> JudgeContext:
    base = dict(
        example_id="x", repo="acme/widget", arm="oracle", doc_path="docs/x.rst",
        doc_text="The `connect` function returns a `Session`.",
        doc_truncated=False, at_sha="a",
        code_files=(CodeFile("src/c.py", "def connect(): ...", False, None),),
        pool_size=1,
    )
    base.update(overrides)
    return JudgeContext(**base)  # type: ignore[arg-type]


def _case(example_id: str, verdict: str, **overrides) -> JudgeCase:
    base = dict(
        example_id=example_id, repo="acme/widget", shape="A", basis="b",
        doc_path="docs/x.rst", code_path="src/c.py", at_sha="a", fix_sha="f",
        subject="s", shared_identifiers=(), verdict=verdict, sheet="s.md",
        resolved_from="labels.jsonl",
    )
    base.update(overrides)
    return JudgeCase(**base)  # type: ignore[arg-type]


class _ScriptedClient:
    """Returns a queued reply per call, so a multi-call judge can be driven exactly.

    `_StubClient` in `test_judge_scoring.py` answers every call with the same string,
    which cannot express the thing that matters here: batch 1 parses and batch 2 does
    not, or batch 3 truncates. A queue can, and running dry raises rather than repeating
    the last reply -- a judge making one more call than the test expects is a bug about
    call count, and silently serving it a stale answer hides exactly that.
    """

    def __init__(self, replies, *, stop_reasons=None) -> None:
        self.replies = list(replies)
        self.stop_reasons = list(stop_reasons or [])
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        index = len(self.calls)
        self.calls.append(kwargs)
        if index >= len(self.replies):
            raise AssertionError(
                f"call {index + 1} was made with only {len(self.replies)} reply/replies "
                "scripted"
            )
        reply = self.replies[index]
        stop = (
            self.stop_reasons[index]
            if index < len(self.stop_reasons)
            else "end_turn"
        )

        class _Block:
            type = "text"
            text = reply

        class _Response:
            content = [_Block()]
            stop_reason = stop

        return _Response()


def _reply(*rows: dict) -> str:
    return json.dumps(list(rows))


def _judge(tmp_path, client, **kwargs) -> PerClaimJudge:
    return PerClaimJudge(client=client, cache_dir=tmp_path, model="m", **kwargs)


class TestTheTwoPromptsShareTheirDefinitionOfFalse:
    """The comment above `CLAIM_SYSTEM_PROMPT` promises this test. Without it the promise
    is itself a false claim about the code, in the repository built to find those.

    The arm is supposed to move exactly one lever -- the unit the question is asked about.
    If the definition of "false", the exclusion list or the invitation to abstain drifted
    between the two prompts, then a difference between this arm's F1 and the per-page
    arm's 0.364 would be two changes measured at once and attributable to neither.
    """

    # Copied out of neither prompt: written from the definition, so that editing either
    # prompt's wording fails here rather than being propagated into the test with it.
    _DEFINITION = (
        "A statement is false if a reader who trusted it would be wrong about the code: a "
        "function, parameter, attribute or setting that does not exist or is named "
        "differently; a described default, type, return value or behaviour that contradicts "
        "the code; an example that could not run as written."
    )
    _EXCLUSIONS = (
        "- Prose about design, intent, rationale or history.",
        "- Something described at a higher level than the code, or simplified.",
        "- A statement about code that is not among the files shown. If the relevant code "
        "is not here, you cannot tell.",
        "- Wording, formatting, typography or links.",
        "- A statement you merely cannot verify.",
    )

    def _unwrapped(self, prompt: str) -> str:
        """Both prompts are hard-wrapped with backslash continuations at 88 columns, so
        the shared text is not a shared SUBSTRING -- it is the same sentences broken in
        different places. Comparing the unwrapped forms is what makes the check about the
        wording rather than about the line lengths."""
        return " ".join(prompt.split())

    def test_the_definition_of_false_is_word_for_word_the_same(self):
        for prompt in (SYSTEM_PROMPT, CLAIM_SYSTEM_PROMPT):
            assert self._unwrapped(self._DEFINITION) in self._unwrapped(prompt)

    def test_every_exclusion_is_in_both(self):
        for clause in self._EXCLUSIONS:
            for prompt in (SYSTEM_PROMPT, CLAIM_SYSTEM_PROMPT):
                assert self._unwrapped(clause) in self._unwrapped(prompt)

    def test_both_invite_abstention_in_the_same_words(self):
        invitation = 'answer "unclear". That is a real answer and is preferred over a guess.'
        for prompt in (SYSTEM_PROMPT, CLAIM_SYSTEM_PROMPT):
            assert invitation in self._unwrapped(prompt)

    def test_only_the_claim_prompt_says_the_page_is_absent(self):
        # The one exclusion that is NOT shared, and it has to be unshared: a judge shown
        # the page must not be told the page is missing. Asserting the asymmetry keeps a
        # careless de-duplication of these two prompts from passing the tests above.
        absent = "You are shown the statements only, not the page they came from"
        assert absent in self._unwrapped(CLAIM_SYSTEM_PROMPT)
        assert absent not in self._unwrapped(SYSTEM_PROMPT)

    def test_the_reply_shapes_differ_because_the_unit_does(self):
        assert '"n": 1' in CLAIM_SYSTEM_PROMPT
        assert "JSON array" in CLAIM_SYSTEM_PROMPT
        assert '"n"' not in SYSTEM_PROMPT


class TestWhatCountsAsAClaimUnit:
    def test_a_prose_sentence_marking_up_an_identifier_is_one(self):
        assert claim_units("The `connect` helper opens a socket.") == [
            "The `connect` helper opens a socket."
        ]

    def test_prose_with_no_marked_identifier_is_not(self):
        # The proxy's whole basis: an identifier marked up is the signal that a sentence
        # makes a checkable claim about code. Prose about intent is not checkable, and the
        # prompt's own exclusion list says so.
        assert claim_units("This library was written to be pleasant to read.") == []

    def test_sentences_are_split_and_kept_in_page_order(self):
        got = claim_units(
            "First, `alpha` exists. Second, `beta` does too. Third, nothing here."
        )
        assert got == ["First, `alpha` exists.", "Second, `beta` does too."]

    def test_a_directive_a_fence_and_an_indented_block_yield_nothing(self):
        text = (
            ".. autofunction:: `connect`\n"
            "\n"
            "```\n"
            "result = `connect`()\n"
            "```\n"
            "\n"
            "    indented = `connect`()\n"
            "\n"
            "| `alpha` | `beta` |\n"
        )
        assert claim_units(text) == []

    def test_the_body_between_two_fences_is_not_a_claim(self):
        # The defect this test found, and the reason it is written out at this length: the
        # first version dropped the ``` markers and kept the lines between them, so a
        # markdown example arrived as a prose sentence marking up every identifier it
        # called. An example is exactly where a removed function is MEANT to appear
        # literally, so these would have been the arm's most confident false positives --
        # and nothing about them would have looked wrong in the output.
        md = (
            "Some prose about `connect`.\n"
            "\n"
            "```python\n"
            "result = `connect`(timeout=3)\n"
            "other = `alpha`.beta()\n"
            "```\n"
        )
        assert claim_units(md) == ["Some prose about `connect`."]

    def test_a_fence_opening_straight_after_its_sentence_is_still_a_fence(self):
        # No blank line between them, so the blank-line split does not separate the prose
        # from the example. That is the common shape in a README, which is why the fence
        # pass runs over the whole text before anything is split.
        md = "Call it like this:\n```\nvalue = `connect`()\n```\nAnd `alpha` is returned.\n"
        assert claim_units(md) == ["And `alpha` is returned."]

    def test_an_unclosed_fence_swallows_the_rest_rather_than_inventing_claims(self):
        # The right direction for a proxy whose errors are supposed to undercount: losing
        # the tail of a malformed page costs units, the alternative costs false claims.
        md = "Prose about `connect`.\n\n```\nvalue = `alpha`()\n\nmore = `beta`()\n"
        assert claim_units(md) == ["Prose about `connect`."]

    def test_the_undercount_this_causes_is_the_documented_direction(self):
        # A page whose only claim is in a table yields no unit, so the judge abstains on
        # it by construction. Named in `claims.py` as a known bias; pinned here so that
        # "it undercounts" stays a measured statement rather than a hope.
        table = "+--------+--------+\n| `alpha` | returns a str |\n+--------+--------+\n"
        assert claim_units(table) == []

    def test_a_claim_past_the_document_budget_is_still_a_unit(self):
        # The measured failure that produced this whole arm: the sentence under test sat
        # at character 22,461 of a 38,830-character page, past a 12,000-character budget.
        # Enumeration is over the untruncated text, so distance into the page is not a
        # reason a claim goes unasked.
        page = ("Filler prose with no marked identifier at all.\n\n" * 600
                + "The `connect` helper returns a Session.")
        assert len(page) > 22_461
        assert "The `connect` helper returns a Session." in claim_units(page)


class TestBatching:
    def test_it_preserves_order_and_drops_nothing(self):
        units = [f"u{i}" for i in range(20)]
        got = batch(units, 8)
        assert [u for group in got for u in group] == units
        assert [len(g) for g in got] == [8, 8, 4]

    def test_the_default_is_the_size_the_pricing_was_read_at(self):
        # 8 is not tuned. It is the value `scripts/claim_units.py` priced at 168 calls and
        # 3.5x the input of one per-page pass, and the decision to build this arm was made
        # off that row. A drifting default would make the built thing a different one.
        assert DEFAULT_BATCH == 8
        assert len(batch(list(range(16)))) == 2

    def test_a_size_below_one_is_refused_rather_than_clamped(self):
        # Silently producing no batches is a judge with nothing to say, at F1 0.00, which
        # reads as a measured result.
        with pytest.raises(ValueError, match="at least 1"):
            batch(["a"], 0)

    def test_the_judge_refuses_the_same_size(self):
        with pytest.raises(ValueError, match="at least 1"):
            PerClaimJudge(batch_size=0, model="m")


class TestTheRenderedBatch:
    def test_the_page_body_is_not_in_it(self):
        # Both the cost argument and the point of the design. Putting the page back
        # returns this arm to roughly the naive 26x price it was chosen over, and gives
        # the judge back the thing it demonstrably did not read.
        context = _context(
            doc_text="A LONG PAGE BODY that must not be sent.",
            doc_full="A LONG PAGE BODY that must not be sent.",
        )
        rendered = render_claim_batch(context, ["The `connect` helper exists."])
        assert "LONG PAGE BODY" not in rendered
        assert "The `connect` helper exists." in rendered

    def test_the_code_comes_before_the_claims(self):
        rendered = render_claim_batch(_context(), ["c1"])
        assert rendered.index("--- CODE:") < rendered.index("--- CLAIMS ---")

    def test_the_claims_are_numbered_from_one_within_the_batch(self):
        rendered = render_claim_batch(_context(), ["first", "second", "third"])
        body = rendered.split("--- CLAIMS ---")[1]
        assert "1. first" in body and "2. second" in body and "3. third" in body

    def test_an_absent_code_side_is_said_rather_than_left_blank(self):
        rendered = render_claim_batch(_context(code_files=()), ["c1"])
        assert "No code files were available" in rendered


class TestTheCacheKeyIsUnchangedForEveryCallerThatExistedBefore:
    """`rendered` is an override rather than a second hash function, and the reason is
    that `data/judgements` holds roughly $6 of replies. If the default path's bytes moved
    by one character, every one of them would be re-paid, and nothing on screen would say
    so -- a re-run would simply cost money and produce the same numbers.
    """

    def test_omitting_rendered_hashes_exactly_the_rendered_context(self):
        context = _context()
        request = {"max_tokens": 6000}
        assert context_hash(context, SYSTEM_PROMPT, "m", request=request) == context_hash(
            context, SYSTEM_PROMPT, "m", request=request, rendered=render(context)
        )

    def test_a_claim_batch_gets_a_different_key_from_the_page(self):
        context = _context()
        request = {"max_tokens": 6000}
        page = context_hash(context, SYSTEM_PROMPT, "m", request=request)
        claims = context_hash(
            context, CLAIM_SYSTEM_PROMPT, "m", request=request,
            rendered=render_claim_batch(context, ["The `connect` helper exists."]),
        )
        assert page != claims

    def test_two_batches_of_the_same_page_get_different_keys(self):
        # Otherwise the second batch of every page would be served the first batch's
        # answer, and a judge would report verdicts about sentences it never saw.
        context = _context()
        request = {"max_tokens": 6000}
        keys = {
            context_hash(
                context, CLAIM_SYSTEM_PROMPT, "m", request=request,
                rendered=render_claim_batch(context, group),
            )
            for group in (["claim one"], ["claim two"])
        }
        assert len(keys) == 2

    def test_a_changed_batch_size_re_asks(self):
        # The batch size is not separately in the key and does not need to be: it decides
        # which claims share a user turn, so it is already visible in the rendered text.
        # That argument is only true if this passes.
        context = _context()
        request = {"max_tokens": 6000}
        units = [f"claim {i}" for i in range(4)]
        keys = {
            context_hash(
                context, CLAIM_SYSTEM_PROMPT, "m", request=request,
                rendered=render_claim_batch(context, group),
            )
            for size in (2, 4)
            for group in batch(units, size)
        }
        assert len(keys) == 3  # two halves at size 2, one whole at size 4


class TestReadingABatchReply:
    """The parser, and it is the riskiest code in the arm.

    A misaligned verdict is worse than a missing one because every downstream number
    still computes: the abstention rate looks healthy, the F1 is a real number, and it
    describes sentences the judge was not asked about.
    """

    def test_a_well_formed_reply_is_read_in_full(self):
        rows, unparsed = _parse_claims(
            _reply(
                {"n": 1, "verdict": "false", "code": "src/c.py:connect", "reason": "r1"},
                {"n": 2, "verdict": "not-false", "code": None, "reason": "r2"},
                {"n": 3, "verdict": "unclear", "code": None, "reason": "r3"},
            ),
            3,
        )
        assert unparsed is False
        assert [(n, a) for n, a, _, _ in rows] == [(1, True), (2, False), (3, None)]

    def test_an_item_with_no_n_is_dropped_rather_than_aligned_by_position(self):
        rows, _ = _parse_claims(
            _reply(
                {"verdict": "false", "reason": "which claim?"},
                {"n": 2, "verdict": "not-false", "reason": "r"},
            ),
            2,
        )
        assert [n for n, *_ in rows] == [2]

    def test_a_non_integer_or_out_of_range_n_is_dropped(self):
        rows, _ = _parse_claims(
            _reply(
                {"n": "two", "verdict": "false", "reason": "r"},
                {"n": 9, "verdict": "false", "reason": "r"},
                {"n": 0, "verdict": "false", "reason": "r"},
                {"n": 1, "verdict": "false", "reason": "kept"},
            ),
            2,
        )
        assert [n for n, *_ in rows] == [1]

    def test_a_duplicate_n_keeps_the_first_answer(self):
        # Not "the last wins", which would make the verdict depend on reply ordering, and
        # not an error, which would throw away two good answers for one confused one.
        rows, _ = _parse_claims(
            _reply(
                {"n": 1, "verdict": "false", "reason": "first"},
                {"n": 1, "verdict": "not-false", "reason": "second"},
            ),
            1,
        )
        assert len(rows) == 1
        assert rows[0][1] is True and rows[0][3] == "first"

    def test_an_unrecognised_verdict_word_is_dropped(self):
        rows, unparsed = _parse_claims(
            _reply({"n": 1, "verdict": "probably", "reason": "r"}), 1
        )
        assert rows == [] and unparsed is True

    def test_a_short_reply_is_not_a_failure(self):
        # The claims it did not answer become abstentions, counted and visible. A model
        # that stopped after three of eight said nothing about the other five, and that
        # is the honest reading.
        rows, unparsed = _parse_claims(_reply({"n": 1, "verdict": "false"}), 8)
        assert unparsed is False
        assert [n for n, *_ in rows] == [1]

    def test_prose_around_the_array_is_tolerated(self):
        rows, unparsed = _parse_claims(
            'Here is my answer:\n[{"n": 1, "verdict": "false"}]\nHope that helps.', 1
        )
        assert unparsed is False and rows[0][1] is True

    @pytest.mark.parametrize(
        "text",
        [
            "no json at all",
            "[not valid json",
            '{"n": 1, "verdict": "false"}',  # an object, not the array asked for
            "[]",
            '["false", "not-false"]',  # an array of the wrong thing
        ],
    )
    def test_nothing_alignable_is_an_unparsed_reply(self, text):
        # Never "not-false". A parse failure scored as agreement with the page would earn
        # free credit on the majority class, which is exactly how a broken judge reports a
        # respectable accuracy.
        rows, unparsed = _parse_claims(text, 2)
        assert rows == [] and unparsed is True


class TestTheJudgeOverAWholePage:
    def test_one_false_claim_makes_the_page_false(self):
        context = _context(doc_full="`alpha` exists. `beta` exists. `gamma` exists.")
        client = _ScriptedClient(
            [_reply(
                {"n": 1, "verdict": "not-false", "reason": "fine"},
                {"n": 2, "verdict": "false", "code": "src/c.py", "reason": "no beta"},
                {"n": 3, "verdict": "unclear", "reason": "cannot tell"},
            )]
        )
        got = PerClaimJudge(client=client, model="m", batch_size=8).judge(context)
        assert got.answer is True
        assert got.claim == "`beta` exists."
        assert got.code == "src/c.py"
        assert "1 of 3 claim(s) false" in got.reason

    def test_all_not_false_is_a_not_false_page(self):
        context = _context(doc_full="`alpha` exists. `beta` exists.")
        client = _ScriptedClient(
            [_reply(
                {"n": 1, "verdict": "not-false", "reason": "r"},
                {"n": 2, "verdict": "not-false", "reason": "r"},
            )]
        )
        got = PerClaimJudge(client=client, model="m").judge(context)
        assert got.answer is False
        assert got.claim is None

    def test_all_unclear_is_an_abstention_not_a_not_false(self):
        context = _context(doc_full="`alpha` exists. `beta` exists.")
        client = _ScriptedClient(
            [_reply(
                {"n": 1, "verdict": "unclear", "reason": "r"},
                {"n": 2, "verdict": "unclear", "reason": "r"},
            )]
        )
        got = PerClaimJudge(client=client, model="m").judge(context)
        assert got.answer is None and got.abstained is True

    def test_every_claim_carries_the_text_it_was_asked_about(self):
        # The property the arm was built for. The per-page arm quoted no claim on 5 of its
        # 7 false negatives, which made them unauditable; here the sentence is known
        # before the call, so it exists even when the reply is terse.
        context = _context(doc_full="`alpha` exists. `beta` exists.")
        client = _ScriptedClient([_reply({"n": 1, "verdict": "false"})])
        got = PerClaimJudge(client=client, model="m").judge(context)
        assert [v.claim for v in got.claim_verdicts] == [
            "`alpha` exists.", "`beta` exists."
        ]
        assert all(v.claim for v in got.claim_verdicts)

    def test_the_index_is_over_the_page_not_within_the_batch(self):
        # So a verdict can be located on the page. Batch-local numbering would make claim
        # 1 of batch 3 indistinguishable from claim 1 of batch 1 in the saved output.
        context = _context(
            doc_full=" ".join(f"Claim `helper_{i}` holds." for i in range(5))
        )
        client = _ScriptedClient(
            [_reply({"n": 1, "verdict": "not-false"}),
             _reply({"n": 1, "verdict": "not-false"}),
             _reply({"n": 1, "verdict": "not-false"})]
        )
        got = PerClaimJudge(client=client, model="m", batch_size=2).judge(context)
        assert [v.index for v in got.claim_verdicts] == [1, 2, 3, 4, 5]

    def test_the_call_count_is_the_number_of_batches(self):
        context = _context(
            doc_full=" ".join(f"Claim `helper_{i}` holds." for i in range(5))
        )
        client = _ScriptedClient([_reply({"n": 1, "verdict": "not-false"})] * 3)
        got = PerClaimJudge(client=client, model="m", batch_size=2).judge(context)
        assert got.calls == 3
        assert len(client.calls) == 3

    def test_a_page_with_no_claim_unit_abstains_and_costs_nothing(self):
        # A cost of the design, and the one respect in which the per-page judge is
        # strictly better: it at least sees such a page. `calls=0` is what makes that
        # readable in the output rather than indistinguishable from a model abstaining.
        client = _ScriptedClient([])
        got = PerClaimJudge(client=client, model="m").judge(
            _context(doc_text="Nothing here is marked up.",
                     doc_full="Nothing here is marked up.")
        )
        assert got.answer is None
        assert got.calls == 0
        assert client.calls == []
        assert "by construction" in got.reason

    def test_it_enumerates_from_the_untruncated_page(self):
        # The bug this arm exists to fix, rebuilt on purpose and caught. `doc_text` is cut
        # at DOC_BUDGET; enumerating from it would put the claim at character 22,461 out
        # of reach however many questions were asked.
        client = _ScriptedClient([_reply({"n": 1, "verdict": "false", "reason": "r"})])
        got = PerClaimJudge(client=client, model="m").judge(
            _context(
                doc_text="Nothing marked up survived the budget.",
                doc_full="Nothing marked up survived the budget. But `connect` is gone.",
            )
        )
        assert [v.claim for v in got.claim_verdicts] == ["But `connect` is gone."]

    def test_doc_text_is_the_fallback_when_no_full_page_was_captured(self):
        # Every context built by `ContextBuilder` carries `doc_full`, but a context
        # constructed by hand -- in a script, or in these tests -- may not, and silently
        # judging zero claims would look like a page with nothing to say.
        client = _ScriptedClient([_reply({"n": 1, "verdict": "false"})])
        got = PerClaimJudge(client=client, model="m").judge(
            _context(doc_text="The `connect` helper is gone.", doc_full="")
        )
        assert got.answer is True

    def test_one_unreadable_batch_of_several_does_not_flag_the_case_unparsed(self):
        # `unparsed` is reported when the case lost its WHOLE answer. A page where 1 of 3
        # batches failed still has an answer, and flagging it would overstate the damage
        # in a field the report totals.
        context = _context(
            doc_full=" ".join(f"Claim `helper_{i}` holds." for i in range(3))
        )
        client = _ScriptedClient(
            [_reply({"n": 1, "verdict": "false", "reason": "r"}),
             "garbage",
             _reply({"n": 1, "verdict": "not-false"})]
        )
        got = PerClaimJudge(client=client, model="m", batch_size=1).judge(context)
        assert got.answer is True
        assert got.unparsed is False
        assert "unreadable" in got.reason

    def test_a_case_that_lost_every_batch_is_unparsed(self):
        context = _context(doc_full="`alpha` exists.")
        client = _ScriptedClient(["garbage"])
        got = PerClaimJudge(client=client, model="m").judge(context)
        assert got.answer is None and got.unparsed is True

    def test_truncation_anywhere_marks_the_case_and_says_so_per_claim(self):
        # The batch is a shared reply budget, so one truncation loses up to eight
        # verdicts. A truncated batch must not be readable as eight abstentions: it is a
        # harness failure, and the per-claim reason says which.
        context = _context(doc_full="`alpha` exists. `beta` exists.")
        client = _ScriptedClient([""], stop_reasons=["max_tokens"])
        got = PerClaimJudge(client=client, model="m").judge(context)
        assert got.truncated is True
        assert got.stop_reason == "max_tokens"
        assert got.answer is None
        assert all("TRUNCATED" in v.reason for v in got.claim_verdicts)

    def test_an_unanswered_claim_in_a_readable_batch_says_that_instead(self):
        context = _context(doc_full="`alpha` exists. `beta` exists.")
        client = _ScriptedClient([_reply({"n": 1, "verdict": "false"})])
        got = PerClaimJudge(client=client, model="m").judge(context)
        missing = got.claim_verdicts[1]
        assert missing.answer is None
        assert "no verdict for this claim" in missing.reason

    def test_tokens_are_summed_over_the_batches_not_taken_from_the_last(self):
        # The estimate is checked against this figure, and an arm that reports one
        # batch's usage as the page's would under-read the bill by the batch count.
        context = _context(
            doc_full=" ".join(f"Claim `helper_{i}` holds." for i in range(3))
        )

        class _WithUsage(_ScriptedClient):
            def create(self, **kwargs):
                response = super().create(**kwargs)

                class _Usage:
                    input_tokens = 100
                    output_tokens = 10

                response.usage = _Usage()
                return response

        client = _WithUsage([_reply({"n": 1, "verdict": "not-false"})] * 3)
        got = PerClaimJudge(client=client, model="m", batch_size=1).judge(context)
        assert got.input_tokens == 300
        assert got.output_tokens == 30

    def test_the_name_carries_the_batch_size_and_the_model(self):
        # Two batch settings must not collide under one key in a results file, the same
        # reason the lexical judge carries its threshold.
        assert PerClaimJudge(model="m", batch_size=4).name == "per-claim/4:m"
        assert PerClaimJudge(model="m").name == f"per-claim/{DEFAULT_BATCH}:m"
        assert (
            PerClaimJudge(model="m", effort="high").name
            == f"per-claim/{DEFAULT_BATCH}:m(high)"
        )

    def test_it_asks_with_the_claim_prompt_not_the_page_prompt(self):
        client = _ScriptedClient([_reply({"n": 1, "verdict": "false"})])
        PerClaimJudge(client=client, model="m").judge(
            _context(doc_full="`alpha` exists.")
        )
        assert client.calls[0]["system"] == CLAIM_SYSTEM_PROMPT

    def test_the_per_page_judge_still_asks_the_page_question(self):
        # `judge = judge_page` on the base class. The subclass arriving must leave every
        # existing caller and every cached reply untouched, or the $6 of measurement
        # history behind F1 0.364 is re-paid and the comparison is against a re-run.
        client = _ScriptedClient(['{"verdict": "false", "reason": "r"}'])
        got = AnthropicJudge(client=client, model="m").judge(_context())
        assert got.answer is True
        assert client.calls[0]["system"] == SYSTEM_PROMPT
        assert got.claim_verdicts == ()
        assert got.calls == 1

    def test_a_second_run_of_a_page_makes_no_call(self, tmp_path):
        context = _context(doc_full="`alpha` exists. `beta` exists.")
        client = _ScriptedClient([_reply({"n": 1, "verdict": "not-false"},
                                        {"n": 2, "verdict": "not-false"})])
        first = _judge(tmp_path, client)
        assert first.judge(context).cached is False
        again = _judge(tmp_path, client).judge(context)
        assert again.cached is True
        assert len(client.calls) == 1

    def test_a_page_is_only_cached_when_every_batch_was(self, tmp_path):
        # Otherwise a run that re-paid for half its batches would report itself as served
        # entirely from cache, and the spend line would disagree with the bill.
        context = _context(
            doc_full=" ".join(f"Claim `helper_{i}` holds." for i in range(2))
        )
        warm = _ScriptedClient([_reply({"n": 1, "verdict": "not-false"})])
        _judge(tmp_path, warm, batch_size=1)
        judge = _judge(tmp_path, warm, batch_size=1)
        # First batch only, so the cache holds one of the two.
        judge._reply(context, render_claim_batch(context, ("Claim `helper_0` holds.",)))
        cold = _ScriptedClient([_reply({"n": 1, "verdict": "not-false"})])
        got = _judge(tmp_path, cold, batch_size=1).judge(context)
        assert got.cached is False
        assert len(cold.calls) == 1


class TestTheLocationStrictScoring:
    """The construct-validity measurement, which is the reason the arm was built.

    A label here comes from a commit touching a median 1.6% of the page, while the judge
    is asked about 100% of it. A judge that correctly flags a false sentence the commit
    never corrected is scored wrong for being right -- demonstrated at n=1 on `docs/api.rst`
    and again by accident on `04a332fe`.
    """

    def _flagged(self, claim: str, **overrides) -> Judgement:
        base = dict(
            example_id="aaa", arm="oracle", judge="per-claim/8:m", answer=True,
            claim=claim, code="src/c.py", reason="r",
            claim_verdicts=(
                ClaimVerdict(index=1, claim=claim, answer=True, code="src/c.py",
                             reason="because"),
            ),
            calls=1,
        )
        base.update(overrides)
        return Judgement(**base)  # type: ignore[arg-type]

    def test_a_flagged_claim_naming_a_shared_identifier_survives(self):
        cases = [_case("aaa", "drift", shared_identifiers=("connect",))]
        got = restrict_to_located(
            cases, {"aaa": self._flagged("The `connect` helper is gone.")}
        )
        assert got["aaa"].answer is True
        assert "name an identifier" in got["aaa"].reason

    def test_a_flagged_claim_the_label_cannot_speak_to_becomes_an_abstention(self):
        # Not a false positive. Scoring it wrong assumes the page is true everywhere the
        # commit did not touch, which is the assumption under suspicion.
        cases = [_case("aaa", "cosmetic", shared_identifiers=("connect",))]
        got = restrict_to_located(
            cases, {"aaa": self._flagged("The `unrelated` setting defaults to 3.")}
        )
        assert got["aaa"].answer is None
        assert "HELD OUT by location" in got["aaa"].reason

    def test_the_held_out_case_stays_in_the_denominator(self):
        # Abstaining rather than dropping is what makes this variant's abstention rate
        # readable as "how often the judge flagged something the label cannot speak to".
        cases = [_case("aaa", "cosmetic", shared_identifiers=("connect",))]
        restricted = restrict_to_located(
            cases, {"aaa": self._flagged("The `unrelated` setting defaults to 3.")}
        )
        assert score(cases, restricted).n == 1

    def test_a_not_false_or_abstained_judgement_is_passed_through_untouched(self):
        # The gate is about what a FLAG was about. Restricting a negative verdict by
        # location would be a second change, and would silently raise recall.
        cases = [_case("aaa", "drift", shared_identifiers=("connect",))]
        for answer in (False, None):
            found = self._flagged("irrelevant", answer=answer, claim_verdicts=())
            got = restrict_to_located(cases, {"aaa": found})
            assert got["aaa"] is found

    def test_a_case_with_no_shared_identifiers_holds_out_every_flag(self):
        # Honest rather than convenient: if the miner recorded no overlap, nothing on the
        # page can be shown to be what the label is about.
        cases = [_case("aaa", "drift", shared_identifiers=())]
        got = restrict_to_located(cases, {"aaa": self._flagged("`connect` is gone.")})
        assert got["aaa"].answer is None

    def test_a_judgement_with_no_matching_case_is_passed_through(self):
        got = restrict_to_located([], {"aaa": self._flagged("`connect` is gone.")})
        assert got["aaa"].answer is True

    def test_the_first_located_claim_becomes_the_reported_one(self):
        # The aggregate answer was `True` because of some claim; the located variant has
        # to report a claim that is actually located, or the row's own evidence field
        # contradicts the row.
        cases = [_case("aaa", "drift", shared_identifiers=("connect",))]
        found = self._flagged(
            "The `unrelated` setting defaults to 3.",
            claim_verdicts=(
                ClaimVerdict(index=1, claim="The `unrelated` setting defaults to 3.",
                             answer=True, code="a", reason="first"),
                ClaimVerdict(index=2, claim="The `connect` helper is gone.",
                             answer=True, code="b", reason="second"),
            ),
        )
        got = restrict_to_located(cases, {"aaa": found})
        assert got["aaa"].claim == "The `connect` helper is gone."
        assert got["aaa"].code == "b"


class TestLocating:
    def test_a_bare_word_matches_a_backticked_identifier(self):
        # The whole subtlety: the model quotes claims with the backticks stripped, so
        # requiring marked-up text would score a correctly located claim as unlocated.
        assert locates("The connect helper is gone.", ("connect",))

    def test_a_marked_up_claim_matches_too(self):
        assert locates("The `connect` helper is gone.", ("connect",))

    def test_a_substring_of_a_longer_name_does_not_match(self):
        assert not locates("Call reconnect() first.", ("connect",))
        assert not locates("See connector.py", ("connect",))

    def test_an_attribute_access_does_not_count_as_naming_the_attribute(self):
        # `client.connect` names `client`'s method, not a free `connect`, and treating
        # them as the same is how a loose gate becomes no gate.
        assert not locates("Use session.connect for this.", ("connect",))

    def test_an_empty_claim_or_identifier_locates_nothing(self):
        assert not locates(None, ("connect",))
        assert not locates("", ("connect",))
        assert not locates("anything", ("",))
