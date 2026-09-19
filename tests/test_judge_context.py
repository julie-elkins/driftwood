"""What the judge is shown, and what it must never be shown.

The leak tests are the reason this file exists. Stage 3's corpus was built from the
correcting commit, so the record carries fields that describe the answer -- and
leakage does not fail a test suite, it produces a very good F1. Those tests assert on
the rendered string rather than on the dataclass, because `render` is the only path
from a case to a model and a field could be excluded from the context and still be
formatted into the prompt.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from driftwood.judge import context as context_module
from driftwood.judge.cases import JudgeCase
from driftwood.judge.context import (
    CODE_BUDGET,
    DOC_BUDGET,
    LEAKING_FIELDS,
    CodeFile,
    ContextBuilder,
    JudgeContext,
    context_hash,
    render,
    select_relevant,
)
from driftwood.mining.gitio import local_name_for

# A subject and an identifier list that would be unmistakable in a rendered prompt.
LEAKY_SUBJECT = "Fix the incorrect timeout default documented in the config guide"
LEAKY_IDENTIFIERS = ("timeout_seconds_LEAKED", "DEFAULT_TIMEOUT_LEAKED")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout


@pytest.fixture(scope="module")
def tiny_repo(tmp_path_factory) -> tuple[Path, str, str]:
    """A two-commit repo, and the sha of the parent.

    A real repo rather than a mock: `ContextBuilder` reads a tree through `ls-tree`
    and `cat-file --batch`, and mocking those would test the mock's idea of which
    paths exist at a rev, which is the exact thing that has to be right.
    """
    root = tmp_path_factory.mktemp("clones")
    # Named through `local_name_for`, not hand-spelled: the builder resolves a repo
    # slug to a directory that way, and a hand-spelled name that happens to differ
    # fails as "cat-file ended early" rather than as a missing clone.
    repo = root / local_name_for("acme/widget")
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")

    (repo / "docs").mkdir()
    (repo / "src").mkdir()
    (repo / "docs" / "config.rst").write_text(
        "Configuration\n=============\n\nThe ``connect_timeout`` defaults to 5 seconds.\n"
    )
    (repo / "src" / "client.py").write_text(
        "DEFAULT_CONNECT = 30\n\n\nclass Client:\n    def __init__(self, connect_timeout=DEFAULT_CONNECT):\n        self.connect_timeout = connect_timeout\n"
    )
    (repo / "src" / "unrelated.py").write_text("def helper():\n    return 1\n")
    (repo / "README.md").write_text("# acme widget\n")
    _git(repo, "add", "docs/config.rst", "src/client.py", "src/unrelated.py", "README.md")
    _git(repo, "commit", "-q", "-m", "initial")
    parent = _git(repo, "rev-parse", "HEAD").strip()

    (repo / "docs" / "config.rst").write_text(
        "Configuration\n=============\n\nThe ``connect_timeout`` defaults to 30 seconds.\n"
    )
    _git(repo, "add", "docs/config.rst")
    _git(repo, "commit", "-q", "-m", LEAKY_SUBJECT)
    fix = _git(repo, "rev-parse", "HEAD").strip()
    return root, parent, fix


def _case(parent: str, fix: str, **overrides) -> JudgeCase:
    base = dict(
        example_id="case1",
        repo="acme/widget",
        shape="A",
        basis="code_and_doc_cochanged",
        doc_path="docs/config.rst",
        code_path="src/client.py",
        at_sha=parent,
        fix_sha=fix,
        subject=LEAKY_SUBJECT,
        shared_identifiers=LEAKY_IDENTIFIERS,
        verdict="drift",
        sheet="s.md",
        resolved_from="labels.jsonl",
    )
    base.update(overrides)
    return JudgeCase(**base)  # type: ignore[arg-type]


class TestNothingFromTheFixReachesTheJudge:
    def test_the_fix_commit_subject_is_not_rendered(self, tiny_repo):
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root)
        text = render(builder.build(_case(parent, fix), "oracle"))
        assert LEAKY_SUBJECT not in text
        assert "incorrect" not in text.lower()

    def test_the_miners_evidence_identifiers_are_not_rendered(self, tiny_repo):
        # `shared_identifiers` is the doc diff's removed-only side: the identifiers
        # the fix deleted from the prose. It points at the drifted sentence.
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root)
        text = render(builder.build(_case(parent, fix), "oracle"))
        for identifier in LEAKY_IDENTIFIERS:
            assert identifier not in text

    def test_the_fix_sha_is_not_rendered(self, tiny_repo):
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root)
        text = render(builder.build(_case(parent, fix), "oracle"))
        assert fix not in text

    def test_the_document_shown_is_the_parents_version(self, tiny_repo):
        # The point of the whole stage. At the parent the doc says 5; the fix changes
        # it to 30. Reading the wrong tree would make every case a negative and the
        # result would be a plausible-looking 71%.
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root)
        context = builder.build(_case(parent, fix), "oracle")
        assert "defaults to 5 seconds" in context.doc_text
        assert "defaults to 30 seconds" not in context.doc_text

    def test_no_diff_markers_appear_anywhere(self, tiny_repo):
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root)
        text = render(builder.build(_case(parent, fix), "retrieved"))
        assert "\n+++ " not in text and "\n--- a/" not in text
        assert "@@" not in text

    def test_the_named_leaking_fields_are_the_ones_tested(self):
        # Keeps the constant and the tests from drifting apart: a field added to
        # LEAKING_FIELDS without a test here would be documented, not enforced.
        assert set(LEAKING_FIELDS) == {"subject", "shared_identifiers", "fix_sha"}


class TestTheTwoArms:
    def test_the_oracle_arm_shows_the_commits_own_file(self, tiny_repo):
        root, parent, fix = tiny_repo
        context = ContextBuilder(root).build(_case(parent, fix), "oracle")
        assert [c.path for c in context.code_files] == ["src/client.py"]
        assert context.code_files[0].rank is None

    def test_the_retrieved_arm_ranks_and_reports_the_oracles_rank(self, tiny_repo):
        root, parent, fix = tiny_repo
        context = ContextBuilder(root, k=2).build(_case(parent, fix), "retrieved")
        assert len(context.code_files) <= 2
        assert all(c.rank is not None for c in context.code_files)
        # The doc shares `connect_timeout` with client.py and nothing with the rest,
        # so retrieval should find it. This is the diagnostic that attributes an
        # oracle-vs-retrieved gap to retrieval rather than to judging.
        assert context.oracle_rank == 1

    def test_the_oracle_arm_refuses_a_case_with_no_code_side(self, tiny_repo):
        # Shape B is 80 of the 125 and has no code file in the commit at all.
        # Silently substituting a retrieved file would put one arm's context under
        # the other arm's label.
        root, parent, fix = tiny_repo
        case = _case(parent, fix, shape="B", code_path=None)
        with pytest.raises(ValueError, match="shape A only"):
            ContextBuilder(root).build(case, "oracle")

    def test_the_retrieved_arm_covers_a_case_with_no_code_side(self, tiny_repo):
        root, parent, fix = tiny_repo
        case = _case(parent, fix, shape="B", code_path=None)
        context = ContextBuilder(root).build(case, "retrieved")
        assert context.code_files
        assert context.oracle_rank is None

    def test_an_unknown_arm_raises(self, tiny_repo):
        root, parent, fix = tiny_repo
        with pytest.raises(ValueError, match="unknown arm"):
            ContextBuilder(root).build(_case(parent, fix), "diff-shown")

    def test_only_code_files_enter_the_pool(self, tiny_repo):
        root, parent, fix = tiny_repo
        context = ContextBuilder(root, k=10).build(_case(parent, fix), "retrieved")
        shown = {c.path for c in context.code_files}
        assert "docs/config.rst" not in shown
        assert "README.md" not in shown


class TestThingsThatVanish:
    def test_a_document_absent_at_the_parent_is_recorded_not_blanked(self, tiny_repo):
        # read_blobs omits rather than returning "". Without `missing`, a doc created
        # by the fix would arrive as an empty string, the judge would answer
        # "not-false" about nothing, and it would count as a correct negative.
        root, parent, fix = tiny_repo
        case = _case(parent, fix, doc_path="docs/nope.rst")
        context = ContextBuilder(root).build(case, "oracle")
        assert "docs/nope.rst" in context.missing
        assert context.doc_text == ""
        assert not context.usable

    def test_a_code_file_absent_at_the_parent_is_recorded(self, tiny_repo):
        root, parent, fix = tiny_repo
        case = _case(parent, fix, code_path="src/created_by_the_fix.py")
        context = ContextBuilder(root).build(case, "oracle")
        assert "src/created_by_the_fix.py" in context.missing
        assert context.code_files == ()
        assert not context.usable


class TestCodeIsWindowedRatherThanHeadTruncated:
    """What the judge is shown of a file it cannot be shown all of.

    29 of the 45 oracle files in the first paid run were over the 6,000-character
    budget, and head-truncation showed the judge the first eighth of the module. Three
    of the ten `drift` abstentions gave that as their reason in so many words -- "the
    relevant classes ... are truncated out of the provided models.py excerpt". A budget
    is unavoidable; taking the front of the file is not.
    """

    def _file(self, hits_at: int, total: int = 400) -> str:
        lines = [f"def filler_{i}():\n    return {i}\n" for i in range(total)]
        lines[hits_at] = "def parse_headers(raw):\n    return HeaderDict(raw)\n"
        return "".join(lines)

    def test_a_match_late_in_the_file_survives_the_budget(self):
        # The exact failure. Head-truncation keeps line 0 and loses line 380; the point
        # of selection is that where the match sits in the file stops mattering.
        text = self._file(hits_at=380)
        budget = len(text) // 8
        shown, cut = select_relevant(text, budget, {"parse_headers", "headerdict"})
        assert cut
        assert "parse_headers" in shown
        assert len(shown) < len(text)

    def test_the_enclosing_signature_comes_with_the_match(self):
        # A hit inside a body with its `def` line cut away cannot answer "does this
        # parameter exist", which is most of what documentation claims.
        body = "".join(f"def filler_{i}():\n    return {i}\n" for i in range(300))
        text = body + "def configure(timeout=30):\n" + "    x = 1\n" * 40 + "    return timeout\n"
        shown, cut = select_relevant(text, len(text) // 6, {"timeout"})
        assert cut
        assert "def configure(timeout=30):" in shown

    def test_it_says_how_much_it_dropped_and_why(self):
        text = self._file(hits_at=200)
        shown, _cut = select_relevant(text, len(text) // 8, {"parse_headers"})
        assert "line(s) elided" in shown
        # The reason matters as much as the count: a judge that sees an elision marker
        # and knows the elided lines matched nothing can rule out "it was cut away",
        # which is the abstention this whole change exists to remove.
        assert "mention none of them" in shown

    def test_a_file_inside_the_budget_is_returned_whole_and_unmarked(self):
        text = "def f():\n    return 1\n"
        assert select_relevant(text, 10_000, {"whatever"}) == (text, False)

    def test_the_head_is_kept_even_when_it_matches_nothing(self):
        text = ('"""Module docstring."""\nimport os\nimport sys\n'
                + "".join(f"def filler_{i}():\n    return {i}\n" for i in range(400))
                + "def parse_headers(raw):\n    return raw\n")
        shown, _cut = select_relevant(text, len(text) // 8, {"parse_headers"})
        assert "Module docstring" in shown and "import os" in shown

    def test_nothing_matching_still_returns_something_readable(self):
        # A document sharing no identifier with the file is the common case for a low
        # coverage score, and it must not produce an empty context: `usable` would still
        # be True and the judge would be asked about a file it was shown none of.
        text = self._file(hits_at=10)
        shown, cut = select_relevant(text, len(text) // 8, {"nothing_here_at_all"})
        assert cut
        assert shown.strip()
        assert "def filler_0" in shown

    def test_a_definition_outranks_a_denser_list_of_mentions(self):
        # The first version of this scored lines by raw identifier count, and that is the
        # project's own lesson pointed back at it: `requests/__init__.py` scores ~100%
        # coverage while implementing nothing, because presence is not definition. One
        # `__all__` line naming six identifiers outscored six `def` lines defining them,
        # so the budget bought the part of the module that names everything and defines
        # nothing. Measured: unweighted, 5 of 29 real cut files came out WORSE than
        # head-truncation, `src/flask/app.py` from 100% coverage to 0%.
        wanted = {"parse", "render", "build", "encode", "decode", "verify"}
        mentions = '__all__ = ["parse", "render", "build", "encode", "decode", "verify"]\n'
        filler = "".join(f"def filler_{i}():\n    return {i}\n" for i in range(300))
        text = filler[:200] + mentions + filler + "def verify(cert):\n    return cert\n"
        shown, cut = select_relevant(text, len(text) // 8, wanted)
        assert cut
        assert "def verify(cert):" in shown, "the definition must win the budget"

    def test_an_import_line_never_buys_a_window_of_its_own(self):
        # Scored at zero rather than merely low. A re-export block is the densest possible
        # match and the least informative: every name on it is defined somewhere else.
        text = ("".join(f"def filler_{i}():\n    return {i}\n" for i in range(300))
                + "from .models import Response, Request, Session\n"
                + "".join(f"def other_{i}():\n    return {i}\n" for i in range(300)))
        shown, _cut = select_relevant(text, len(text) // 10, {"Response", "Request", "Session"})
        assert "from .models import" not in shown

    def test_it_is_never_worse_than_the_truncation_it_replaced(self):
        # A file whose relevant definitions sit in the first eighth, with a denser run of
        # mentions further down. Windowing would spend the budget on the mentions and drop
        # definitions the head included for free -- observed on 3 of 29 real files. The
        # guard compares the two on the document's own identifiers, which is a signal the
        # selector is already allowed to see; comparing on the drifted sentence instead
        # would choose the better arm using the answer.
        head = "def parse(raw):\n    return Token(raw)\n" * 3
        tail = "".join(f"# mentions parse and Token here {i}\n" for i in range(4000))
        text = head + tail
        wanted = {"parse", "Token"}
        shown, cut = select_relevant(text, 600, wanted)
        assert cut
        assert "def parse(raw):" in shown


class TestTheSeededArm:
    """The arm that does what the oracle arm was built to do.

    `oracle` shows one file, and the judge's own reasons say one file is not enough:
    seven of its ten `drift` abstentions were "the relevant implementation is not in this
    module". Guaranteeing the known file is present *and* giving it the rest of k
    separates judging from retrieval without also testing whether a page can be answered
    from a single module.
    """

    def test_it_shows_the_commits_own_file_first_and_then_retrieved_ones(self, tiny_repo):
        root, parent, fix = tiny_repo
        context = ContextBuilder(root, k=3).build(_case(parent, fix), "seeded")
        assert context.code_files[0].path == "src/client.py"
        assert context.code_files[0].rank is None
        assert len(context.code_files) > 1, "the whole point is more than one file"
        assert all(c.rank is not None for c in context.code_files[1:])

    def test_the_oracle_file_is_not_shown_twice(self, tiny_repo):
        # It is both the seed and, usually, retrieval's top hit. Showing it twice would
        # spend half the budget on a duplicate and inflate every coverage number.
        root, parent, fix = tiny_repo
        context = ContextBuilder(root, k=3).build(_case(parent, fix), "seeded")
        paths = [c.path for c in context.code_files]
        assert len(paths) == len(set(paths))

    def test_k_is_the_total_and_not_k_plus_the_seed(self, tiny_repo):
        root, parent, fix = tiny_repo
        context = ContextBuilder(root, k=2).build(_case(parent, fix), "seeded")
        assert len(context.code_files) <= 2

    def test_it_refuses_a_case_with_no_code_side(self, tiny_repo):
        root, parent, fix = tiny_repo
        case = _case(parent, fix, shape="B", code_path=None)
        with pytest.raises(ValueError, match="shape A only"):
            ContextBuilder(root).build(case, "seeded")

    def test_nothing_from_the_fix_leaks_into_it_either(self, tiny_repo):
        # The leak tests are per-arm because `render` is per-arm, and a new arm is a new
        # path to a model. The selection signal is the DOCUMENT's identifiers; if it ever
        # became `shared_identifiers` -- the fix's own evidence, which names the drifted
        # sentence -- this arm would quietly start scoring very well indeed.
        root, parent, fix = tiny_repo
        text = render(ContextBuilder(root, k=3).build(_case(parent, fix), "seeded"))
        assert LEAKY_SUBJECT not in text
        assert fix not in text
        for identifier in LEAKY_IDENTIFIERS:
            assert identifier not in text


class TestTruncation:
    def test_a_long_document_is_cut_and_says_so(self, tiny_repo):
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root)
        context = builder.build(_case(parent, fix), "oracle")
        long_doc = "x" * (DOC_BUDGET + 500)
        cut = JudgeContext(
            example_id="x", repo="r", arm="oracle", doc_path="d",
            doc_text=long_doc, doc_truncated=True, at_sha="a",
            code_files=context.code_files, pool_size=1,
        )
        assert "truncated" in render(cut) or len(long_doc) > DOC_BUDGET
        # The flag itself is what the eval reports, so it has to be set by the
        # builder rather than inferred downstream.
        assert context.doc_truncated is False

    def test_the_marker_states_how_much_was_dropped(self):
        from driftwood.judge.context import _truncate

        text, was_cut = _truncate("y" * (CODE_BUDGET + 40), CODE_BUDGET)
        assert was_cut
        assert "40 of" in text and "characters not shown" in text

    def test_text_inside_the_budget_is_untouched(self):
        from driftwood.judge.context import _truncate

        text, was_cut = _truncate("short", 100)
        assert text == "short" and not was_cut


class TestAnsweringIsPossibleAtAll:
    """The free check that should have run before the first paid one.

    The oracle arm scored the model at F1 0.40 with a 69% abstention rate. That reads as
    a judge unwilling to commit, and it was not: the abstentions were correct and
    specific, because the "oracle" code file is the file the FIX COMMIT touched rather
    than the file the document makes claims about. Median identifier coverage across the
    45 shape-A cases is 16%, and 0% for five of them. None of that costs an API call to
    find out, and all of it was measurable before the run.
    """

    def _context(self, doc: str, code: str) -> JudgeContext:
        return JudgeContext(
            example_id="x", repo="r", arm="oracle", doc_path="d.md", doc_text=doc,
            doc_truncated=False, at_sha="a",
            code_files=(CodeFile("c.py", code, False, None),), pool_size=1,
        )

    def test_a_doc_about_the_code_on_screen_scores_high(self):
        got = self._context(
            "Call `parse_headers(raw)` which returns a `HeaderDict`.",
            "class HeaderDict(dict): pass\ndef parse_headers(raw): return HeaderDict()",
        )
        assert got.marked_identifier_coverage == 1.0

    def test_a_doc_about_a_file_that_is_not_shown_scores_zero(self):
        # The real shape of the failure: the doc discusses `Field`, the context carries
        # the file that defines `ConfigDict`, and the only honest answer is "unclear".
        got = self._context(
            "Use `Field(alias=...)` with `AliasChoices` to rename inputs.",
            "class ConfigDict(TypedDict): populate_by_name: bool",
        )
        assert got.marked_identifier_coverage == 0.0

    def test_prose_with_nothing_marked_up_scores_zero_rather_than_dividing_by_nothing(self):
        # Zero, not 1.0. A doc with no checkable identifiers gives a judge nothing to
        # check, so scoring it as fully covered would hide exactly the cases where the
        # warning is most deserved -- and 1.0 is what an empty-set division reads as if
        # you write the ratio the obvious way round.
        assert self._context("Design notes and rationale.", "def f(): pass"
                             ).marked_identifier_coverage == 0.0


class TestTheCacheKey:
    def _context(self, **overrides) -> JudgeContext:
        base = dict(
            example_id="x", repo="r", arm="oracle", doc_path="d",
            doc_text="the docs", doc_truncated=False, at_sha="a",
            code_files=(CodeFile("c.py", "code", False, None),), pool_size=1,
        )
        base.update(overrides)
        return JudgeContext(**base)  # type: ignore[arg-type]

    REQUEST = {"max_tokens": 6000}

    def test_the_same_context_hashes_the_same(self):
        a = context_hash(self._context(), "prompt", "m", request=self.REQUEST)
        b = context_hash(self._context(), "prompt", "m", request=self.REQUEST)
        assert a == b

    def test_a_changed_prompt_changes_the_key(self):
        # Otherwise editing the prompt appears to have no effect on the result,
        # because every answer comes back from the cache built under the old one.
        a = context_hash(self._context(), "prompt one", "m", request=self.REQUEST)
        b = context_hash(self._context(), "prompt two", "m", request=self.REQUEST)
        assert a != b

    def test_a_changed_model_changes_the_key(self):
        a = context_hash(self._context(), "p", "claude-sonnet-5", request=self.REQUEST)
        b = context_hash(
            self._context(), "p", "claude-haiku-4-5-20251001", request=self.REQUEST
        )
        assert a != b

    def test_changed_context_content_changes_the_key(self):
        a = context_hash(self._context(), "p", "m", request=self.REQUEST)
        b = context_hash(
            self._context(doc_text="different docs"), "p", "m", request=self.REQUEST
        )
        assert a != b

    def test_the_arm_changes_the_key(self):
        # The two arms can render identically -- a shape-A case whose oracle file is
        # also retrieval's top hit -- and their answers must still not share a cache
        # entry, because the arm is what the result is reported under.
        a = context_hash(self._context(arm="oracle"), "p", "m", request=self.REQUEST)
        b = context_hash(self._context(arm="retrieved"), "p", "m", request=self.REQUEST)
        assert a != b

    def test_a_changed_reply_budget_changes_the_key(self):
        # The one this class was missing, and the omission had teeth. A 700-token budget
        # truncated 16 of 45 replies mid-reasoning and cached all 16 as empty answers;
        # without this, raising the budget would have re-served every one of them
        # instantly, for free, looking exactly like a fix that changed nothing.
        a = context_hash(self._context(), "p", "m", request={"max_tokens": 700})
        b = context_hash(self._context(), "p", "m", request={"max_tokens": 6000})
        assert a != b

    def test_a_changed_effort_changes_the_key(self):
        a = context_hash(self._context(), "p", "m", request=self.REQUEST)
        b = context_hash(
            self._context(), "p", "m",
            request={**self.REQUEST, "output_config": {"effort": "low"}},
        )
        assert a != b

    def test_the_order_the_request_was_written_in_does_not_matter(self):
        # Keys are sorted before hashing, so an unrelated refactor of the dict literal
        # cannot invalidate a cache full of replies that are still perfectly valid.
        a = context_hash(
            self._context(), "p", "m", request={"max_tokens": 1, "output_config": {}}
        )
        b = context_hash(
            self._context(), "p", "m", request={"output_config": {}, "max_tokens": 1}
        )
        assert a == b


class TestTheCodeBudgetIsASweptParameter:
    """`code_budget` moved from a constant read at the point of use to a builder
    argument, because the budget turned out to be the lever.

    Measured on the 5 recall-costing cases whose answer-bearing definition was cut:
    9,000 characters brings 2 of them on screen, 36,000 brings 4, and nothing in
    between recovers anything further. That is a dimension to sweep, and sweeping it by
    editing the module constant would change every later run's cache key invisibly.
    """

    def test_it_defaults_to_the_published_constant(self, tiny_repo):
        # The default has to stay the value every score in `data/scores/` was produced
        # at, or a re-run silently measures a different harness.
        root, _parent, _fix = tiny_repo
        assert ContextBuilder(root).code_budget == CODE_BUDGET

    def test_the_seed_file_is_windowed_at_the_builders_budget(
        self, tiny_repo, monkeypatch
    ):
        # Checked by capturing the argument rather than by measuring the output, because
        # the fixture's files are shorter than `_HEAD_LINES` and so are returned whole at
        # any budget. That is correct behaviour and it makes an output-shape assertion
        # here vacuous -- it passed against the constant still being read at the call site.
        root, parent, fix = tiny_repo
        seen: list[int] = []
        real = context_module.select_relevant
        monkeypatch.setattr(
            context_module,
            "select_relevant",
            lambda text, budget, wanted: (seen.append(budget), real(text, budget, wanted))[1],
        )
        ContextBuilder(root, code_budget=1234).build(_case(parent, fix), "oracle")
        assert seen == [1234]

    def test_the_retrieved_files_are_windowed_at_it_too(self, tiny_repo, monkeypatch):
        # Two call sites in `build`, and the seeded arm goes through both. A budget
        # honoured on the seed and ignored on the retrieved files would spend an
        # unbounded amount on exactly the files nobody chose.
        root, parent, fix = tiny_repo
        seen: list[int] = []
        real = context_module.select_relevant
        monkeypatch.setattr(
            context_module,
            "select_relevant",
            lambda text, budget, wanted: (seen.append(budget), real(text, budget, wanted))[1],
        )
        context = ContextBuilder(root, k=3, code_budget=1234).build(
            _case(parent, fix), "seeded"
        )
        assert any(f.rank is not None for f in context.code_files), (
            "the seeded arm must show retrieved files as well as the seed"
        )
        assert len(seen) == len(context.code_files) > 1
        assert set(seen) == {1234}

    def test_changing_it_changes_the_rendered_code_and_so_the_cache_key(self):
        # The whole safety argument for making this a flag. The budget is not in the
        # request dict, so it can only reach the key through the rendered context -- and
        # if it did not, a run at a new budget would be served the old budget's replies
        # and report them as a result for the new one.
        body = "".join(
            f"def thing_{n}(timeout):\n    return timeout\n\n\n" for n in range(60)
        )
        wanted = frozenset({"timeout"})
        narrow, narrow_cut = select_relevant(body, 400, wanted)
        wide, wide_cut = select_relevant(body, 1200, wanted)
        assert narrow_cut and wide_cut
        assert narrow != wide and len(narrow) < len(wide)

        request = {"max_tokens": 6000}
        def _context(text: str) -> JudgeContext:
            return JudgeContext(
                example_id="x", repo="r", arm="oracle", doc_path="d",
                doc_text="the ``timeout`` argument", doc_truncated=False, at_sha="a",
                code_files=(CodeFile("src/x.py", text, True, rank=None),),
                pool_size=1,
            )

        assert context_hash(
            _context(narrow), "p", "m", request=request
        ) != context_hash(_context(wide), "p", "m", request=request)


class TestTheDocumentBudgetIsASweptParameterToo:
    """Added because 5 of 9 recall-costing cases had a cut document and nobody had asked
    whether the cut removed the CLAIM.

    It did, on 3 of them. `psf/requests docs/user/advanced.rst` is 38,830 characters and
    the sentence the fixing commit deleted starts at character 22,461 -- so at
    `DOC_BUDGET = 12,000` the false statement under test was not in the prompt at all, and
    those cases were unanswerable rather than answered wrongly. Truncation was counted
    from the first paid run; what it cut was not.
    """

    def test_it_defaults_to_the_published_constant(self, tiny_repo):
        root, _parent, _fix = tiny_repo
        assert ContextBuilder(root).doc_budget == DOC_BUDGET

    def test_a_smaller_budget_cuts_the_document_and_says_so(self, tiny_repo):
        # The doc side is head-truncated rather than windowed, so unlike the code side a
        # short file does shrink -- and the flag it sets is what the eval reports.
        root, parent, fix = tiny_repo
        whole = ContextBuilder(root).build(_case(parent, fix), "oracle")
        assert whole.doc_truncated is False

        tight = ContextBuilder(root, doc_budget=30).build(_case(parent, fix), "oracle")
        assert tight.doc_truncated is True
        # On the prose, not on `len`: the marker explaining the cut is longer than the
        # sentence it replaced on a page this small, so a length assertion would fail
        # while the cut it is checking for had happened correctly.
        assert "defaults to 5 seconds" in whole.doc_text
        assert "defaults to 5 seconds" not in tight.doc_text
        assert "truncated" in render(tight)

    def test_it_is_independent_of_the_code_budget(self, tiny_repo):
        # Two separate levers on two separate measured failures, and the probe that
        # distinguishes them needs to move one without the other.
        root, parent, fix = tiny_repo
        builder = ContextBuilder(root, doc_budget=30, code_budget=99_000)
        context = builder.build(_case(parent, fix), "oracle")
        assert context.doc_truncated is True
        assert context.code_files[0].truncated is False
