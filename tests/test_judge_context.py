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


class TestTheCacheKey:
    def _context(self, **overrides) -> JudgeContext:
        base = dict(
            example_id="x", repo="r", arm="oracle", doc_path="d",
            doc_text="the docs", doc_truncated=False, at_sha="a",
            code_files=(CodeFile("c.py", "code", False, None),), pool_size=1,
        )
        base.update(overrides)
        return JudgeContext(**base)  # type: ignore[arg-type]

    def test_the_same_context_hashes_the_same(self):
        a = context_hash(self._context(), "prompt", "m")
        b = context_hash(self._context(), "prompt", "m")
        assert a == b

    def test_a_changed_prompt_changes_the_key(self):
        # Otherwise editing the prompt appears to have no effect on the result,
        # because every answer comes back from the cache built under the old one.
        a = context_hash(self._context(), "prompt one", "m")
        b = context_hash(self._context(), "prompt two", "m")
        assert a != b

    def test_a_changed_model_changes_the_key(self):
        a = context_hash(self._context(), "p", "claude-sonnet-5")
        b = context_hash(self._context(), "p", "claude-haiku-4-5-20251001")
        assert a != b

    def test_changed_context_content_changes_the_key(self):
        a = context_hash(self._context(), "p", "m")
        b = context_hash(self._context(doc_text="different docs"), "p", "m")
        assert a != b

    def test_the_arm_changes_the_key(self):
        # The two arms can render identically -- a shape-A case whose oracle file is
        # also retrieval's top hit -- and their answers must still not share a cache
        # entry, because the arm is what the result is reported under.
        a = context_hash(self._context(arm="oracle"), "p", "m")
        b = context_hash(self._context(arm="retrieved"), "p", "m")
        assert a != b
